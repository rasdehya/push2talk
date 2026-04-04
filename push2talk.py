#!/usr/bin/env python3
"""
Push-to-Talk — script principal

Cycle de vie à deux niveaux :
  • Niveau APP    : toujours actif (surveillance USB, systray, Whisper)
  • Niveau SESSION: actif uniquement quand le micro est branché
                   (capture clavier, enregistrement, transcription)

Quand le micro est débranché → la SESSION s'arrête, mais l'APP continue
à écouter le port USB. Rebrancher le micro relance une nouvelle SESSION.
Cliquer "Quitter" dans le systray → arrêt total de l'APP.
"""

from __future__ import annotations

import logging
import os
import pathlib
import signal
import socket
import subprocess
import sys
import threading
import time
import select
import wave
from typing import Optional

import evdev
import requests
from evdev import UInput, categorize, ecodes
from PIL import Image, ImageDraw
from pystray import Icon, Menu, MenuItem

import config
from config import (
    KEY_TRIGGER,
    MIC_NAME,
    AUDIO_FILE,
    WHISPER_URL,
    ICON,
    MIN_RECORD_DURATION,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(threadName)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("push_to_talk")

# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------
BASE_DIR = pathlib.Path(__file__).resolve().parent
WHISPER_SERVER = BASE_DIR / "whisper_server.py"

# ---------------------------------------------------------------------------
# Events de cycle de vie
# ---------------------------------------------------------------------------
# Mis à True une seule fois → arrêt total de l'application
app_shutdown_event = threading.Event()

# Mis à True quand le micro est débranché → arrêt de la session clavier
# Remis à False quand une nouvelle session démarre
session_stop_event = threading.Event()

# ---------------------------------------------------------------------------
# État session (enregistrement en cours)
# ---------------------------------------------------------------------------
_rec_lock = threading.Lock()
_rec: Optional[subprocess.Popen] = None
_recording = False


def _is_recording() -> bool:
    with _rec_lock:
        return _recording


# ---------------------------------------------------------------------------
# Icône systray (instanciée une seule fois)
# ---------------------------------------------------------------------------
_tray_icon: Optional[Icon] = None
_tray_lock = threading.Lock()

# Process du serveur Whisper (None si démarré avant nous ou non géré)
_whisper_proc: Optional[subprocess.Popen] = None


# ---------------------------------------------------------------------------
# Icône systray
# ---------------------------------------------------------------------------
def _load_tray_image() -> Image.Image:
    try:
        return Image.open(str(ICON))
    except Exception:
        log.warning("Icône '%s' introuvable, utilisation du fallback.", ICON)
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((4, 4, 60, 60), fill=(220, 50, 50, 255))
        return img


def setup_tray() -> None:
    """
    Crée l’icône systray UNE seule fois et bloque dans ce thread jusqu’au stop().
    Sur xorg, écoute les clics via une boucle Xlib car pystray ne dispatche
    pas les événements ButtonPress sur ce backend.
    """
    global _tray_icon

    with _tray_lock:
        if _tray_icon is not None:
            log.debug("Icône systray déjà créée, on ignore.")
            return

        def on_quit() -> None:
            log.info("Quitter demandé depuis le systray.")
            app_shutdown_event.set()
            session_stop_event.set()

        _tray_icon = Icon(
            "push_to_talk",
            _load_tray_image(),
            "Push To Talk",
        )
        log.info("Icône systray prête.")

    def _watch_clicks(icon: Icon) -> None:
        """
        Boucle Xlib dédiée aux clics sur la fenêtre systray.
        Tourne dans un thread daemon séparé.
        """
        try:
            from Xlib import X
            from Xlib.display import Display as XDisplay

            dpy = XDisplay()
            for _ in range(50):
                if icon._window is not None:
                    break
                time.sleep(0.1)
            else:
                log.error("Fenêtre X pystray jamais créée, clics indisponibles.")
                return

            win = dpy.create_resource_object("window", icon._window)
            win.change_attributes(event_mask=X.ButtonPressMask)
            dpy.sync()
            log.debug("Écoute des clics Xlib sur window=0x%x", int(icon._window.id))

            while not app_shutdown_event.is_set():
                while dpy.pending_events():
                    ev = dpy.next_event()
                    if ev.type == X.ButtonPress:
                        log.debug("Clic Xlib détecté, bouton=%d", ev.detail)
                        on_quit()
                        return
                time.sleep(0.05)

        except Exception:
            log.exception("Erreur dans _watch_clicks.")

    def _setup(icon: Icon) -> None:
        icon.visible = True
        threading.Thread(
            target=_watch_clicks, args=(icon,), name="XlibClickWatcher", daemon=True
        ).start()

    try:
        _tray_icon.run(setup=_setup)
    except Exception:
        log.exception("Erreur dans la boucle du systray.")
    finally:
        log.info("Thread systray terminé.")


def stop_tray() -> None:
    with _tray_lock:
        icon = _tray_icon
    if icon is not None:
        try:
            icon.stop()
            log.info("Icône systray arrêtée.")
        except Exception:
            log.exception("Erreur lors de l'arrêt du systray.")


# ---------------------------------------------------------------------------
# Whisper server
# ---------------------------------------------------------------------------
def _is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False


def ensure_whisper(host: str = "127.0.0.1", port: int = None, wait: int = 30) -> None:
    """Vérifie que le serveur Whisper tourne ; le démarre si nécessaire.
    Si on le démarre nous-mêmes, on stocke le process dans _whisper_proc."""
    global _whisper_proc
    if port is None:
        port = config.WHISPER_PORT if hasattr(config, "WHISPER_PORT") else 5001

    if _is_port_open(host, port):
        log.info(
            "Serveur Whisper déjà actif sur %s:%d (non géré par nous).", host, port
        )
        return

    log.info("Démarrage du serveur Whisper…")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(WHISPER_SERVER)],
            cwd=str(BASE_DIR),
            stdout=None,
            stderr=None,
        )
    except OSError as exc:
        raise RuntimeError(f"Impossible de lancer whisper_server.py : {exc}") from exc

    for elapsed in range(wait):
        if _is_port_open(host, port):
            log.info("Serveur Whisper prêt après %d s.", elapsed + 1)
            _whisper_proc = proc
            return
        if proc.poll() is not None:
            raise RuntimeError("Serveur Whisper arrêté de façon inattendue.")
        time.sleep(1)

    raise RuntimeError(f"Serveur Whisper inactif après {wait} secondes d'attente.")


def stop_whisper() -> None:
    """Arrête le serveur Whisper — via le process si on l'a lancé,
    sinon en cherchant le PID qui écoute sur le port 5001."""
    global _whisper_proc

    if _whisper_proc is not None:
        log.info("Arrêt du serveur Whisper (process géré)…")
        try:
            _whisper_proc.terminate()
            _whisper_proc.wait(timeout=5)
            log.info("Serveur Whisper arrêté.")
        except subprocess.TimeoutExpired:
            log.warning("Whisper ne répond pas, on le tue.")
            _whisper_proc.kill()
        except Exception:
            log.exception("Erreur lors de l'arrêt de Whisper.")
        finally:
            _whisper_proc = None
        return

    # Whisper était déjà lancé avant nous → on cherche le PID via le port
    log.info(
        "Recherche du processus Whisper sur le port %d…",
        config.WHISPER_PORT if hasattr(config, "WHISPER_PORT") else 5001,
    )
    port = config.WHISPER_PORT if hasattr(config, "WHISPER_PORT") else 5001
    try:
        result = subprocess.run(
            ["fuser", f"{port}/tcp"], capture_output=True, text=True
        )
        pids = result.stdout.strip().split()
        if not pids:
            log.warning("Aucun processus trouvé sur le port 5001.")
            return
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGTERM)
                log.info("SIGTERM envoyé au PID %s (Whisper).", pid)
            except ProcessLookupError:
                log.warning("PID %s introuvable.", pid)
            except Exception:
                log.exception("Erreur lors du kill du PID %s.", pid)
    except FileNotFoundError:
        log.error("fuser introuvable, impossible d'arrêter Whisper par port.")
    except Exception:
        log.exception("Erreur lors de la recherche du processus Whisper.")


# ---------------------------------------------------------------------------
# Enregistrement audio
# ---------------------------------------------------------------------------
def _find_arecord_device() -> list:
    """
    Cherche le numéro de carte ALSA correspondant à MIC_NAME dans arecord -l.
    Retourne ["-D", "plughw:X,0"] si trouvé, [] sinon (arecord utilisera le défaut).
    """
    try:
        result = subprocess.run(
            ["/usr/bin/arecord", "-l"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if MIC_NAME in line and line.startswith("carte"):
                card_num = line.split(":")[0].replace("carte", "").strip()
                log.debug("Micro trouvé sur carte ALSA %s.", card_num)
                return ["-D", f"plughw:{card_num},0"]
    except Exception:
        log.exception("Erreur lors de la recherche du périphérique arecord.")
    log.warning(
        "Micro '%s' non trouvé dans arecord -l, utilisation du périphérique par défaut.",
        MIC_NAME,
    )
    return []


def start_record() -> None:
    global _rec, _recording

    with _rec_lock:
        if _rec is not None:
            log.warning(
                "start_record() appelé alors qu'un enregistrement est déjà en cours."
            )
            return
        log.info("Démarrage de l'enregistrement → %s", AUDIO_FILE)
        try:
            _rec = subprocess.Popen(
                ["/usr/bin/arecord"]
                + _find_arecord_device()
                + [
                    "-f",
                    "S16_LE",
                    "-r",
                    "16000",
                    "-c",
                    "1",
                    "-t",
                    "wav",
                    str(AUDIO_FILE),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            _recording = True
        except FileNotFoundError:
            log.error("Enregistreur audio introuvable. Vérifiez alsa-utils.")
            _rec = None
        except Exception:
            log.exception("Erreur lors du lancement de l'enregistrement.")
            _rec = None


def stop_record() -> None:
    global _rec, _recording

    with _rec_lock:
        proc = _rec
        _rec = None
        _recording = False

    if proc is None:
        log.warning("stop_record() appelé sans enregistrement actif.")
        return

    try:
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        log.warning("Enregistrement ne répond pas, on le tue.")
        proc.kill()
        proc.wait()
    except Exception:
        log.exception("Erreur lors de l'arrêt de l'enregistrement.")

    try:
        with wave.open(str(AUDIO_FILE), "rb") as wf:
            duration = wf.getnframes() / wf.getframerate()
    except Exception:
        log.exception("Impossible de lire %s pour vérifier la durée.", AUDIO_FILE)
        try:
            os.remove(AUDIO_FILE)
        except OSError:
            pass
        return

    log.debug("Durée du clip audio : %.2f s", duration)

    if duration < MIN_RECORD_DURATION:
        log.info(
            "Clip trop court (%.2f s < %.2f s), transcription annulée.",
            duration,
            MIN_RECORD_DURATION,
        )
        return
    threading.Thread(target=transcribe, name="Transcribe", daemon=True).start()


# ---------------------------------------------------------------------------
# Transcription Whisper
# ---------------------------------------------------------------------------
def transcribe() -> None:
    log.info("Envoi de %s au serveur Whisper…", AUDIO_FILE)
    try:
        resp = requests.post(
            WHISPER_URL,
            json={"file_path": str(AUDIO_FILE)},
            timeout=120,
        )
        resp.raise_for_status()
        text: str = resp.json().get("text", "").strip()
    except requests.RequestException:
        log.exception("Erreur de communication avec Whisper.")
        return

    try:
        os.remove(AUDIO_FILE)
    except OSError:
        pass

    if not text:
        log.info("Whisper a retourné un texte vide.")
        return

    log.info("Texte transcrit : %r", text)
    try:
        subprocess.run(["xdotool", "type", "--clearmodifiers", "--", text], check=True)
        subprocess.run(["xdotool", "key", "Return"], check=True)
    except FileNotFoundError:
        log.error("xdotool introuvable. Installez xdotool.")
    except subprocess.CalledProcessError:
        log.exception("Erreur xdotool lors de la saisie du texte.")


# ---------------------------------------------------------------------------
# Clavier
# ---------------------------------------------------------------------------
def find_keyboard() -> evdev.InputDevice:
    devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
    for d in devices:
        if "keyboard" in d.name.lower():
            log.info("Clavier trouvé : %s (%s)", d.name, d.path)
            return d
    if devices:
        log.warning(
            "Aucun clavier nommé 'keyboard', utilisation de %s.", devices[0].name
        )
        return devices[0]
    raise RuntimeError("Aucun périphérique d'entrée détecté par evdev.")


# ---------------------------------------------------------------------------
# Session clavier (liée à la présence du micro)
# ---------------------------------------------------------------------------
def run_keyboard_session() -> None:
    """
    Capture le clavier et écoute les événements jusqu'à ce que
    session_stop_event soit mis à True (micro débranché ou quitter).
    """
    log.info("Démarrage de la session clavier.")
    global _recording

    try:
        device = find_keyboard()
    except RuntimeError:
        log.exception("Impossible de trouver un clavier.")
        return

    try:
        device.grab()
        log.info("Clavier accaparé : %s", device.name)
    except Exception:
        log.exception("Impossible de capturer le clavier.")
        return

    ui = UInput.from_device(device)

    try:
        while not session_stop_event.is_set() and not app_shutdown_event.is_set():
            # Timeout 0.5s pour vérifier les events de shutdown sans attendre de frappe
            r, _, _ = select.select([device.fd], [], [], 0.5)
            if not r:
                continue
            for event in device.read():
                if event.type != ecodes.EV_KEY:
                    ui.write_event(event)
                    ui.syn()
                    continue
                key = categorize(event)
                if key.scancode == KEY_TRIGGER:
                    if key.keystate == key.key_down and not _is_recording():
                        start_record()
                    elif key.keystate == key.key_up and _is_recording():
                        stop_record()
                else:
                    ui.write_event(event)
                    ui.syn()
        log.info("Arrêt demandé, sortie de la boucle clavier.")

    except OSError as exc:
        log.error("Erreur I/O sur le clavier (périphérique retiré ?) : %s", exc)
    except Exception:
        log.exception("Erreur inattendue dans la boucle clavier.")
    finally:
        # Arrêt de l'enregistrement si en cours
        with _rec_lock:
            proc = _rec
        if proc is not None:
            log.info("Enregistrement en cours, arrêt forcé.")
            try:
                proc.send_signal(signal.SIGINT)
                proc.wait(timeout=3)
            except Exception:
                proc.kill()

        try:
            device.ungrab()
        except Exception:
            pass
        try:
            ui.close()
        except Exception:
            pass

        log.info("Session clavier terminée.")


# ---------------------------------------------------------------------------
# Surveillance du microphone (niveau APP — tourne toujours)
# ---------------------------------------------------------------------------
def mic_watcher_loop() -> None:
    """
    Tourne en permanence au niveau APP.
    - Micro branché  → démarre une session clavier (dans un thread)
    - Micro débranché → arrête la session en cours via session_stop_event
    - app_shutdown_event → sort de la boucle
    """
    # Initialise à True si le micro est déjà branché au démarrage
    try:
        _r = subprocess.run(
            ["/usr/bin/arecord", "-l"], capture_output=True, text=True, timeout=5
        )
        mic_connected = MIC_NAME in _r.stdout
        if mic_connected:
            log.info("Micro déjà branché au démarrage, déclenchement immédiat.")
    except Exception:
        mic_connected = False

    session_thread: Optional[threading.Thread] = None

    log.info("Surveillance du micro '%s' démarrée.", MIC_NAME)

    # Si le micro est déjà branché, démarre immédiatement la session
    if mic_connected:
        try:
            ensure_whisper()
        except RuntimeError:
            log.exception("Impossible de démarrer Whisper au démarrage.")
        session_stop_event.clear()
        session_thread = threading.Thread(
            target=run_keyboard_session, name="KeyboardSession", daemon=True
        )
        session_thread.start()

    while not app_shutdown_event.is_set():
        try:
            result = subprocess.run(
                ["/usr/bin/arecord", "-l"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            mic_present = MIC_NAME in result.stdout

        except subprocess.TimeoutExpired:
            log.warning("arecord -l a mis trop de temps à répondre.")
            app_shutdown_event.wait(timeout=2.0)
            continue
        except FileNotFoundError:
            log.error("arecord introuvable, surveillance du micro impossible.")
            return
        except Exception:
            log.exception("Erreur inattendue dans mic_watcher_loop().")
            app_shutdown_event.wait(timeout=2.0)
            continue

        # --- Micro vient d'être branché ---
        if mic_present and not mic_connected:
            mic_connected = True
            log.info("Micro détecté, démarrage d'une nouvelle session.")

            try:
                ensure_whisper()
            except RuntimeError:
                log.exception("Impossible de démarrer Whisper au branchement.")

            # Réinitialise l'event de session pour cette nouvelle session
            session_stop_event.clear()

            session_thread = threading.Thread(
                target=run_keyboard_session,
                name="KeyboardSession",
                daemon=True,
            )
            session_thread.start()

        # --- Micro vient d'être débranché ---
        elif not mic_present and mic_connected:
            mic_connected = False
            log.warning("Micro débranché, arrêt de la session.")

            # Signale l'arrêt à la session clavier
            session_stop_event.set()

            # Attend que la session se termine (max 5 s)
            if session_thread and session_thread.is_alive():
                session_thread.join(timeout=5.0)
                if session_thread.is_alive():
                    log.warning(
                        "La session clavier ne s'est pas terminée dans les temps."
                    )

            stop_whisper()

        app_shutdown_event.wait(timeout=1.0)

    log.info("Thread de surveillance du micro terminé.")


# ---------------------------------------------------------------------------
# Gestionnaires de signaux système
# ---------------------------------------------------------------------------
def _handle_system_signal(signum: int, _frame) -> None:
    log.info("Signal %d reçu, arrêt total en cours…", signum)
    app_shutdown_event.set()
    session_stop_event.set()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    signal.signal(signal.SIGINT, _handle_system_signal)
    signal.signal(signal.SIGTERM, _handle_system_signal)

    log.info("=== Push-To-Talk démarrage ===")

    # --- Systray (thread dédié, bloquant, une seule instance) ---
    # Lancé immédiatement, indépendamment du micro
    tray_thread = threading.Thread(target=setup_tray, name="SystrayThread", daemon=True)
    tray_thread.start()

    # --- Surveillance micro (niveau APP, tourne toujours) ---
    # Whisper et session clavier sont gérés à l'intérieur au branchement/débranchement
    mic_thread = threading.Thread(
        target=mic_watcher_loop, name="MicWatcher", daemon=True
    )
    mic_thread.start()

    log.info("Application démarrée. En attente du micro '%s'…", MIC_NAME)

    # --- Boucle principale : attend le shutdown total ---
    try:
        app_shutdown_event.wait()
    except KeyboardInterrupt:
        log.info("KeyboardInterrupt dans main().")
        app_shutdown_event.set()
        session_stop_event.set()

    # --- Nettoyage final ---
    log.info("Arrêt de l'application…")

    stop_whisper()
    stop_tray()

    for t, label in [(mic_thread, "MicWatcher"), (tray_thread, "SystrayThread")]:
        t.join(timeout=5.0)
        if t.is_alive():
            log.warning("Thread '%s' toujours actif après timeout.", label)

    log.info("=== Push-To-Talk arrêté proprement ===")


if __name__ == "__main__":
    main()
