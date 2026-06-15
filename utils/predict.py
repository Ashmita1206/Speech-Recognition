"""
Prediction module – Whisper-powered speech-to-text + keyword classification.

Flow:
  1. Transcribe audio with OpenAI Whisper (local model, no API key needed).
  2. Classify the transcribed text as YES / NO / UNKNOWN.
  3. Return transcription, classification, and a confidence score.
"""

import os
import re
import math
import whisper

# ---------------------------------------------------------------------------
# Ensure ffmpeg is on PATH before Whisper tries to use it
# (Whisper calls ffmpeg via subprocess internally)
# ---------------------------------------------------------------------------
try:
    import imageio_ffmpeg
    _ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
    if _ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass  # Fall back to system ffmpeg

# ---------------------------------------------------------------------------
# Load the Whisper model once at import time (cached across requests)
# Available sizes: tiny, base, small, medium, large
# "base" is a good trade-off between speed and accuracy.
# ---------------------------------------------------------------------------
print("Loading Whisper model (base)... This may take a moment on first run.")
whisper_model = whisper.load_model("base")
print("Whisper model loaded successfully.")


# ---------------------------------------------------------------------------
# YES / NO keyword lists (handles common variations & mishearings)
# ---------------------------------------------------------------------------
YES_KEYWORDS = [
    "yes", "yeah", "yep", "yup", "ya", "yah", "sure", "absolutely",
    "correct", "affirmative", "indeed", "right", "okay", "ok",
    "of course", "definitely", "certainly",
]

NO_KEYWORDS = [
    "no", "nope", "nah", "nay", "negative", "never", "not",
    "don't", "do not", "doesn't", "does not", "wasn't", "won't",
]


def _classify_text(text: str) -> str:
    """
    Classify transcribed text as YES, NO, or UNKNOWN.
    Uses simple keyword matching on the cleaned text.
    """
    cleaned = text.strip().lower()

    # Remove common punctuation for better matching
    cleaned = re.sub(r'[^\w\s]', '', cleaned)

    # Check for YES keywords
    for kw in YES_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', cleaned):
            return "YES"

    # Check for NO keywords
    for kw in NO_KEYWORDS:
        if re.search(r'\b' + re.escape(kw) + r'\b', cleaned):
            return "NO"

    return "UNKNOWN"


def _compute_confidence(result: dict) -> float:
    """
    Compute a 0-1 confidence score from Whisper's segment-level log probs.
    Whisper returns avg_logprob per segment; we convert to a probability.
    """
    segments = result.get("segments", [])
    if not segments:
        return 0.0

    # Average the avg_logprob across all segments
    avg_log_probs = [seg.get("avg_logprob", -1.0) for seg in segments]
    mean_log_prob = sum(avg_log_probs) / len(avg_log_probs)

    # Convert log-probability to a 0-1 scale (exp of log prob)
    # Clamp to [0, 1]
    confidence = math.exp(mean_log_prob)
    return round(min(max(confidence, 0.0), 1.0), 4)


def predict_audio(audio_path: str) -> dict:
    """
    Transcribe the audio file and classify the speech.

    Args:
        audio_path: Path to a WAV file (16 kHz mono recommended).

    Returns:
        dict with keys:
            transcription (str) – full transcribed text
            prediction    (str) – YES / NO / UNKNOWN
            confidence    (str) – e.g. "87.32%"
    """
    try:
        # Transcribe with Whisper
        result = whisper_model.transcribe(audio_path, fp16=False)
        transcription = result.get("text", "").strip()

        if not transcription:
            return {
                "success": False,
                "error": "Whisper could not detect any speech in the audio."
            }

        # Classify
        prediction = _classify_text(transcription)

        # Confidence
        confidence = _compute_confidence(result)

        return {
            "success": True,
            "transcription": transcription,
            "prediction": prediction,
            "confidence": f"{confidence * 100:.2f}%",
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Prediction failed: {e}",
        }
