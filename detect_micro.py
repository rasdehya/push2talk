#!/usr/bin/env python3
import subprocess
import time
import pathlib
import signal

print("=== Detect Micro Script lancé ===", flush=True)
BASE_DIR = pathlib.Path(__file__).resolve().parent
PUSH2TALK_SCRIPT = BASE_DIR / "push2talk.sh"  # ton script PTT existant

MIC_NAME = "USB MICROPHONE"  # change selon ton micro
proc = None

def find_mic():
    """Vérifie si le micro USB est branché"""
    result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
    return MIC_NAME in result.stdout

def start_ptt():
    global proc
    if proc is None:
        proc = subprocess.Popen([str(PUSH2TALK_SCRIPT)])
        print("Push2Talk lancé")

def stop_ptt():
    global proc
    if proc:
        proc.send_signal(signal.SIGINT)
        proc.wait()
        proc = None
        print("Push2Talk arrêté")

def main():
    mic_connected = False
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