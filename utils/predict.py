"""
Prediction module — Faster-Whisper speech-to-text.

Flow:
  1. Load Faster-Whisper model (with environment-configurable cache path).
  2. Transcribe incoming audio files (16 kHz mono WAV).
  3. Detect optional commands if configured.
  4. Return clean transcription, script-normalized text, and speech metadata.
"""

import os
import time

# ---------------------------------------------------------------------------
# Ensure ffmpeg is on PATH before Whisper tries to use it
# (Faster-Whisper calls ffmpeg via subprocess internally)
# ---------------------------------------------------------------------------
try:
    import imageio_ffmpeg
    _ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    _ffmpeg_dir = os.path.dirname(_ffmpeg_exe)
    if _ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass  # Fall back to system ffmpeg

# ---------------------------------------------------------------------------
# Hugging Face Model Cache Configuration
# Supports HF_HOME or WHISPER_CACHE_DIR from environment; defaults to local .hf_cache
# ---------------------------------------------------------------------------
_env_cache = os.environ.get("HF_HOME") or os.environ.get("WHISPER_CACHE_DIR")
if _env_cache:
    _cache_dir = os.path.abspath(_env_cache)
else:
    _cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".hf_cache"))
    os.environ["HF_HOME"] = _cache_dir

from faster_whisper import WhisperModel
from utils.script_normalizer import normalize_transcript

try:
    from utils.commands import detect_command, execute_command
except ImportError:
    detect_command = None
    execute_command = None

# Model singleton and loaded model metadata tracker
_whisper_model = None
_loaded_model_name = None


def get_loaded_model_name() -> str | None:
    """Return the name of the currently active in-memory Whisper model."""
    return _loaded_model_name


def get_whisper_model():
    """
    Load Faster-Whisper model singleton with graceful memory fallback.

    Default configured model is 'large-v3' (or WHISPER_MODEL env var).
    If memory allocation (e.g. mkl_malloc / OOM) or download fails,
    explicitly falls back to 'base' (or 'tiny') and logs the actual state.
    """
    global _whisper_model, _loaded_model_name
    if _whisper_model is None:
        target_model = os.environ.get("WHISPER_MODEL", "large-v3").strip()
        print(f"[predict] Initializing Faster-Whisper model ('{target_model}') using cache: {_cache_dir}...")
        try:
            _whisper_model = WhisperModel(
                target_model,
                device="cpu",
                compute_type="int8",
                download_root=_cache_dir,
            )
            _loaded_model_name = target_model
            print(f"[predict] Faster-Whisper model ('{_loaded_model_name}') loaded successfully.")
        except Exception as e:
            print(f"[predict] Warning loading '{target_model}': {e}. Activating fallback to 'base' model...")
            try:
                _whisper_model = WhisperModel(
                    "base",
                    device="cpu",
                    compute_type="int8",
                    download_root=_cache_dir,
                )
                _loaded_model_name = "base"
                print(f"[predict] Faster-Whisper fallback model ('base') loaded successfully.")
            except Exception as e2:
                print(f"[predict] Warning loading 'base' model: {e2}. Activating emergency fallback to 'tiny' model...")
                _whisper_model = WhisperModel(
                    "tiny",
                    device="cpu",
                    compute_type="int8",
                    download_root=_cache_dir,
                )
                _loaded_model_name = "tiny"
                print(f"[predict] Faster-Whisper emergency fallback model ('tiny') loaded successfully.")
    return _whisper_model


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
            "model": "<loaded model name>",
            "duration": <seconds>,
            "processing_time": <seconds>,
            "error": "..." (only when status is "error")
        }
    """
    start_time = time.time()
    try:
        model = get_whisper_model()
        active_model_name = get_loaded_model_name()

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
            vad_filter=False,  # avoids dependency on onnxruntime
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
                "model": active_model_name,
                "duration": round(getattr(info, "duration", 0.0), 2) if 'info' in locals() and info else 0.0,
                "processing_time": processing_time,
            }

        # Normalize script (ensures consistent Devanagari for Hindi, leaves English/others clean)
        transcription = normalize_transcript(
            raw_transcription,
            detected_language=detected_lang,
            language_preference=language_preference,
        )

        # Optional command detection (system command policy enforced in commands module)
        command_result = None
        if callable(detect_command):
            cmd_info = detect_command(transcription)
            if cmd_info is not None and callable(execute_command):
                try:
                    command_result = execute_command(cmd_info)
                except Exception:
                    command_result = None

        return {
            "transcription": transcription,
            "command": command_result,
            "status": "success",
            "language": detected_lang,
            "model": active_model_name,
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
            "model": get_loaded_model_name(),
            "duration": 0.0,
            "processing_time": processing_time,
        }


def predict_audio(audio_path: str) -> dict:
    """
    Backward-compatible alias for transcribe_audio.
    Provides compatibility for legacy callers expecting 'success' and 'prediction' keys.
    """
    res = transcribe_audio(audio_path)
    return {
        "success": res.get("status") == "success",
        "transcription": res.get("transcription", ""),
        "language": res.get("language", "en"),
        "model": res.get("model", None),
        "status": res.get("status", "error"),
        "error": res.get("error", None),
    }
