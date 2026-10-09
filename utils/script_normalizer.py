"""
Script Normalizer Module — Speech Recognition Studio
=====================================================
Ensures consistent Devanagari script for Hindi speech recognition:
  1. Detects script type (Devanagari, Urdu/Perso-Arabic, Roman/Latin).
  2. Normalizes Roman Hinglish into proper Devanagari script.
  3. Converts Urdu/Perso-Arabic characters into Devanagari script.
  4. Preserves already-correct Devanagari text without distortion.
  5. Preserves genuine English phrases, acronyms, and numbers in code-switched speech.
  6. Leaves English and other non-Hindi languages intact.
"""

import re
import html
import requests

# ---------------------------------------------------------------------------
# Unicode Ranges
# ---------------------------------------------------------------------------
RE_DEVANAGARI = re.compile(r'[\u0900-\u097F]')
RE_URDU_ARABIC = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
RE_LATIN = re.compile(r'[a-zA-Z]')

# ---------------------------------------------------------------------------
# Common Hinglish Vocabulary (Offline Fallback Dictionary)
# ---------------------------------------------------------------------------
HINGLISH_TO_DEVANAGARI = {
    # Pronouns & Questions
    "mujhe": "मुझे", "mujhi": "मुझे", "mujhko": "मुझको", "mera": "मेरा", "meri": "मेरी", "mere": "मेरे",
    "main": "मैं", "hum": "हम", "humko": "हमको", "hamara": "हमारा", "hamari": "हमारी", "hamare": "हमारे",
    "aap": "आप", "aapko": "आपको", "aapka": "आपका", "aapki": "आपकी", "aapke": "आपके",
    "tum": "तुम", "tumko": "तुमको", "tumhara": "तुम्हारा", "tumhari": "तुम्हारी", "tumhare": "तुम्हारे",
    "yeh": "यह", "ye": "यह", "voh": "वह", "woh": "वह", "wo": "वह", "kya": "क्या",
    "kyun": "क्यों", "kyu": "क्यों", "kahan": "कहाँ", "kaha": "कहाँ", "kidhar": "किधर",
    "kaise": "कैसे", "kaisa": "कैसा", "kaisi": "कैसी", "kab": "कब", "kaun": "कौन",
    "kitna": "कितना", "kitni": "कितनी", "kitne": "कितने", "kiska": "किसका", "kisko": "किसको",
    # Verbs & Auxiliaries
    "hai": "है", "hain": "हैं", "ho": "हो", "hoon": "हूँ", "hun": "हूँ",
    "tha": "था", "thi": "थी", "the": "थे", "thien": "थीं",
    "peeni": "पीनी", "pini": "पीनी", "peena": "पीना", "peeta": "पीता", "peeti": "पीती",
    "karna": "करना", "karni": "करनी", "karta": "करता", "karti": "करती", "karte": "करते",
    "hona": "होना", "honi": "होनी", "hota": "होता", "hoti": "होती", "hote": "होते",
    "chahiye": "चाहिए", "chahta": "चाहता", "chahti": "चाहती", "chahte": "चाहते",
    "aana": "आना", "aata": "आता", "aati": "आती", "aate": "आते", "aaye": "आए",
    "jana": "जाना", "jaana": "जाना", "jata": "जाता", "jati": "जाती", "jate": "जाते", "gaya": "गया", "gayi": "गयी", "gaye": "गए",
    "dena": "देना", "deta": "देता", "deti": "देती", "dete": "देते", "do": "दो", "dijiye": "दीजिए",
    "lena": "लेना", "leta": "लेता", "leti": "लेती", "lete": "लेते", "lo": "लो", "lijiye": "लीजिए",
    "bolna": "बोलना", "bolta": "बोलता", "bolti": "बोलती", "bolo": "बोलो", "kaho": "कहो",
    "dekhna": "देखना", "dekha": "देखा", "dekho": "देखो", "suno": "सुनो", "samajh": "समझ",
    # Particles, Prepositions, Conjunctions
    "ek": "एक", "do": "दो", "teen": "तीन", "chaar": "चार", "paanch": "पाँच",
    "ko": "को", "se": "से", "ka": "का", "ki": "की", "ke": "के", "mein": "में", "me": "में", "par": "पर", "pe": "पे",
    "aur": "और", "ya": "या", "lekin": "लेकिन", "parantu": "परन्तु", "bhi": "भी", "hi": "ही", "to": "तो",
    "nahin": "नहीं", "nahi": "नहीं", "na": "ना", "haan": "हाँ", "han": "हाँ",
    # Common Nouns & Adjectives
    "chai": "चाय", "chaay": "चाय", "cup": "कप", "kaap": "कप", "pani": "पानी", "paani": "पानी",
    "khana": "खाना", "roti": "रोटी", "doodh": "दूध",
    "namaste": "नमस्ते", "namaskar": "नमस्कार", "dhanyawad": "धन्यवाद", "shukriya": "शुक्रिया",
    "achha": "अच्छा", "accha": "अच्छा", "acchi": "अच्छी", "acche": "अच्छे",
    "bura": "बुरा", "buri": "बुरी", "bure": "bure",
    "bahut": "बहुत", "bohot": "बहुत", "thoda": "थोड़ा", "thodi": "थोड़ी", "jyada": "ज़्यादा", "zyada": "ज़्यादा",
    "aaj": "आज", "kal": "कल", "parson": "परसों", "subah": "सुबह", "shaam": "शाम", "raat": "रात", "din": "दिन",
    "samay": "समय", "waqt": "वक़्त", "baat": "बात", "kaam": "काम", "ghar": "घर", "dost": "दोस्त",
}

# ---------------------------------------------------------------------------
# Urdu to Devanagari Word Dictionary & Character Mapping
# ---------------------------------------------------------------------------
URDU_WORD_MAP = {
    "مجھے": "मुझे", "ایک": "एक", "کپ": "कप", "چائے": "चाय", "چای": "चाय",
    "پینی": "पीनी", "پینا": "पीना", "ہے": "है", "ہیں": "हैं", "تھا": "था",
    "تھی": "थी", "تھے": "थे", "اور": "और", "کا": "का", "کی": "की",
    "کے": "के", "کو": "को", "سے": "से", "میں": "में", "پر": "पर",
    "یہ": "यह", "وہ": "वह", "کیا": "क्या", "کیسے": "कैसे", "کہاں": "कहाँ",
    "کیوں": "क्यों", "کب": "कब", "نہیں": "नहीं", "ہاں": "हाँ", "آپ": "आप",
    "تم": "तुम", "ہم": "हम", "میرا": "मेरा", "میری": "मेरी", "میرे": "मेरे",
    "بہت": "बहुत", "اچھا": "अच्छा", "شکریہ": "शुक्रिया", "سلام": "नमस्ते",
    "پانی": "पानी", "کھانا": "खाना", "دوست": "दोस्त", "گھر": "घर", "کام": "काम",
    "صبح": "सुबह", "شام": "शाम", "رات": "रात", "دن": "दिन", "وقت": "वक़्त",
}

URDU_CHAR_MAP = {
    'ا': 'आ', 'ب': 'ब', 'پ': 'प', 'ت': 'त', 'ٹ': 'ट', 'ث': 'स',
    'ج': 'ज', 'چ': 'च', 'ح': 'ह', 'خ': 'ख़', 'د': 'द', 'ڈ': 'ड',
    'ذ': 'ज़', 'ر': 'र', 'ڑ': 'ड़', 'ز': 'ज़', 'ژ': 'ज़', 'س': 'स',
    'ش': 'श', 'ص': 'स', 'ض': 'ज़', 'ط': 'त', 'ظ': 'ज़', 'ع': 'अ',
    'غ': 'ग़', 'ف': 'फ़', 'ق': 'क़', 'ک': 'क', 'گ': 'ग', 'ل': 'ल',
    'م': 'म', 'ن': 'न', 'ں': 'ँ', 'و': 'व', 'ہ': 'ह', 'ۂ': 'ह',
    'ۃ': 'त', 'ھ': 'ह', 'ء': 'अ', 'ی': 'ी', 'ے': 'े', 'ئ': 'य',
}


def is_predominantly_devanagari(text: str) -> bool:
    """Check if text is predominantly written in Devanagari script."""
    if not text:
        return False
    deva_count = len(RE_DEVANAGARI.findall(text))
    latin_count = len(RE_LATIN.findall(text))
    urdu_count = len(RE_URDU_ARABIC.findall(text))
    # True if Devanagari is present, no Urdu characters, and more Devanagari than Latin
    return deva_count > 0 and urdu_count == 0 and deva_count >= latin_count


def has_urdu_characters(text: str) -> bool:
    """Check if text contains any Arabic/Urdu script characters."""
    return bool(RE_URDU_ARABIC.search(text))


def has_latin_characters(text: str) -> bool:
    """Check if text contains Latin / Roman characters."""
    return bool(RE_LATIN.search(text))


# ---------------------------------------------------------------------------
# Transliteration & Normalization Functions
# ---------------------------------------------------------------------------
def _transliterate_google_inputtools(text: str) -> str | None:
    """Convert Roman Hinglish to Devanagari via Google Input Tools API."""
    try:
        url = "https://inputtools.google.com/request"
        params = {"text": text, "itc": "hi-t-i0-und", "num": "1"}
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, params=params, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 1 and len(data[1]) > 0:
                first_item = data[1][0]
                if len(first_item) > 1 and first_item[1]:
                    res = first_item[1][0].strip()
                    if res:
                        return res
    except Exception:
        pass
    return None


def _transliterate_offline_hinglish(text: str) -> str:
    """
    Offline fallback to convert Roman Hinglish words into Devanagari.
    Preserves numbers, genuine English phrases, and uppercase acronyms.
    """
    words = text.split()
    converted_words = []
    for word in words:
        # Separate trailing punctuation
        m = re.match(r'^([a-zA-Z0-9_\-]+)([\.,!?;:।]*)$', word)
        if m:
            core, punct = m.groups()
            core_lower = core.lower()

            # Keep pure numbers or short acronyms (e.g. AI, CPU, 3, 100)
            if core.isdigit() or (core.isupper() and len(core) <= 4 and core_lower not in HINGLISH_TO_DEVANAGARI):
                converted_words.append(core + punct)
            elif core_lower in HINGLISH_TO_DEVANAGARI:
                converted_words.append(HINGLISH_TO_DEVANAGARI[core_lower] + punct)
            else:
                converted_words.append(word)
        else:
            converted_words.append(word)

    return " ".join(converted_words)


def _convert_urdu_segment(text: str) -> str:
    """Convert Urdu words/characters to Devanagari."""
    # First try word-level replacement
    words = text.split()
    converted_words = []
    has_unmapped_urdu = False

    for word in words:
        clean_word = word.strip(".,!?;:؟،।")
        if clean_word in URDU_WORD_MAP:
            converted_words.append(word.replace(clean_word, URDU_WORD_MAP[clean_word]))
        elif RE_URDU_ARABIC.search(word):
            has_unmapped_urdu = True
            # Character-level phonetic conversion
            converted_chars = "".join(URDU_CHAR_MAP.get(c, c) for c in word)
            converted_words.append(converted_chars)
        else:
            converted_words.append(word)

    # If any Urdu characters remained, try online translation for those segments
    result = " ".join(converted_words)
    if has_unmapped_urdu:
        try:
            r = requests.get(
                "https://clients5.google.com/translate_a/t",
                params={"client": "dict-chrome-ex", "sl": "ur", "tl": "hi", "q": text},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=4,
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    return str(data[0][0]).strip()
                elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], str):
                    return str(data[0]).strip()
        except Exception:
            pass

    return result


def normalize_hindi_script(text: str) -> str:
    """
    Ensure Hindi text is presented in proper, clean Devanagari script.
    - If already proper Devanagari: preserves text, standardizes sentence danda.
    - If Urdu script present: converts Urdu words/characters to Devanagari.
    - If Roman Hinglish: transliterates to Devanagari, preserving genuine code-switched terms.
    """
    if not text or not text.strip():
        return ""

    raw = text.strip()

    # 1. Handle Urdu / Arabic characters if present
    if has_urdu_characters(raw):
        raw = _convert_urdu_segment(raw)

    # 2. Check if already predominantly Devanagari
    if is_predominantly_devanagari(raw) and not has_latin_characters(raw):
        # Already clean Devanagari; standardize punctuation if ended with dot
        if raw.endswith('.'):
            raw = raw[:-1] + '।'
        return raw

    # 3. If contains Roman / Latin words and represents Hindi speech
    # Attempt online transliteration via Google Input Tools
    normalized = _transliterate_google_inputtools(raw)

    # If online transliteration succeeded and yielded Devanagari
    if normalized and RE_DEVANAGARI.search(normalized):
        res = normalized.strip()
        if res.endswith('.'):
            res = res[:-1] + '।'
        return res

    # 4. Fallback: offline Hinglish transliteration dictionary
    offline_res = _transliterate_offline_hinglish(raw)
    if offline_res.endswith('.'):
        offline_res = offline_res[:-1] + '।'

    return offline_res


def normalize_transcript(
    text: str,
    detected_language: str = "en",
    language_preference: str = None
) -> str:
    """
    Master transcript normalizer:
    - If Hindi (detected as 'hi' / 'ur', or explicit Hindi preference): normalizes to Devanagari.
    - If English or other language: returns clean original transcript.
    """
    if not text or not text.strip():
        return ""

    clean_text = text.strip()
    pref = (language_preference or "").lower().strip()
    detected = (detected_language or "en").lower().strip()

    is_hindi_target = (
        pref in ("hi", "hindi")
        or (not pref and detected in ("hi", "ur"))
        or (detected in ("hi", "ur") and pref not in ("en", "english"))
    )

    if is_hindi_target:
        return normalize_hindi_script(clean_text)

    # For English and other languages, return clean text as-is
    return clean_text
