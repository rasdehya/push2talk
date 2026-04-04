#!/usr/bin/env python3
"""
Détecte la présence du micro USB et lance/arrête push2talk.py en conséquence.

Ce script est optionnel : push2talk.py intègre déjà sa propre détection.
Il n'est utile que si tu veux un superviseur externe.
"""

import logging
import pathlib
import signal
import subprocess
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("detect_micro")

BASE_DIR = pathlib.Path(__file__).resolve().parent
PUSH2TALK_SCRIPT = BASE_DIR / "push2talk.sh"
MIC_NAME = "USB MICROPHONE"


def find_mic() -> bool:
    try:
        result = subprocess.run(
            ["arecord", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return MIC_NAME in result.stdout
    except Exception:
        return False


def main() -> None:
    proc: subprocess.Popen[bytes] | None = None
    mic_connected = False

    def stop_ptt() -> None:
        nonlocal proc
        if proc is not None:
            log.info("Arrêt de Push2Talk…")
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            proc = None
            log.info("Push2Talk arrêté.")

    def start_ptt() -> None:
        nonlocal proc
        if proc is None:
            log.info("Démarrage de Push2Talk…")
            proc = subprocess.Popen([str(PUSH2TALK_SCRIPT)])

    def _handle_signal(signum: int, _frame) -> None:
        log.info("Signal %d reçu.", signum)
        stop_ptt()
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    log.info("Surveillance du micro '%s'…", MIC_NAME)

    try:
        while True:
            detected = find_mic()
            if detected and not mic_connected:
                mic_connected = True
                start_ptt()
            elif not detected and mic_connected:
                mic_connected = False
                stop_ptt()
            time.sleep(2)
    except KeyboardInterrupt:
        stop_ptt()


if __name__ == "__main__":
    main()
