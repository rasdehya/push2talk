# push2talk

# Push2Talk 🎤

Un outil d'assistance vocale léger et efficace qui permet d'utiliser la reconnaissance vocale avec un simple appui sur une touche (push-to-talk).

## 🌟 Fonctionnalités

- **Reconnaissance vocale en temps réel** : Utilise la technologie Whisper optimisée (faster-whisper) pour une transcription rapide
- **Push-to-talk** : Contrôle l'enregistrement audio via une touche dédiée (configurable)
- **Micro détection** : Détection du micro automatique. Le serveur whisper se lance et le script demarre
- **Interface système** : Icône de barre système (system tray) pour quitter facilement l'application
- **Serveur Flask intégré** : API pour intégrer l'outil dans d'autres applications
- **Support multi-plateforme** : Compatible Linux (Ubuntu/Debian)
- **Accélération GPU NVIDIA** : Support CUDA pour une performance optimale (optionnel)

## 📋 Prérequis

- **Linux** (Ubuntu 20.04+ ou Debian)
- **Python 3.10+**
- **Accès administrateur** (pour l'installation de dépendances système)
- **(Optionnel) GPU NVIDIA** avec CUDA pour de meilleures performances

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/rasdehya/push2talk.git
cd push2talk
```

### 2. Installation automatique

Exécutez le script d'installation qui installe toutes les dépendances système et Python :

```bash
chmod +x install.sh
./install.sh
```

### 3. Installation manuelle

Si vous préférez une installation étape par étape :
```bash
# Installez les dépendances système
sudo apt install -y python3-pip xdotool alsa-utils librsvg2-bin

# Créez un environnement virtuel
python3 -m venv venv
source venv/bin/activate
# Et installez les dépendances Python
pip install -r requirements.txt
# Ou en utilisant uv (wrapper pour pip, venv, etc...)
# curl -LsSf https://astral.sh/uv/install.sh | sh
uv init 
uv venv
uv pip install -r requirements.txt
```
### 4. Configuration (config.py)

- Modifier la bindkey qui declanche l'enregistrement. Utilisez `sudo showkey` pour obtenir le keycode
- Modifier le nom de votre micro. Utiliser `a record -l` pour trouver le nom du périphérique
- Si vous avez un GPU NVIDIA et souhaitez utiliser l'accélération CUDA :

```bash
# Après l'installation, decommentez et modifier les chemins des bibliothèques
export LD_LIBRARY_PATH=/chemin/vers/venv/lib/python3.12/site-packages/nvidia/cublas/lib:/chemin/vers/venv/lib/python3.12/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH
# Et modifier les variables 
WHISPER_DEVICE = "cuda"             # "cuda" si GPU Nvidia, sinon "cpu"
WHISPER_COMPUTE_TYPE = "float16"    # "float16" sur GPU, "int8" sur CPU
```
- Vous pouvez jouer avec les valeurs des variables suivantes pour faire varier la rapiditée/qualitée de la retranscription.
```bash
WHISPER_MODEL = "medium"          # small = bon compromis vitesse/qualité
WHISPER_BEAM_SIZE = 5             # 1 = greedy, plus rapide, quasi même qualité
WHISPER_VAD_FILTER = True       # supprime les silences avant transcription
WHISPER_VAD_THRESHOLD = 0.5     # 0.0-1.0, plus bas = plus permissif (défaut 0.5)
```

### Lancer l'application

```bash
chmod +x ./push2talk.sh
./push2talk.sh
```

## 🎮 Utilisation

- Appuyer sur la touche choisie pour lancer l'enregistrement ("œ" par default)
- Relacher pour copier dans la fenetre active suivi d'un envoie de la touche ENTER
- Vous pouvez quitter l'application en cliquant sur l'icone du systray

