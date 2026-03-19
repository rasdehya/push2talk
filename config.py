import os

KEY_TRIGGER = 41  					# Correspond a la touche "œ" 
AUDIO_FILE = "/tmp/ptt_record.wav"
WHISPER_URL = "http://127.0.0.1:5001/transcribe"
ICON = "./mic-on.png"
USER = os.getlogin()

#MIC_NAME = "USB MICROPHONE"
MIC_NAME = "ALC257 Analog"

# ---------------------------------------------------------------------------
# Whisper
# ---------------------------------------------------------------------------
WHISPER_MODEL = "medium"       		# small = bon compromis vitesse/qualité
WHISPER_DEVICE = "cuda"       		# "cuda" si GPU Nvidia, sinon "cpu"
WHISPER_COMPUTE_TYPE = "float16"  	# "float16" sur GPU, "int8" sur CPU
WHISPER_LANGUAGE = "fr"
WHISPER_BEAM_SIZE = 5         		# 1 = greedy, plus rapide, quasi même qualité
WHISPER_VAD_FILTER = True    		# supprime les silences avant transcription
WHISPER_VAD_THRESHOLD = 0.5  		# 0.0-1.0, plus bas = plus permissif (défaut 0.5)

# ---------------------------------------------------------------------------
# Enregistrement
# ---------------------------------------------------------------------------
MIN_RECORD_DURATION = 0.5    		# durée minimale en secondes pour lancer la transcription