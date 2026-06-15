# 🎤 AI Voice Assistant — Linux (Faster-Whisper)

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web_App-black?style=for-the-badge&logo=flask)
![Whisper](https://img.shields.io/badge/Faster--Whisper-large--v3-green?style=for-the-badge)
![Linux](https://img.shields.io/badge/Linux-Compatible-orange?style=for-the-badge&logo=linux)
![JavaScript](https://img.shields.io/badge/Frontend-JS-yellow?style=for-the-badge&logo=javascript)

</div>

---

## 📌 Overview

A **Linux-compatible AI voice assistant** powered by **Faster-Whisper (large-v3)**.

- 🎤 **Speech-to-Text** — Accurate transcription using Faster-Whisper
- 🧠 **Intent Detection** — Recognises voice commands from transcribed text
- ⚡ **Command Execution** — Runs Linux system commands directly
- 🛡️ **Safety Rules** — Dangerous commands require explicit confirmation
- 🌐 **Flask Web App** — Premium dark-themed chat UI

---

## 🎯 Key Features

- Real-time voice recording (browser microphone)
- Audio file upload (WAV, MP3, WebM, OGG, FLAC, M4A)
- Faster-Whisper large-v3 with int8 quantisation (CPU optimised)
- One-time model loading at startup
- Linux system command execution
- Dangerous command confirmation flow
- Waveform visualisation during recording
- Chat-style conversational interface

---

## 🏗️ Project Structure

```
SPEECH-RECOGNITION/
│
├── app.py                   # Flask application (routes)
├── requirements.txt         # Python dependencies
├── .gitignore               # Git ignore rules
├── README.md                # This file
│
├── utils/
│   ├── predict.py           # Faster-Whisper transcription engine
│   ├── commands.py          # Command detection & execution
│   ├── audio_processing.py  # Audio conversion utilities
│   └── dataset.py           # Dataset loader (training)
│
├── model/
│   ├── model.py             # Keras model definition (training)
│   └── label_map.json       # Label mapping
│
├── static/
│   ├── script.js            # Frontend JavaScript
│   ├── style.css            # CSS (dark glassmorphism)
│   ├── uploads/             # Temporary audio uploads
│   └── spectrograms/        # Generated spectrograms
│
├── templates/
│   └── index.html           # Voice assistant UI
│
└── test.py                  # Model training script
```

---

## ⚙️ Installation & Setup (Linux)

### 1️⃣ Prerequisites

```bash
sudo apt update
sudo apt install ffmpeg -y
```

### 2️⃣ Clone & Setup

```bash
git clone https://github.com/Ashmita1206/Speech-Recognition.git
cd Speech-Recognition
git checkout feature/voice-assistant-linux
```

### 3️⃣ Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 5️⃣ Run Application

```bash
python3 app.py
```

Open in browser: **http://localhost:5000**

> ⚠️ First run will download the Faster-Whisper large-v3 model (~3 GB).

---

## 📡 API Endpoints

### `POST /transcribe`

Accept audio, transcribe, detect & execute commands.

**Request:** `multipart/form-data` with `audio` file field.

**Response:**
```json
{
  "transcription": "open the browser",
  "command": {
    "intent": "open_browser",
    "action": "xdg-open https://google.com",
    "executed": true,
    "requires_confirmation": false,
    "output": "Command executed successfully."
  },
  "status": "success"
}
```

### `POST /execute`

Confirm and execute a dangerous command.

**Request:**
```json
{
  "confirmation_token": "<token from /transcribe>",
  "confirmed": true
}
```

### `POST /predict` (Legacy)

Backward-compatible alias for `/transcribe`.

---

## 🧠 Supported Voice Commands

| Voice Input | Action | Dangerous? |
|---|---|---|
| "open browser" | Opens default browser | No |
| "open terminal" | Opens GNOME terminal | No |
| "list files" | Lists files (`ls -la`) | No |
| "check disk space" | Shows disk usage (`df -h`) | No |
| "check memory" | Shows RAM usage (`free -h`) | No |
| "what time is it" | Returns current date/time | No |
| "take screenshot" | Takes screenshot | No |
| "open file manager" | Opens Nautilus | No |
| "system info" | Shows OS info (`uname -a`) | No |
| "play music" | Opens media player | No |
| "ip address" | Shows IP address | No |
| "uptime" | Shows system uptime | No |
| **"shutdown system"** | Shuts down system | **⚠️ Yes** |
| **"reboot"** | Reboots system | **⚠️ Yes** |
| **"delete files"** | Blocked for safety | **⚠️ Yes** |
| **"system update"** | Runs `apt update` | **⚠️ Yes** |

---

## ⚠️ Safety Rules

- Dangerous commands (shutdown, reboot, delete, system update) are **never executed automatically**
- The system returns a confirmation token
- The user must explicitly confirm via the UI before execution
- File deletion commands are **always blocked**

---

## ❌ Error Handling

| Scenario | Error Message |
|---|---|
| No audio uploaded | "No audio input detected" |
| Whisper fails | "Transcription failed" |
| No command match | Returns transcription only (no command) |

---

## ⚡ Performance

- **Model loaded once** at startup (global singleton)
- **CPU optimisation** with int8 quantisation (CTranslate2)
- **VAD filter** enabled to skip silence
- **Beam search** (size=5) for accuracy

---

## 🔮 Future Improvements

- 🎯 Custom wake word detection
- 🌍 Multi-language voice commands
- 🔊 Text-to-Speech responses
- 📱 Mobile-optimised UI
- 🔌 Plugin system for custom commands

---

## 👩‍💻 Author

**Ashmita Goyal**

⭐ If you liked this project, give it a ⭐ on GitHub!
