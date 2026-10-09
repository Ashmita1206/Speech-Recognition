"""
Prediction module — Faster-Whisper speech-to-text.

Flow:
  1. Load Faster-Whisper model (with cache on D: drive where space is available).
  2. Transcribe incoming audio files (16 kHz mono WAV).
  3. Detect optional commands if configured.
  4. Return clean transcription and speech metadata.
"""

import os
import time

# ---------------------------------------------------------------------------
# Ensure ffmpeg is on PATH before Whisper tries to use it
# (Faster-Whisper calls ffmpeg via subprocess internally)
# ---------------------------------------------------------------------------
try:
    import imageio_ffmpeg
    _ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
    if _ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass  # Fall back to system ffmpeg

# Ensure HuggingFace cache is on D: drive where space is available
_cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".hf_cache"))
os.environ["HF_HOME"] = _cache_dir

from faster_whisper import WhisperModel
from utils.commands import detect_command, execute_command
from utils.script_normalizer import normalize_transcript

whisper_model = None

def get_whisper_model():
    """Load Faster-Whisper model with fallback for available RAM/disk space."""
    global whisper_model
    if whisper_model is None:
        model_name = os.environ.get("WHISPER_MODEL", "large-v3")
        print(f"[predict] Initializing Faster-Whisper model ({model_name}) using cache: {_cache_dir}…")
        try:
            whisper_model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=_cache_dir)
            print(f"[predict] Faster-Whisper model ({model_name}) loaded successfully.")
        except Exception as e:
            print(f"[predict] Warning loading {model_name}: {e}. Trying base model fallback...")
            try:
                whisper_model = WhisperModel("base", device="cpu", compute_type="int8", download_root=_cache_dir)
                print("[predict] Faster-Whisper base model loaded.")
            except Exception as e2:
                print(f"[predict] Fallback to tiny model: {e2}")
                whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root=_cache_dir)
                print("[predict] Whisper fallback model loaded.")
    return whisper_model


def transcribe_audio(audio_path: str, language_preference: str = None) -> dict:
    """
    Transcribe audio and return clean text and metadata.

    Args:
        audio_path: Path to a WAV file (16 kHz mono recommended).
        language_preference: Optional expected spoken language (e.g. 'hi', 'en', 'auto').

    Returns:
        dict matching the API response format:
        {
            "transcription": "<clean text>",
            "command": { ... } or null,
            "status": "success" | "error",
            "language": "<language code>",
            "duration": <seconds>,
            "processing_time": <seconds>,
            "error": "..." (only when status is "error")
        }
    """
    start_time = time.time()
    try:
        model = get_whisper_model()

        # Resolve language and initial prompt preference
        whisper_lang = None
        initial_prompt = None

        if language_preference:
            pref = language_preference.strip().lower()
            if pref in ("hi", "hindi"):
                whisper_lang = "hi"
                initial_prompt = "यह हिंदी में प्रतिलेखन है, देवनागरी लिपि में।"
            elif pref in ("en", "english"):
                whisper_lang = "en"
            elif pref != "auto":
                whisper_lang = pref

        # Transcribe with Faster-Whisper
        segments, info = model.transcribe(
            audio_path,
            beam_size=2,
            language=whisper_lang,
            initial_prompt=initial_prompt,
            vad_filter=False,     # avoids dependency on onnxruntime
        )

        # Collect all segment texts
        full_text_parts = []
        for segment in segments:
            full_text_parts.append(segment.text.strip())

        raw_transcription = " ".join(full_text_parts).strip()
        processing_time = round(time.time() - start_time, 2)
        detected_lang = getattr(info, "language", "en") if 'info' in locals() and info else "en"

        if not raw_transcription:
            return {
                "transcription": "",
                "command": None,
                "status": "error",
                "error": "No speech detected in audio",
                "language": detected_lang,
                "duration": round(getattr(info, "duration", 0.0), 2) if 'info' in locals() and info else 0.0,
                "processing_time": processing_time,
            }

        # Normalize script (ensures consistent Devanagari for Hindi, leaves English/others clean)
        transcription = normalize_transcript(
            raw_transcription,
            detected_language=detected_lang,
            language_preference=language_preference,
        )

        # Optional command detection (preserved for backward compatibility)
        cmd_info = detect_command(transcription)
        command_result = None
        if cmd_info is not None:
            try:
                command_result = execute_command(cmd_info)
            except Exception:
                command_result = None

        return {
            "transcription": transcription,
            "command": command_result,
            "status": "success",
            "language": detected_lang,
            "duration": round(getattr(info, "duration", 0.0), 2) if 'info' in locals() and info else 0.0,
            "processing_time": processing_time,
        }

    except Exception as e:
        processing_time = round(time.time() - start_time, 2)
        return {
            "transcription": "",
            "command": None,
            "status": "error",
            "error": f"Transcription failed: {str(e)}",
            "language": "en",
            "duration": 0.0,
            "processing_time": processing_time,
        }
