"""
Voice Assistant App — Flask Backend
====================================
Linux-compatible AI voice assistant powered by Faster-Whisper (large-v3).

Routes:
  GET  /            → Serve the frontend
  POST /transcribe  → Accept audio, transcribe, detect & execute commands
  POST /execute     → Confirm and execute a dangerous command
  POST /predict     → Legacy alias for /transcribe (backward compat)
"""

import os
import uuid
from flask import Flask, request, jsonify, render_template, url_for

# Import audio_processing FIRST — it configures ffmpeg for pydub
from utils.audio_processing import (
    convert_to_wav,
    is_supported_format,
    load_audio,
    generate_spectrogram,
)
from utils.predict import transcribe_audio
from utils.commands import confirm_and_execute

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


@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    Accept an uploaded audio file, transcribe it with Faster-Whisper,
    detect commands, and execute safe ones automatically.

    Returns JSON:
        {
          "transcription": "<clean text>",
          "command": {
              "intent": "...",
              "action": "...",
              "executed": true/false,
              "requires_confirmation": true/false,
              "confirmation_token": "..." (if confirmation needed),
              "warning": "..." (if confirmation needed),
              "output": "..."
          } or null,
          "status": "success" or "error"
        }
    """
    try:
        # ----- Validate input -----
        if 'audio' not in request.files:
            return jsonify({
                "transcription": "",
                "command": None,
                "status": "error",
                "error": "No audio input detected",
            }), 400

        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({
                "transcription": "",
                "command": None,
                "status": "error",
                "error": "No audio input detected",
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
        convert_to_wav(raw_path, wav_path)

        # ----- Transcribe & detect commands -----
        result = transcribe_audio(wav_path)

        # ----- Clean up temp files -----
        try:
            if os.path.exists(raw_path) and raw_path != wav_path:
                os.remove(raw_path)
            if os.path.exists(wav_path):
                os.remove(wav_path)
        except OSError:
            pass  # Non-critical cleanup

        # ----- Return response -----
        status_code = 200 if result.get("status") == "success" else 500
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "transcription": "",
            "command": None,
            "status": "error",
            "error": f"Transcription failed: {str(e)}",
        }), 500


@app.route('/execute', methods=['POST'])
def execute():
    """
    Confirm and execute a dangerous command.

    Expects JSON:
        {
          "confirmation_token": "<token from /transcribe>",
          "confirmed": true
        }

    Returns JSON with execution result.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "error": "Invalid request body",
            }), 400

        token = data.get("confirmation_token")
        confirmed = data.get("confirmed", False)

        if not token or not confirmed:
            return jsonify({
                "status": "error",
                "error": "Missing confirmation token or confirmation flag",
            }), 400

        result = confirm_and_execute(token)

        return jsonify({
            "command": result,
            "status": "success" if result.get("executed") else "error",
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": f"Execution failed: {str(e)}",
        }), 500


# --- Legacy alias ---
@app.route('/predict', methods=['POST'])
def predict():
    """Backward-compatible alias for /transcribe."""
    return transcribe()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
