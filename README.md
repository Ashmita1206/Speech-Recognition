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

🧠 Whisper transcribes speech

🤖 ML model predicts YES/NO

📊 Spectrogram generated

📊 Model Details
Feature Extraction: MFCC

Model Type: Neural Network (Keras)

Input Shape: (timesteps, features)

Output: Binary (Yes / No)

⚠️ Important Notes
Whisper runs locally → no API key needed

First run may take time (model loading)

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
