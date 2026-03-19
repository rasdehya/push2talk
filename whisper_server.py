from flask import Flask, request, jsonify
from faster_whisper import WhisperModel
import os
import config

app = Flask(__name__)

print(f"Loading Whisper model '{config.WHISPER_MODEL}' on {config.WHISPER_DEVICE} ({config.WHISPER_COMPUTE_TYPE})…")
model = WhisperModel(
    config.WHISPER_MODEL,
    device=config.WHISPER_DEVICE,
    compute_type=config.WHISPER_COMPUTE_TYPE,
)
print("Whisper ready")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.json
    path = data["file_path"]
    if not os.path.exists(path):
        return jsonify({"error": "file missing"}), 400
    segments, _ = model.transcribe(
        path,
        language=config.WHISPER_LANGUAGE,
        beam_size=config.WHISPER_BEAM_SIZE,
        vad_filter=config.WHISPER_VAD_FILTER,
        temperature=0.0,
        condition_on_previous_text=False,
        no_speech_threshold=0.6,  # rejette si probabilité de silence > 60%
    )
    text = " ".join(seg.text for seg in segments)
    return jsonify({"text": text.strip()})


@app.route("/")
def health():
    return "ok"


if __name__ == "__main__":
    # from waitress import serve
    # serve(app, host="127.0.0.1", port=5001)
    app.run("127.0.0.1", 5001)
