
# AI Voice Assistant — Linux (Faster-Whisper)

# 🎤 Speech Recognition System (Yes/No Classifier + Whisper)


<div align="center">

![Python](https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web_App-black?style=for-the-badge&logo=flask)
![TensorFlow](https://img.shields.io/badge/TensorFlow-DeepLearning-orange?style=for-the-badge&logo=tensorflow)
![Librosa](https://img.shields.io/badge/Librosa-AudioProcessing-purple?style=for-the-badge)
![Whisper](https://img.shields.io/badge/OpenAI-Whisper-green?style=for-the-badge)
![JavaScript](https://img.shields.io/badge/Frontend-JS-yellow?style=for-the-badge&logo=javascript)

</div>

---

## 📌 Overview

This is an **end-to-end Speech Recognition System** that combines:

- 🧠 **Speech-to-Text (Whisper)**
- 🤖 **Custom ML Classification (Yes/No)**
- 🌐 **Flask Web App Interface**

It allows users to **record voice, transcribe it, and classify it in real-time**.

---

## 🎯 Key Features


- Real-time voice recording (browser microphone)
- Audio file upload (WAV, MP3, WebM, OGG, FLAC, M4A)
- Faster-Whisper large-v3 with int8 quantisation (CPU optimised)
- Multi-Language Translation Suite with 17+ languages & custom language support
- Hands-free Voice Language Selection (e.g. “Translate this to Hindi”)
- Dual Translation Display preserving original transcription
- One-click Copy, Download (.txt), and Listen (Text-to-Speech)
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
│   ├── translator.py        # Modular multi-language translation engine
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

- 🎤 Real-time voice recording (browser)
- 🔄 Audio format conversion (WebM → WAV)
- 🧠 Whisper-based speech-to-text (offline)
- 🤖 ML model for Yes/No classification
- 📊 Spectrogram generation
- 🌐 Interactive Flask web app

---

## 📸 Screenshots


> ⚠️ Add your screenshots here

```html
<!-- Example -->
<img width="2560" height="1244" alt="Screenshot 2026-06-11 212852" src="https://github.com/user-attachments/assets/a677b55e-8d2e-4dc0-a139-43f16b0f6e32" />
<img width="2560" height="1252" alt="Screenshot 2026-06-11 212915" src="https://github.com/user-attachments/assets/727616f5-6491-4648-9261-18e31540a43d" />

🛠️ Tech Stack
🔹 Languages
Python

JavaScript

HTML

CSS

🔹 Libraries & Frameworks
Flask

NumPy

Librosa

TensorFlow / Keras

OpenAI Whisper

🔹 Tools
FFmpeg

Git & GitHub

VS Code

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
🏗️ Project Structure
SPEECH-RECOGNITION/
│
├── app.py                 # Main Flask app
├── requirements.txt       # Dependencies
├── test.py                # Model testing
│
├── data/
│   ├── yes/
│   └── no/
│
├── model/
│   ├── model.py
│   ├── speech_model.keras
│   └── label_map.json
│
├── utils/
│   ├── audio_processing.py
│   ├── dataset.py
│   └── predict.py
│
├── static/
│   ├── uploads/
│   ├── spectrograms/
│   ├── script.js
│   └── style.css
│
├── templates/
│   └── index.html
⚙️ Installation & Setup
1️⃣ Clone Repository
git clone <your-repo-link>
cd SPEECH-RECOGNITION
2️⃣ Create Virtual Environment
python -m venv .venv
.venv\Scripts\activate
3️⃣ Install Dependencies
pip install -r requirements.txt
▶️ Run Application
python app.py
Open in browser:


http://127.0.0.1:5000
🧠 How It Works
🎤 User records audio

🔄 Audio converted to WAV


**Request:**

```json
{
  "confirmation_token": "<token from /transcribe>",
  "confirmed": true
}
```

🧠 Whisper transcribes speech


🤖 ML model predicts YES/NO

📊 Spectrogram generated

📊 Model Details
Feature Extraction: MFCC


## 🧠 Supported Voice Commands

| Voice Input           | Action                      | Dangerous? |
| --------------------- | --------------------------- | ---------- |
| "open browser"        | Opens default browser       | No         |
| "open terminal"       | Opens GNOME terminal        | No         |
| "list files"          | Lists files (`ls -la`)      | No         |
| "check disk space"    | Shows disk usage (`df -h`)  | No         |
| "check memory"        | Shows RAM usage (`free -h`) | No         |
| "what time is it"     | Returns current date/time   | No         |
| "take screenshot"     | Takes screenshot            | No         |
| "open file manager"   | Opens Nautilus              | No         |
| "system info"         | Shows OS info (`uname -a`)  | No         |
| "play music"          | Opens media player          | No         |
| "ip address"          | Shows IP address            | No         |
| "uptime"              | Shows system uptime         | No         |
| **"shutdown system"** | Shuts down system           | **⚠️ Yes** |
| **"reboot"**          | Reboots system              | **⚠️ Yes** |
| **"delete files"**    | Blocked for safety          | **⚠️ Yes** |
| **"system update"**   | Runs `apt update`           | **⚠️ Yes** |

Model Type: Neural Network (Keras)


Input Shape: (timesteps, features)

Output: Binary (Yes / No)

⚠️ Important Notes
Whisper runs locally → no API key needed

First run may take time (model loading)


## 🌐 Translation Suite

### API Endpoint: `POST /translate`

Request:
```json
{
  "text": "Good morning everyone, welcome to my presentation.",
  "target_language": "Hindi"
}
```

Response:
```json
{
  "status": "success",
  "source_text": "Good morning everyone, welcome to my presentation.",
  "translated_text": "सभी को सुप्रभात, मेरी प्रस्तुति में आपका स्वागत है।",
  "target_language": "Hindi",
  "source_language": "en"
}
```

### Voice Language Commands
Users can speak natural translation commands directly after recording:
- *"Translate this into English."*
- *"Translate this to Hindi."*
- *"Translate my last transcription into Hindi."*
- *"Convert this to Spanish."*
- *"Give me the Hindi translation."*

The system automatically detects the requested target language and translates the latest transcription while preserving the original.

---

## ❌ Error Handling

| Scenario          | Error Message                           |
| ----------------- | --------------------------------------- |
| No audio uploaded | "No audio input detected"               |
| Whisper fails     | "Transcription failed"                  |
| No command match  | Returns transcription only (no command) |

Ensure FFmpeg is installed/configured

🔮 Future Improvements
🎯 Multi-class classification


🌍 Multi-language support

⚡ Faster inference

📱 Mobile compatibility

👩‍💻 Author
Ashmita Goyal

⭐ Show Some Love
If you liked this project, give it a ⭐ on GitHub!


---

## 🔥 Extra Pro Tips (THIS matters)

👉 Screenshot section:
- UI ka screenshot
- spectrogram output
- prediction result

👉 Add later:
```markdown
## 🎥 Demo Video
[Watch Demo](your-link)
