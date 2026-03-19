# Push-to-Talk avec Whisper — Documentation pour LLM

## Objectif

Ce projet implémente un outil Push-to-Talk (PTT) pour clavier sous Linux, utilisant le modèle Whisper pour la transcription audio. Il permet à l'utilisateur d'appuyer sur une touche pour enregistrer, puis de relâcher la touche pour envoyer l'audio à Whisper et injecter le texte dans l'application active.

## Architecture

### 1. Composants principaux

1. **push_to_talk.py** — script principal

   * Gestion du clavier et détection de la touche Push-to-Talk.
   * Enregistrement audio avec `arecord`.
   * Transcription avec Whisper via serveur Flask.
   * Réinjection du texte dans la fenêtre active avec `xdotool`.
   * Notifications système avec `notify-send`.

2. **whisper_server.py** — serveur de transcription

   * Serveur Flask exposant un endpoint `/transcribe`.
   * Charge le modèle Whisper (`small` ou `medium` selon précision souhaitée).
   * Reçoit un chemin de fichier WAV et retourne la transcription JSON.

3. **config.py** — configuration

   * `KEY_TRIGGER`: code de la touche clavier déclencheur.
   * `AUDIO_FILE`: chemin temporaire du fichier audio.
   * `WHISPER_URL`: URL du serveur Whisper (`http://127.0.0.1:5001/transcribe`).
   * `ICON`: chemin absolu d'une icône pour les notifications.

### 2. Permissions et dépendances

* **/dev/input/event*** : lecture par l'utilisateur, souvent via groupe `input`.
* **/dev/uinput** : écriture pour UInput, règles udev nécessaires.
* Dépendances Python : `evdev`, `requests`, `xdotool` (CLI), `Flask`, `faster_whisper`.
* Python >= 3.10 recommandé.

### 3. Fonctionnement

1. **Initialisation**

   * `push_to_talk.py` vérifie si le serveur Whisper est actif.
   * Si non, démarre `whisper_server.py`.

2. **Détection clavier**

   * Trouve le clavier par nom contenant `keyboard`.
   * Utilise `evdev` pour lire les événements.

3. **Push-to-Talk**

   * Appui sur `KEY_TRIGGER` → `arecord` démarre l’enregistrement audio mono 16kHz.
   * Relâchement → `arecord` stoppe, fichier WAV vérifié pour durée ≥ 0.5 s.
   * Transcription via Whisper POST JSON.
   * Texte injecté avec `xdotool type` + `Return`.

4. **Notifications**

   * `notify-send` avec icône PNG/SVG absolue pour XFCE.

### 4. Comportement attendu

* Détection Push-to-Talk rapide.
* Segments trop courts ignorés pour éviter hallucinations.
* Transcription après relâchement de la touche.
* Délai ~2s pour traitement complet avec modèle `small`.
* Fonctionne sans `sudo` si `/dev/uinput` est correctement configuré.

### 5. Limitations

* Pas de transcription en temps réel (mode bloc).
* Hallucinations possibles sur segments < 0.5 s.
* Délai dû à la taille du segment et temps de traitement de Whisper.
* Icône notifications dépend du support XFCE et chemin absolu.

### 6. Suggestions d’amélioration pour LLM

* Implémenter streaming audio pour transcription quasi temps réel.
* Ajouter threading pour lancer Whisper pendant que le fichier se ferme.
* Supporter différents modèles Whisper (`small`, `medium`, `large`) pour ajuster précision/performance.
* Filtrage intelligent des segments silencieux pour réduire hallucinations.
* Interface graphique ou CLI pour configurer touches et fichiers audio.

---

Ce fichier fournit à n’importe quel LLM toutes les informations pour **comprendre et recréer l’outil Push-to-Talk complet avec Whisper sous Linux**, y compris architecture, dépendances, permissions et comportements.
