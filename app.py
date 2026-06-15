"""
Speech Recognition App – Flask Backend
=======================================
Powered by OpenAI Whisper (local model, no API key required).

Routes:
  GET  /         → Serve the frontend
  POST /predict  → Accept audio, transcribe, classify (YES / NO / UNKNOWN)
"""

import os
import uuid
from flask import Flask, request, jsonify, render_template, url_for

# Import audio_processing FIRST — it configures ffmpeg for pydub + Whisper
from utils.audio_processing import (
    convert_to_wav,
    is_supported_format,
    load_audio,
    generate_spectrogram,
)
from utils.predict import predict_audio

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
SPECTROGRAM_FOLDER = os.path.join('static', 'spectrograms')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SPECTROGRAM_FOLDER, exist_ok=True)

# Allowed extensions for upload validation
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'webm', 'ogg', 'flac', 'm4a'}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    """
    Accept an uploaded audio file, transcribe it with Whisper,
    and classify the speech as YES / NO / UNKNOWN.

    Returns JSON:
        {
          "success": true/false,
          "transcription": "...",
          "prediction": "YES" | "NO" | "UNKNOWN",
          "confidence": "87.32%",
          "spectrogram": "/static/spectrograms/xxx.png",
          "error": "..."   (only when success is false)
        }
    """
    try:
        # ----- Validate input -----
        if 'audio' not in request.files:
            return jsonify({
                "success": False,
                "error": "No audio file uploaded. Please send a file with key 'audio'."
            }), 400

        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({
                "success": False,
                "error": "Empty filename."
            }), 400

        # ----- Save uploaded file -----
        unique_id = str(uuid.uuid4())
        original_ext = os.path.splitext(audio_file.filename)[1].lower()

        # Default to .webm for recordings that come without a known extension
        if not original_ext:
            original_ext = '.webm'

        raw_filename = f"{unique_id}{original_ext}"
        raw_path = os.path.join(UPLOAD_FOLDER, raw_filename)
        audio_file.save(raw_path)

        # ----- Convert to 16 kHz mono WAV (for Whisper) -----
        wav_filename = f"{unique_id}.wav"
        wav_path = os.path.join(UPLOAD_FOLDER, wav_filename)

        if original_ext != '.wav':
            convert_to_wav(raw_path, wav_path)
        else:
            # Even if already .wav, normalise to 16 kHz mono
            convert_to_wav(raw_path, wav_path)

        # ----- Generate spectrogram (optional visual) -----
        spectrogram_url = None
        audio_data, sr = load_audio(wav_path)
        if audio_data is not None:
            spec_filename = f"{unique_id}_spec.png"
            spec_path = os.path.join(SPECTROGRAM_FOLDER, spec_filename)
            generate_spectrogram(audio_data, sr, spec_path)
            spectrogram_url = url_for('static', filename=f"spectrograms/{spec_filename}")

        # ----- Transcribe & classify -----
        result = predict_audio(wav_path)

        if not result.get("success"):
            return jsonify({
                "success": False,
                "error": result.get("error", "Unknown prediction error."),
            }), 500

        # ----- Return response -----
        return jsonify({
            "success": True,
            "transcription": result["transcription"],
            "prediction": result["prediction"],
            "confidence": result["confidence"],
            "spectrogram": spectrogram_url,
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Server error: {str(e)}",
        }), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
