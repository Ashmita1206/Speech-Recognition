"""
Audio Processing Utilities
- Converts any audio format (mp3, webm, ogg, wav) to 16kHz mono WAV for Whisper
- Generates mel-spectrogram for visualization (optional)
- Auto-discovers ffmpeg from imageio-ffmpeg (no system install needed)
"""

import os

# ---------------------------------------------------------------------------
# Auto-configure ffmpeg from imageio-ffmpeg BEFORE importing pydub
# (pydub checks for ffmpeg at import time and warns if not found)
# ---------------------------------------------------------------------------
try:
    import imageio_ffmpeg
    _ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    _ffmpeg_dir = os.path.dirname(_ffmpeg_path)
    if _ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    print(f"[audio] Using ffmpeg from: {_ffmpeg_path}")
except ImportError:
    _ffmpeg_path = None
    print("[audio] WARNING: imageio-ffmpeg not installed. "
          "Falling back to system ffmpeg. Install with: pip install imageio-ffmpeg")

import librosa
import numpy as np
import librosa.display
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use
import matplotlib.pyplot as plt
from pydub import AudioSegment

# Point pydub at the bundled ffmpeg binary (if available)
if _ffmpeg_path:
    AudioSegment.converter = _ffmpeg_path


# ---------------------------------------------------------------------------
# Supported input formats
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {'.wav', '.mp3', '.webm', '.ogg', '.flac', '.m4a'}


def is_supported_format(filename: str) -> bool:
    """Check if the file extension is one we can handle."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in SUPPORTED_EXTENSIONS


def convert_to_wav(input_path: str, output_path: str) -> str:
    """
    Convert any supported audio file to a 16 kHz mono WAV file.
    Uses pydub (which wraps ffmpeg) so it works with mp3, webm, ogg, etc.

    Returns:
        output_path on success.
    Raises:
        RuntimeError on failure.
    """
    try:
        ext = os.path.splitext(input_path)[1].lower().lstrip('.')

        # For webm and other formats, let pydub auto-detect
        if ext in ('webm', 'ogg', 'flac', 'm4a'):
            audio = AudioSegment.from_file(input_path, format=ext)
        elif ext == 'mp3':
            audio = AudioSegment.from_mp3(input_path)
        else:
            audio = AudioSegment.from_file(input_path)

        # Whisper expects 16 kHz mono
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(output_path, format='wav')
        return output_path
    except Exception as e:
        raise RuntimeError(f"Audio conversion failed: {e}")


# ---------------------------------------------------------------------------
# Spectrogram generation (kept for visualization)
# ---------------------------------------------------------------------------
def load_audio(file_path):
    """Load audio using librosa (for spectrogram only)."""
    try:
        audio, sr = librosa.load(file_path, sr=None)
        return audio, sr
    except Exception as e:
        print(f"Error loading audio {file_path}: {e}")
        return None, None


def generate_spectrogram(audio, sr, save_path):
    """Generates and saves a mel-spectrogram image."""
    if audio is None:
        return False

    plt.figure(figsize=(10, 4))
    S = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=128, fmax=8000)
    S_dB = librosa.power_to_db(S, ref=np.max)
    librosa.display.specshow(S_dB, sr=sr, fmax=8000)
    plt.axis('off')
    plt.savefig(save_path, bbox_inches='tight', pad_inches=0)
    plt.close()
    return True