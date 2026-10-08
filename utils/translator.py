"""
Translation Module — Speech Recognition Studio
================================================
Handles modular text translation across supported languages with:
  1. Primary translation via Google Translate service (fast, lightweight, no heavy ML models).
  2. Fallback translation via MyMemory API.
  3. Optional API key support configured via .env (never hardcoded).
  4. Natural language voice command detection for voice-driven language selection.
  5. Clean error handling without exposing Python/API tracebacks.
"""

import os
import re
import urllib.parse
import requests

# ---------------------------------------------------------------------------
# Load environment variables from .env if present
# ---------------------------------------------------------------------------
def _load_env():
    """Load key-value pairs from .env in project root if available."""
    env_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if os.path.isfile(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("\"'")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env()

# ---------------------------------------------------------------------------
# Supported Languages Registry
# ---------------------------------------------------------------------------
# Curated primary languages requested for the language selector
PRIMARY_LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese": "zh-CN",
    "Arabic": "ar",
    "Punjabi": "pa",
    "Bengali": "bn",
    "Marathi": "mr",
    "Gujarati": "gu",
    "Tamil": "ta",
    "Telugu": "te",
    "Kannada": "kn",
    "Malayalam": "ml",
}

# Extended mapping for "Other language" input and voice commands
EXTENDED_LANGUAGES = {
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Turkish": "tr",
    "Dutch": "nl",
    "Polish": "pl",
    "Swedish": "sv",
    "Greek": "el",
    "Czech": "cs",
    "Danish": "da",
    "Finnish": "fi",
    "Hebrew": "he",
    "Indonesian": "id",
    "Malay": "ms",
    "Norwegian": "no",
    "Persian": "fa",
    "Farsi": "fa",
    "Romanian": "ro",
    "Thai": "th",
    "Ukrainian": "uk",
    "Urdu": "ur",
    "Vietnamese": "vi",
    "Hungarian": "hu",
    "Filipino": "tl",
    "Tagalog": "tl",
    "Nepali": "ne",
    "Sinhala": "si",
    "Swahili": "sw",
}

# Unified lookup dictionary (lowercase name -> (display_name, code))
_LOOKUP_MAP = {}
for name, code in PRIMARY_LANGUAGES.items():
    _LOOKUP_MAP[name.lower()] = (name, code)
    _LOOKUP_MAP[code.lower()] = (name, code)

for name, code in EXTENDED_LANGUAGES.items():
    _LOOKUP_MAP[name.lower()] = (name, code)
    _LOOKUP_MAP[code.lower()] = (name, code)

# Special aliases
_LOOKUP_MAP["mandarin"] = ("Chinese", "zh-CN")
_LOOKUP_MAP["chinese simplified"] = ("Chinese", "zh-CN")
_LOOKUP_MAP["chinese traditional"] = ("Chinese", "zh-TW")
_LOOKUP_MAP["zh"] = ("Chinese", "zh-CN")


def get_supported_languages() -> dict:
    """Return dictionary of primary supported languages."""
    return dict(PRIMARY_LANGUAGES)


def resolve_language(lang_input: str) -> tuple[str, str] | None:
    """
    Resolve a user-provided language name or code into (canonical_name, iso_code).
    Returns None if unsupported.
    """
    if not lang_input or not isinstance(lang_input, str):
        return None

    cleaned = lang_input.strip().lower()
    # Strip any trailing punctuation
    cleaned = cleaned.rstrip(".!?,;:")

    if cleaned in _LOOKUP_MAP:
        return _LOOKUP_MAP[cleaned]

    # Check standard 2-letter ISO code regex (e.g., 'es', 'fr', 'pt')
    if re.fullmatch(r"[a-z]{2}(-[a-z]{2,4})?", cleaned):
        # Capitalize nicely
        display_name = cleaned.upper()
        return (display_name, cleaned)

    return None


# ---------------------------------------------------------------------------
# Voice Command Detection
# ---------------------------------------------------------------------------
VOICE_COMMAND_PATTERNS = [
    # "Translate this into English", "Translate my last transcription into Hindi", "Convert this to Spanish"
    r'(?:translate|convert)(?:\s+(?:this|it|that|my\s+last\s+transcription|the\s+transcription|the\s+text))?\s+(?:in)?to\s+([a-zA-Z\-]+)',
    # "Give me the Hindi translation", "Give me the translation in Hindi"
    r'give\s+me\s+the\s+([a-zA-Z\-]+)\s+translation',
    r'give\s+me\s+the\s+translation\s+(?:in|to)\s+([a-zA-Z\-]+)',
    # "How do you say this in French"
    r'how\s+do\s+you\s+say\s+this\s+in\s+([a-zA-Z\-]+)',
    # "Translate this in Hindi"
    r'translate\s+(?:this|it|that)?\s+in\s+([a-zA-Z\-]+)',
]

def detect_translation_command(text: str) -> dict | None:
    """
    Check if a transcribed text represents a voice translation command.

    Examples:
      - "Translate this into English."
      - "Translate my last transcription into Hindi."
      - "Convert this to Spanish."
      - "Give me the Hindi translation."

    Returns:
      {
        "is_command": True,
        "target_language": "Hindi",
        "target_code": "hi",
        "raw_language": "Hindi"
      }
      or None if the text is regular speech.
    """
    if not text or not isinstance(text, str):
        return None

    cleaned = text.strip().rstrip(".!?,;:")

    for pattern in VOICE_COMMAND_PATTERNS:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            raw_lang = match.group(1).strip()
            resolved = resolve_language(raw_lang)
            if resolved:
                name, code = resolved
                return {
                    "is_command": True,
                    "target_language": name,
                    "target_code": code,
                    "raw_language": raw_lang,
                }
            else:
                # Command detected but language is unknown/unsupported
                return {
                    "is_command": True,
                    "target_language": raw_lang.capitalize(),
                    "target_code": None,
                    "raw_language": raw_lang,
                }

    return None


# ---------------------------------------------------------------------------
# Core Translation Execution
# ---------------------------------------------------------------------------
def _translate_google_web(text: str, target_code: str, source_code: str = "auto") -> str | None:
    """Primary translation using lightweight Google Translate web endpoint."""
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": source_code or "auto",
        "tl": target_code,
        "dt": "t",
        "q": text,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    response = requests.get(url, params=params, headers=headers, timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            # Concatenate all sentence segments
            translated_parts = [segment[0] for segment in data[0] if segment and segment[0]]
            result = "".join(translated_parts).strip()
            if result:
                return result
    return None


def _translate_mymemory(text: str, target_code: str, source_code: str = "auto") -> str | None:
    """Fallback translation using MyMemory Translation API."""
    src = "en" if (not source_code or source_code == "auto") else source_code
    langpair = f"{src}|{target_code}"
    url = "https://api.mymemory.translated.net/get"
    params = {
        "q": text,
        "langpair": langpair,
    }
    headers = {
        "User-Agent": "SpeechRecognitionStudio/1.0",
    }
    response = requests.get(url, params=params, headers=headers, timeout=10)
    if response.status_code == 200:
        data = response.json()
        translated = data.get("responseData", {}).get("translatedText")
        if translated and not translated.startswith("MYMEMORY WARNING"):
            # Unescape HTML entities if present
            import html
            return html.unescape(translated).strip()
    return None


def _translate_custom_api(text: str, target_code: str, api_key: str, source_code: str = "auto") -> str | None:
    """Optional translation via Google Cloud API key if configured in .env."""
    url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
    payload = {
        "q": text,
        "target": target_code,
        "format": "text",
    }
    if source_code and source_code != "auto":
        payload["source"] = source_code

    response = requests.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        data = response.json()
        translations = data.get("data", {}).get("translations", [])
        if translations:
            import html
            return html.unescape(translations[0].get("translatedText", "")).strip()
    return None


def translate_text(text: str, target_language: str, source_language: str = None) -> dict:
    """
    Translate text into the specified target language.

    Args:
        text: Source text to translate.
        target_language: Target language name (e.g. 'Hindi', 'Spanish') or code ('hi', 'es').
        source_language: Optional source language code (e.g. 'en', 'hi') or None for auto.

    Returns:
        dict:
          {
            "status": "success",
            "source_text": text,
            "translated_text": "<translated string>",
            "target_language": "Hindi",
            "target_code": "hi",
            "source_language": "en"
          }
          or on error:
          {
            "status": "error",
            "error": "..."
          }
    """
    if not text or not text.strip():
        return {
            "status": "error",
            "error": "No text provided to translate.",
        }

    source_text = text.strip()

    # 1. Resolve target language
    resolved_target = resolve_language(target_language)
    if not resolved_target:
        return {
            "status": "error",
            "error": "That language isn't currently supported.",
        }

    target_name, target_code = resolved_target

    # 2. Resolve source language if provided
    source_code = "auto"
    source_name = "Auto"
    if source_language:
        resolved_src = resolve_language(source_language)
        if resolved_src:
            source_name, source_code = resolved_src
        else:
            source_code = source_language.lower()

    # Don't translate if source and target are identical
    if source_code.lower() == target_code.lower() and source_code != "auto":
        return {
            "status": "success",
            "source_text": source_text,
            "translated_text": source_text,
            "target_language": target_name,
            "target_code": target_code,
            "source_language": source_name,
        }

    # 3. Check for external API key in environment
    api_key = os.environ.get("TRANSLATION_API_KEY") or os.environ.get("GOOGLE_TRANSLATE_API_KEY")
    translated_result = None

    if api_key:
        try:
            translated_result = _translate_custom_api(source_text, target_code, api_key, source_code)
        except Exception:
            translated_result = None

    # 4. Primary Google web endpoint
    if not translated_result:
        try:
            translated_result = _translate_google_web(source_text, target_code, source_code)
        except Exception:
            translated_result = None

    # 5. Fallback MyMemory endpoint
    if not translated_result:
        try:
            translated_result = _translate_mymemory(source_text, target_code, source_code)
        except Exception:
            translated_result = None

    # 6. Check results
    if translated_result:
        return {
            "status": "success",
            "source_text": source_text,
            "translated_text": translated_result,
            "target_language": target_name,
            "target_code": target_code,
            "source_language": source_name,
        }

    # Friendly UI error as per requirements
    return {
        "status": "error",
        "error": "Translation couldn't be completed.",
    }
