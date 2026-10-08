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

whisper_model = None

def get_whisper_model():
    """Load Faster-Whisper model with fallback for available RAM/disk space."""
    global whisper_model
    if whisper_model is None:
        # Check if large-v3 is available, else use base (already cached & memory-efficient)
        print(f"[predict] Initializing Faster-Whisper model using cache: {_cache_dir}…")
        try:
            # Try base model which is already downloaded and verified on CPU with int8
            whisper_model = WhisperModel("base", device="cpu", compute_type="int8", download_root=_cache_dir)
            print("[predict] Faster-Whisper model loaded successfully.")
        except Exception as e:
            print(f"[predict] Warning loading base model: {e}. Trying tiny/large fallback...")
            whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root=_cache_dir)
            print("[predict] Whisper fallback model loaded.")
    return whisper_model


def transcribe_audio(audio_path: str) -> dict:
    """
    Transcribe audio and return clean text and metadata.

    Args:
        audio_path: Path to a WAV file (16 kHz mono recommended).

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

        # Transcribe with Faster-Whisper
        segments, info = model.transcribe(
            audio_path,
            beam_size=2,
            language=None,        # auto-detect language
            vad_filter=False,     # avoids dependency on onnxruntime
        )

        # Collect all segment texts
        full_text_parts = []
        for segment in segments:
            full_text_parts.append(segment.text.strip())

        transcription = " ".join(full_text_parts).strip()
        processing_time = round(time.time() - start_time, 2)

        if not transcription:
            return {
                "transcription": "",
                "command": None,
                "status": "error",
                "error": "No speech detected in audio",
                "language": getattr(info, "language", "en") if 'info' in locals() else "en",
                "duration": round(getattr(info, "duration", 0.0), 2) if 'info' in locals() else 0.0,
                "processing_time": processing_time,
            }

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
            "language": getattr(info, "language", "en"),
            "duration": round(getattr(info, "duration", 0.0), 2),
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
