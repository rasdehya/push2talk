# push2talk

# Push2Talk 🎤

Un outil d'assistance vocale léger et efficace qui permet d'utiliser la reconnaissance vocale avec un simple appui sur une touche (push-to-talk).

## 🌟 Fonctionnalités

- **Reconnaissance vocale en temps réel** : Utilise la technologie Whisper optimisée (faster-whisper) pour une transcription rapide
- **Push-to-talk** : Contrôle l'enregistrement audio via une touche dédiée (configurable)
- **Interface système** : Icône de barre système (system tray) pour un accès facile
- **Serveur Flask intégré** : API pour intégrer l'outil dans d'autres applications
- **Support multi-plateforme** : Compatible Linux (Ubuntu/Debian)
- **Accélération GPU NVIDIA** : Support CUDA pour une performance optimale (optionnel)

## 📋 Prérequis

- **Linux** (Ubuntu 20.04+ ou Debian)
- **Python 3.10+**
- **Microphone** fonctionnel
- **Accès administrateur** (pour l'installation de dépendances système)
- **(Optionnel) GPU NVIDIA** avec CUDA pour de meilleures performances

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/votre-username/push2talk.git
cd push2talk
```

### 2. Installation automatique (recommandée)

Exécutez le script d'installation qui installe toutes les dépendances système et Python :

```bash
chmod +x install.sh
./install.sh
```

### 3. Installation manuelle

Si vous préférez une installation étape par étape :

```bash
# Installez les dépendances système
sudo apt install \
  python3-pip \
  xdotool \
  alsa-utils \
  libnotify-bin \
  librsvg2-bin \
  -y

# Créez un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installez les dépendances Python
pip install -r requirements.txt
```

### 4. Configuration GPU (optionnel - NVIDIA uniquement)

Si vous avez un GPU NVIDIA et souhaitez utiliser l'accélération CUDA :

```bash
# Après l'installation, définissez les chemins des bibliothèques
export LD_LIBRARY_PATH=/chemin/vers/venv/lib/python3.12/site-packages/nvidia/cublas/lib:/chemin/vers/venv/lib/python3.12/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH
```

> **Note** : Remplacez `/chemin/vers/venv` par le chemin réel de votre environnement virtuel.

## 🎮 Utilisation

### Lancer l'application

```bash
./push2talk.sh
```
- Appuyer sur la touche pour lancer l'enregistrement
- Relacher pour copier dans la fenetre active suivi d'un envoie de la touche ENTER
 