#!/usr/bin/env python3
import evdev
from evdev import categorize, ecodes, UInput
import subprocess
import requests
import time
import os
import signal
import config
import pathlib
import sys
import wave

BASE_DIR = pathlib.Path(__file__).resolve().parent
WHISPER_SERVER = BASE_DIR / "whisper_server.py"

recording = False
rec = None

# -------------------------
# Notifications
# -------------------------
def notify(msg):
    icon_path = os.path.abspath(config.ICON) if hasattr(config, "ICON") else None
    cmd = ["notify-send"]
    if icon_path:
        cmd += ["-i", icon_path]
    cmd += ["Push To Talk", msg]
    subprocess.run(cmd)

# -------------------------
# Whisper server
# -------------------------
def is_port_open(host, port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(0.5)
            s.connect((host, port))
            return True
        except:
            return False

def ensure_whisper():
    host, port = "127.0.0.1", 5001
    if is_port_open(host, port):
        print("Whisper server already running")
        return
    print("Starting Whisper server...")
    proc = subprocess.Popen([sys.executable, str(WHISPER_SERVER)], cwd=str(BASE_DIR))
    for _ in range(30):
        if is_port_open(host, port):
            print("Whisper ready")
            return
        if proc.poll() is not None:
            raise RuntimeError("Whisper server exited unexpectedly")
        time.sleep(1)
    raise RuntimeError("Whisper server failed to start")

# -------------------------
# Audio
# -------------------------
def start_record():
    global rec
    notify("🎤 Recording...")
    rec = subprocess.Popen([
        "arecord",
        "-f", "S16_LE",
        "-r", "16000",
        "-c", "1",
        "-t", "wav",
        config.AUDIO_FILE
    ])

def stop_record():
    global rec
    if rec:
        # Petit buffer pour éviter d’avoir un fichier trop court
        time.sleep(0.2)
        rec.send_signal(signal.SIGINT)
        rec.wait()

    # Vérifier durée pour éviter hallucinations
    if not os.path.exists(config.AUDIO_FILE):
        notify("⚠️ Fichier audio manquant")
        return

    with wave.open(config.AUDIO_FILE, "rb") as f:
        duration = f.getnframes() / f.getframerate()
    if duration < 0.5:
        notify("⚠️ Segment trop court, pas de transcription")
        return

    notify("Transcribing...")
    transcribe()

# -------------------------
# Whisper transcription
# -------------------------
def transcribe():
    try:
        r = requests.post(
            config.WHISPER_URL,
            json={"file_path": config.AUDIO_FILE},
            timeout=120
        )
        text = r.json().get("text", "")
        if text:
            subprocess.run(["xdotool", "type", text])
            subprocess.run(["xdotool", "key", "Return"])
    except Exception as e:
        print("Whisper error:", e)

# -------------------------
# Keyboard
# -------------------------
def find_keyboard():
    devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
    for d in devices:
        if "keyboard" in d.name.lower():
            return d
    if devices:
        return devices[0]
    raise RuntimeError("Aucun clavier trouvé")

# -------------------------
# Main
# -------------------------
def main():
    global recording
    ensure_whisper()
    device = find_keyboard()
    print("Using keyboard:", device)

    try:
        device.grab()
    except:
        print("Impossible de grab le clavier, vérifier les permissions / sudo")

    ui = UInput.from_device(device)

    for event in device.read_loop():
        if event.type == ecodes.EV_KEY:
            key = categorize(event)
            if key.scancode == config.KEY_TRIGGER:
                if key.keystate == key.key_down and not recording:
                    recording = True
                    start_record()
                elif key.keystate == key.key_up and recording:
                    recording = False
                    stop_record()
            else:
                ui.write_event(event)
                ui.syn()

if __name__ == "__main__":
    main()