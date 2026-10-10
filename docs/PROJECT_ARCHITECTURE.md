# Speech Recognition Studio — Project Architecture & System Reference

## Section A: Project Overview

### What the Application Does
Speech Recognition Studio is an end-to-end, privacy-focused speech-to-text, script normalization, and multilingual translation web application. It allows users to record live speech directly within their web browser or upload pre-recorded audio files in diverse formats (WAV, MP3, WebM, OGG, FLAC, M4A). The server processes the audio through an offline **Faster-Whisper** engine, detects and normalizes language scripts (specifically ensuring natural Devanagari Hindi while preserving English code-switching), translates the transcript into any of 17+ target languages via a multi-engine fallback pipeline, and allows one-click copying, downloading, and audio playback.

The system also includes an integrated voice-command interpreter capable of detecting conversational actions (e.g., system queries, application launching, or voice-directed translation triggers) with strict safety confirmation boundaries for high-impact actions.

### Primary Features
1. **Real-Time Browser Recording**: High-fidelity audio capture via the Web MediaStream Recording API with animated real-time audio visualizer feedback.
2. **Universal Audio Upload**: Drag-and-drop or file picker support for `.wav`, `.mp3`, `.webm`, `.ogg`, `.flac`, and `.m4a` files with server-side 16 kHz mono normalization (25 MB max upload guard).
3. **Optimized Local Whisper Inference**: High-accuracy transcription powered by CTranslate2-quantized Whisper models (`large-v3` default with automatic graceful fallback to `base`/`tiny` under memory constraints), executing locally with INT8 CPU quantization.
4. **Intelligent Script Normalization**: Dedicated script normalization for South Asian and code-switched languages:
   - Detects script type (Devanagari, Urdu/Perso-Arabic, Roman/Latin).
   - Normalizes Roman Hinglish and Urdu phonetic text into standard Devanagari script.
   - Preserves genuine English technical vocabulary, acronyms, and numbers.
5. **Multi-Engine Translation Suite**: Live translation across 17+ primary languages (and custom extended languages) utilizing a cascading multi-tier architecture:
   - Tier 1: Lightweight Google Translate Chrome endpoint (fast, zero API key required, reliable).
   - Tier 2: MyMemory Translation API.
   - Tier 3: Direct Google Web translator.
   - Tier 4: Optional Google Cloud Translation v2 API if an explicit API key is configured.
6. **Preserved Dual Display**: Independent presentation of original transcript alongside translated text; changing the target language re-translates the original transcript without overwriting it.
7. **Client-Side History & Export**: Client-side recording history cached in browser `localStorage`, with one-click clipboard copying, `.txt` file export, and Web Speech synthesis playback.
8. **Voice Assistant / Command Interpretation**: Rule-based intent parser for hands-free voice commands, including language switching ("Translate this to Spanish") and Linux desktop operations guarded by an environment security gate (`ENABLE_SYSTEM_COMMANDS`).

### Technology Stack
- **Frontend**: Vanilla HTML5, CSS3 (responsive dark glassmorphism theme, CSS variables, backdrop filters), and Vanilla JavaScript (ES6+, Web Audio API, MediaRecorder API, Web Speech Synthesis).
- **Backend**: Python 3.12, Flask 3.1 WSGI web framework.
- **Audio Processing**: PyDub, imageio-ffmpeg (bundled static FFmpeg binary), Librosa, NumPy (pinned to 2.2.6), Matplotlib (headless Agg backend).
- **AI / Speech-to-Text**: `faster-whisper` (1.1.1), `ctranslate2` (4.4.0), Hugging Face Hub cache.
- **HTTP & Networking**: `requests` (2.34.2) for modular translation and transliteration services.
- **Production Server**: Gunicorn (single-worker, 4-thread architecture to prevent duplicate in-memory model weights).

---

## Section B: Complete Directory Tree

```
D:\SPEECH RECOGNITION/
├── .dockerignore                 # Excludes local caches, virtualenvs, recordings, and secrets
├── .env.example                  # Reference template for environment configuration
├── .gitignore                    # Git rules ignoring model caches, recordings, and venvs
├── Dockerfile                    # Production Debian-slim container with FFmpeg & Gunicorn
├── README.md                     # Repository overview and setup instructions
├── requirements.txt              # Pinned Python package dependencies (NumPy 2.2.6 compatible)
├── app.py                        # Main Flask server entry point & HTTP route controller
├── test_hindi.wav                # Verified audio test fixture (Hindi speech sample)
├── test_translation.py           # Automated test suite (transcription, translation, security)
├── test.py                       # Legacy Keras training script (retained for compatibility)
│
├── .github/                      # CI/CD Workflows
│   └── workflows/
│       └── ci.yml                # Automated lint, test, model verification, and Docker CI pipeline
│
├── docs/                         # Engineering & Deployment Documentation
│   ├── PROJECT_ARCHITECTURE.md   # Complete system architecture, workflows, & API reference
│   └── DEPLOYMENT_AND_CICD.md    # Hosting feasibility, cardless deployment, & rollback guide
│
├── static/                       # Frontend Assets
│   ├── script.js                 # Web Audio recording, AJAX fetch, & UI controller
│   ├── style.css                 # Dark glassmorphic design system & layout styling
│   ├── uploads/                  # Temporary staging directory for audio uploads
│   └── spectrograms/             # Transient directory for generated mel-spectrograms
│
├── templates/                    # Jinja2 HTML Templates
│   └── index.html                # Single-page web application interface
│
├── utils/                        # Backend Subsystems
│   ├── audio_processing.py       # Format conversion (pydub/ffmpeg) to 16 kHz mono WAV
│   ├── commands.py               # Voice command parsing, token confirmation, & security gate
│   ├── dataset.py                # Legacy dataset loader (retained for compatibility)
│   ├── predict.py                # Faster-Whisper model loading, fallback, & inference
│   ├── script_normalizer.py      # Devanagari Hindi normalization & Hinglish transliteration
│   └── translator.py             # Multi-engine translation suite & voice command language parser
│
└── model/                        # Legacy Model Definitions
    ├── model.py                  # Legacy Keras LSTM model architecture
    └── label_map.json            # Legacy label mapping
```

---

## Section C: Architecture Diagram

```mermaid
flowchart TD
    subgraph Browser ["Web Browser Client"]
        UI["User Interface (templates/index.html)"]
        AudioRecord["MediaRecorder API / Audio Upload"]
        WaveVisual["Canvas Waveform Visualizer"]
        ClientJS["Frontend Controller (static/script.js)"]
        LocalStorage[("Browser LocalStorage")]
        WebSpeech["Web Speech Synthesis API"]
    end

    subgraph Backend ["Flask WSGI Server (app.py)"]
        Router{"Flask URL Router"}
        UploadHandler["File Staging & Validation (/transcribe)"]
        TranslateHandler["Translation Controller (/translate)"]
        ExecuteHandler["Command Confirmation Guard (/execute)"]
        LangHandler["Language Registry (/languages)"]
    end

    subgraph AudioEngine ["Audio Processing Engine (utils/audio_processing.py)"]
        AudioValidator["Format & Size Validator (25MB Limit)"]
        FFmpegConverter["pydub + imageio-ffmpeg\n(16 kHz Mono WAV Conversion)"]
        MelSpecGen["Librosa Mel-Spectrogram Generator"]
    end

    subgraph WhisperInference ["Speech Recognition Engine (utils/predict.py)"]
        ModelSingleton["get_whisper_model() Singleton\n(Systran/faster-whisper-large-v3)"]
        CTranslate2["CTranslate2 INT8 CPU Engine"]
        ModelFallback["Fallback: faster-whisper-base"]
        ModelCache[("Environment-Configurable Model Cache\n($HF_HOME / .hf_cache)")]
    end

    subgraph ScriptNormalization ["Language Script Normalizer (utils/script_normalizer.py)"]
        ScriptDetector{"Script Detection\n(Devanagari / Urdu / Latin)"}
        DevaPreserve["Preserve Clean Devanagari"]
        UrduConverter["Phonetic Urdu to Devanagari Map"]
        HinglishTransliterate["Offline Hinglish Dict / Google Input Tools"]
        CodeSwitchGuard["Preserve English Tech Terms"]
    end

    subgraph AssistantEngine ["Voice Assistant & Security Engine (utils/commands.py)"]
        IntentParser["Command Regex Matcher"]
        SecurityGate{"ENABLE_SYSTEM_COMMANDS\nEnabled?"}
        TokenStore[("In-Memory Confirmation Tokens\n(5-Minute TTL Store)")]
        BuiltinTime["Safe In-Process Built-in (__builtin_time__)"]
        SubprocessExec["Subprocess Shell Execution (Linux)"]
    end

    subgraph TranslationService ["Multi-Engine Translator (utils/translator.py)"]
        LangResolver["ISO Language Resolver"]
        CommandDetector["Translation Voice Command Detector"]
        Tier1["Tier 1: Google Dict Service (dict-chrome-ex)"]
        Tier2["Tier 2: MyMemory Translation API"]
        Tier3["Tier 3: Google Web Translation Endpoint"]
        Tier4["Tier 4: Optional Google Cloud API Key (.env)"]
    end

    subgraph ExternalCloud ["External Network Services"]
        GoogleDictAPI[["Google Dict Service\n(clients5.google.com)"]]
        MyMemoryAPI[["MyMemory Translation API\n(api.mymemory.translated.net)"]]
        GoogleInputAPI[["Google Input Tools API\n(inputtools.google.com)"]]
    end

    %% Audio recording & submission flow
    AudioRecord -->|Audio Blob / Multipart Form| UploadHandler
    UI <--> ClientJS
    AudioRecord --> WaveVisual
    ClientJS <--> LocalStorage
    ClientJS --> WebSpeech

    %% Flask Routing
    UploadHandler --> AudioValidator
    AudioValidator --> FFmpegConverter
    FFmpegConverter --> MelSpecGen
    FFmpegConverter -->|16kHz Mono WAV| ModelSingleton

    %% Model Inference
    ModelSingleton <--> ModelCache
    ModelSingleton --> CTranslate2
    CTranslate2 -.->|OOM Fallback| ModelFallback
    CTranslate2 -->|Raw Text + Language| ScriptDetector

    %% Script Normalization
    ScriptDetector --> DevaPreserve
    ScriptDetector --> UrduConverter
    ScriptDetector --> HinglishTransliterate
    HinglishTransliterate <-->|Online Fallback| GoogleInputAPI
    ScriptDetector --> CodeSwitchGuard
    DevaPreserve & UrduConverter & HinglishTransliterate & CodeSwitchGuard -->|Normalized Transcript| IntentParser

    %% Command interpretation & Security
    IntentParser -->|Built-in Time| BuiltinTime
    IntentParser -->|OS Shell Action| SecurityGate
    SecurityGate -->|Disabled (Default)| UploadHandler
    SecurityGate -->|Enabled & Dangerous| TokenStore
    TokenStore --> ExecuteHandler --> SubprocessExec
    IntentParser -->|Voice Translation Command| TranslateHandler

    %% Translation flow
    ClientJS -->|POST /translate (text, target_lang)| TranslateHandler
    TranslateHandler --> LangResolver
    LangResolver --> Tier1
    Tier1 <-->|HTTP Request| GoogleDictAPI
    Tier1 -.->|On Failure| Tier2
    Tier2 <-->|HTTP Request| MyMemoryAPI
    Tier2 -.->|On Failure| Tier3
    Tier3 -.->|If Configured| Tier4

    %% Response cycle
    UploadHandler -->|JSON: text, lang, model, duration, command| ClientJS
    TranslateHandler -->|JSON: translated_text, target_lang| ClientJS
    LangHandler -->|JSON: languages dict| ClientJS
```

---

## Section D: Full Transcription Flow

```
[User Mic Click] 
  → [MediaRecorder WebM Blob] 
  → [AJAX POST /transcribe] 
  → [Flask Request Staging & Size Check] 
  → [16 kHz Mono WAV Normalization] 
  → [Faster-Whisper Inference (Singleton)] 
  → [Script Normalization (Devanagari)] 
  → [Security-Gated Command Intent Check] 
  → [JSON Response Packaging] 
  → [DOM Rendering & LocalStorage History]
```

1. **User Recording & Audio Capture**: Browser MediaRecorder captures Opus/WebM audio with real-time waveform feedback via Web Audio API.
2. **Packaging**: Stopping recording packages chunks into a binary `Blob` uploaded via `POST /transcribe` under the form key `"audio"`.
3. **Request Validation**: `app.py` checks for file presence, non-empty filename, file size against `MAX_CONTENT_LENGTH` (25 MB), and extension against `ALLOWED_EXTENSIONS`.
4. **Format Normalization**: `utils/audio_processing.py` converts the audio to 16 kHz mono WAV using FFmpeg.
5. **Whisper Inference**: `get_whisper_model()` runs inference on CPU INT8. If `large-v3` fails memory allocation, it explicitly falls back to `base` (or `tiny`) and logs the fallback state.
6. **Script Normalization**: `normalize_transcript()` converts Roman Hinglish and Urdu characters to Devanagari Hindi while preserving English code-switched terms.
7. **Assistant & Security Check**: `detect_command()` checks for voice commands. If OS commands are disabled (`ENABLE_SYSTEM_COMMANDS=false`), OS commands are blocked safely.
8. **Storage Cleanup & Return**: Temporary WAV and raw files are deleted in a `finally` block to prevent disk growth.

---

## Section E: Full Translation Flow

```
[Target Language Selected]
  → [AJAX POST /translate]
  → [Language Code Resolution]
  → [Direct Match / Normalization Check]
  → [Cascading Multi-Tier Translation Dispatch]
  → [Devanagari / Punctuation Post-Processing]
  → [Translated Box Rendering (Original Preserved)]
```

1. **Source Transcript**: Retrieved from active transcription pane; never modified during translation.
2. **Target Language**: Selected via dropdown, custom modal, or voice command (*"Translate this to Spanish"*).
3. **Cascading Dispatch**:
   - Tier 1: Google Dict Chrome service (`clients5.google.com/translate_a/t`).
   - Tier 2: MyMemory API (`api.mymemory.translated.net/get`).
   - Tier 3: Google Web translation endpoint.
   - Tier 4: Optional Google Cloud Translation v2 key if configured in `.env`.
4. **Dual Display**: Translated text renders into `#translatedText`. The original transcription card remains untouched.

---

## Section F: Model Architecture and Lifecycle

- **Model Identifier**: Default `large-v3` (`Systran/faster-whisper-large-v3`).
- **Memory Fallback**: Falls back to `base` (`Systran/faster-whisper-base`) if memory allocation fails.
- **Quantization**: `int8` CPU quantization via CTranslate2.
- **Cache Configuration**: Resolves via `HF_HOME` or `WHISPER_CACHE_DIR`; defaults to project-root `.hf_cache`. Never hardcoded to a specific drive.
- **In-Memory Tracking**: `get_loaded_model_name()` returns the exact model loaded.
- **Worker Policy**: Container / WSGI uses **1 Gunicorn worker with 4 threads** to prevent duplicating in-memory model weights.

---

## Section G: API Reference

| Endpoint | Method | Request Format | Response Format | Called Utility | Purpose & Security Policy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/` | `GET` | Empty | `text/html` | `index()` | Serves main UI layout from `templates/index.html`. |
| `/transcribe` | `POST` | `multipart/form-data`<br>`audio`: Binary file (<= 25 MB)<br>`language`: String | `application/json`<br>`{ status, transcription, language, model, duration, command }` | `transcribe_audio()` in `utils/predict.py` | Primary audio transcription endpoint. |
| `/predict` | `POST` | Identical to `/transcribe` | Identical to `/transcribe` | `predict_audio()` | Backward-compatible alias for legacy testing. |
| `/translate` | `POST` | `application/json`<br>`{ text, target_language, source_language }` | `application/json`<br>`{ status, source_text, translated_text, target_language, target_code, source_language }` | `translate_text()` in `utils/translator.py` | Multilingual translation with multi-tier fallback. |
| `/languages` | `GET` | Empty | `application/json`<br>`{ status, languages: [Name] }` | `get_supported_languages()` in `utils/translator.py` | Populates language selection dropdown. |
| `/execute` | `POST` | `application/json`<br>`{ confirmation_token, confirmed }` | `application/json`<br>`{ status, executed, command }` | `confirm_and_execute()` in `utils/commands.py` | **Security Protected**: Returns 403 Forbidden if `ENABLE_SYSTEM_COMMANDS=false`. Requires 5-min TTL token. |

---

## Section H: Data and Security

1. **Storage**: Temporary uploads staged in `static/uploads/` are deleted immediately in `try...finally`.
2. **History**: Maintained entirely in client browser `localStorage`; zero server-side database storage.
3. **System Command Gate**: `ENABLE_SYSTEM_COMMANDS` environment variable defaults to `false`. Public deployments reject remote shell command execution.
4. **Token Security**: Confirmation tokens expire after 300 seconds (5 minutes) and are single-use (`.pop()`).
5. **Secrets Hygiene**: `.env` and `.hf_cache` are strictly excluded via `.gitignore` and `.dockerignore`.

---

## Section I: Debugging Guide

- **U+2013 Syntax Error**: Descriptive text placed directly in executable code. Wrapped in docstrings.
- **mkl_malloc Allocation Error**: Host lacks sufficient RAM for `large-v3`. `get_whisper_model()` automatically catches this and falls back to `base`.
- **cp310 Wheel Metadata Warnings**: `pip check` in local Windows environment reports platform warnings for packages installed with Python 3.10 wheels. Resolved in clean environments via pinned `numpy==2.2.6`.
