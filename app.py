"""
Voice Assistant App — Flask Backend
====================================
Speech recognition and translation web application powered by Faster-Whisper.

Routes:
  GET  /            → Serve the frontend
  POST /transcribe  → Accept audio, transcribe, detect commands
  POST /execute     → Confirm and execute dangerous command (security protected)
  POST /predict     → Legacy alias for /transcribe (backward compat)
  POST /translate   → Multilingual text translation
  GET  /languages   → Supported primary languages listing
"""

import os
import uuid
from flask import Flask, request, jsonify, render_template

# Import audio_processing FIRST — it configures ffmpeg for pydub
from utils.audio_processing import (
    convert_to_wav,
    is_supported_format,
    load_audio,
    generate_spectrogram,
)
from utils.predict import transcribe_audio, predict_audio
try:
    from utils.commands import confirm_and_execute, is_system_commands_enabled
except ImportError:
    confirm_and_execute = None
    is_system_commands_enabled = lambda: False
from utils.translator import translate_text, get_supported_languages

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Max upload size: 25 MB
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024

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
    detect commands, and return normalized transcript and metadata.
    """
    raw_path = None
    wav_path = None
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
        if not audio_file or not audio_file.filename:
            return jsonify({
                "transcription": "",
                "command": None,
                "status": "error",
                "error": "No audio input detected",
            }), 400

        # ----- Validate extension -----
        unique_id = str(uuid.uuid4())
        original_ext = os.path.splitext(audio_file.filename)[1].lower()

        # Default to .webm for raw microphone recordings that lack an explicit extension
        if not original_ext:
            original_ext = '.webm'

        ext_check = original_ext.lstrip('.')
        if ext_check not in ALLOWED_EXTENSIONS:
            return jsonify({
                "transcription": "",
                "command": None,
                "status": "error",
                "error": f"Unsupported audio format '{original_ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            }), 400

        raw_filename = f"{unique_id}{original_ext}"
        raw_path = os.path.join(UPLOAD_FOLDER, raw_filename)
        audio_file.save(raw_path)

        # ----- Convert to 16 kHz mono WAV (for Whisper) -----
        wav_filename = f"{unique_id}.wav"
        wav_path = os.path.join(UPLOAD_FOLDER, wav_filename)
        convert_to_wav(raw_path, wav_path)

        # Optional language preference (e.g., 'hi', 'en', 'auto')
        language_pref = (
            request.form.get("language")
            or request.form.get("language_preference")
            or request.args.get("language")
        )

        # ----- Transcribe & detect commands -----
        result = transcribe_audio(wav_path, language_preference=language_pref)
        status_code = 200 if result.get("status") == "success" else 500
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            "transcription": "",
            "command": None,
            "status": "error",
            "error": f"Transcription failed: {str(e)}",
        }), 500

    finally:
        # Clean up transient audio files from disk to prevent storage leaks
        try:
            if raw_path and os.path.exists(raw_path) and raw_path != wav_path:
                os.remove(raw_path)
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)
        except OSError:
            pass


@app.route('/execute', methods=['POST'])
def execute():
    """
    Confirm and execute a dangerous command after explicit user confirmation.
    Enforces security gate: blocked if ENABLE_SYSTEM_COMMANDS is false.
    """
    try:
        # Enforce server security policy: reject anonymous remote execution
        if not is_system_commands_enabled():
            return jsonify({
                "status": "error",
                "error": "System command execution is disabled on this server for security.",
            }), 403

        data = request.get_json(silent=True)
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

        if not callable(confirm_and_execute):
            return jsonify({
                "status": "error",
                "error": "Command execution module is not available",
            }), 501

        result = confirm_and_execute(token)
        return jsonify({
            "command": result,
            "status": "success" if result.get("executed") else "error",
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "error": "Command execution failed.",
        }), 500


# --- Legacy alias ---
@app.route('/predict', methods=['POST'])
def predict():
    """Backward-compatible alias for /transcribe."""
    return transcribe()


@app.route('/translate', methods=['POST'])
def translate():
    """
    Multilingual translation endpoint.
    Expects JSON:
        {
          "text": "Good morning everyone",
          "target_language": "Hindi",
          "source_language": "en" (optional)
        }
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                "status": "error",
                "error": "Invalid request body",
            }), 400

        text = data.get("text", "").strip()
        target_language = data.get("target_language", "").strip()
        source_language = data.get("source_language", None)

        if not text:
            return jsonify({
                "status": "error",
                "error": "No text provided to translate.",
            }), 400

        if not target_language:
            return jsonify({
                "status": "error",
                "error": "No target language specified.",
            }), 400

        result = translate_text(text, target_language, source_language)
        status_code = 200 if result.get("status") == "success" else 400
        return jsonify(result), status_code

    except Exception:
        return jsonify({
            "status": "error",
            "error": "Translation couldn't be completed.",
        }), 500


@app.route('/languages', methods=['GET'])
def languages():
    """Return available primary translation languages."""
    return jsonify({
        "status": "success",
        "languages": list(get_supported_languages().keys()),
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
