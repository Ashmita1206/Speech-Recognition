"""
Prediction module — Faster-Whisper speech-to-text for Linux Voice Assistant.

Flow:
  1. Load Faster-Whisper model ONCE at startup (large-v3, CPU, int8).
  2. Transcribe incoming audio files.
  3. Detect commands from transcribed text.
  4. Return transcription + command info as a structured dict.
"""

import os

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

from faster_whisper import WhisperModel
from utils.commands import detect_command, execute_command

# ---------------------------------------------------------------------------
# Load the Faster-Whisper model ONCE at module-import time.
# large-v3 with int8 quantisation gives great accuracy with CPU efficiency.
# ---------------------------------------------------------------------------
# Model size options: tiny, base, small, medium, large-v3
# Using "large-v3" for best accuracy (~3 GB download on first run).
print("[predict] Loading Faster-Whisper model (large-v3, int8)…")
print("[predict] This may take a moment on first run (model download ~3 GB).")
whisper_model = WhisperModel("large-v3", device="cpu", compute_type="int8")
print("[predict] Faster-Whisper model loaded successfully.")


def transcribe_audio(audio_path: str) -> dict:
    """
    Transcribe audio and detect commands.

    Args:
        audio_path: Path to a WAV file (16 kHz mono recommended).

    Returns:
        dict matching the API response format:
        {
            "transcription": "<clean text>",
            "command": { ... } or null,
            "status": "success" | "error",
            "error": "..." (only when status is "error")
        }
    """
    try:
        # --- Transcribe with Faster-Whisper ---
        segments, info = whisper_model.transcribe(
            audio_path,
            beam_size=5,
            language=None,        # auto-detect language
            vad_filter=True,      # skip silence for speed
        )

        # Collect all segment texts
        full_text_parts = []
        for segment in segments:
            full_text_parts.append(segment.text.strip())

        transcription = " ".join(full_text_parts).strip()

        if not transcription:
            return {
                "transcription": "",
                "command": None,
                "status": "error",
                "error": "No audio input detected",
            }

        # --- Detect command from transcription ---
        cmd_info = detect_command(transcription)

        command_result = None
        if cmd_info is not None:
            command_result = execute_command(cmd_info)

        return {
            "transcription": transcription,
            "command": command_result,
            "status": "success",
        }

    except Exception as e:
        return {
            "transcription": "",
            "command": None,
            "status": "error",
            "error": f"Transcription failed: {str(e)}",
        }
