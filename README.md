# 🎙️ Mantra AI v3.1 — Intelligent Voice & Desktop Automation Agent

<p align="center">
  <img src="https://img.shields.io/badge/Version-3.1_Multi--Provider-blue.svg?style=for-the-badge" alt="Version 3.1" />
  <img src="https://img.shields.io/badge/Python-3.10%20–%203.14-brightgreen.svg?style=for-the-badge" alt="Python Version" />
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg?style=for-the-badge&logo=windows" alt="Platform" />
  <img src="https://img.shields.io/badge/AI%20Brain-Gemini%20%2B%20OpenAI%20%2B%20Ollama-orange.svg?style=for-the-badge" alt="Triple Brain" />
  <img src="https://img.shields.io/badge/Voice%20Control-Wake%20Word%20Enabled-red.svg?style=for-the-badge" alt="Voice Control" />
</p>

> **Mantra AI v3.1** is an enterprise-grade, voice-controlled AI desktop assistant and automation system built specifically for Windows. Powered by a **Multi-Provider AI Brain** (Google Gemini + OpenAI GPT + Local Ollama Offline Fallback), persistent cross-session memory, biometric speaker verification, RAG knowledge base, local media control, and full-spectrum desktop automation.
>
> 🗣️ **Default Wake Word:** `"Hello Mantra"`  
> 🌐 **Persona:** Natural English Conversational Agent (English-only input and output)

---

## 📑 Table of Contents

- [✨ What's New in v3.1](#-whats-new-in-v31)
- [⚡ Feature Matrix](#-feature-matrix)
- [🏗️ System Architecture](#️-system-architecture)
- [📁 Project Structure](#-project-structure)
- [🚀 Quick Start & Installation](#-quick-start--installation)
- [🔑 API Key Setup (.env)](#-api-key-setup-env)
- [⚙️ Configuration Guide (`data/config.json`)](#️-configuration-guide-dataconfigjson)
- [🤖 AI Provider Switching](#-ai-provider-switching)
- [🗣️ Voice Command Reference](#️-voice-command-reference)
- [🧠 Multi-Provider AI Brain](#-multi-provider-ai-brain)
- [🔒 Speaker Verification (Voice Biometrics)](#-speaker-verification-voice-biometrics)
- [🎵 Local Music Player](#-local-music-player)
- [📚 RAG Knowledge Base](#-rag-knowledge-base)
- [🔄 Self-Update System](#-self-update-system)
- [🛠️ Diagnostics & Troubleshooting](#️-diagnostics--troubleshooting)
- [📦 Dependencies & Libraries](#-dependencies--libraries)

---

## ✨ What's New in v3.1

### Multi-Provider AI Brain
- **OpenAI GPT support** alongside existing Google Gemini — switch between providers with one config change.
- **Auto mode** (default): tries Gemini → OpenAI → Ollama automatically, so Mantra always has an AI brain available.
- No new SDK dependencies — OpenAI API uses the same lightweight `requests` library as Gemini.

### Lazy RAG Loading
- **Embedding model (`all-MiniLM-L6-v2`) is now lazy-loaded** — it only loads on the first RAG query, not at startup.
- Startup is significantly faster. `VectorStore` (ChromaDB) still initialises immediately so `has_documents()` works instantly.
- Fixed **duplicate RAG initialisation** — previously the embedding model loaded twice (once in Agent, once in Brain). Now only a single `Retriever` instance exists.

### Voice Update Command
- New voice commands: **"Update"**, **"Update yourself"**, **"Mantra, update"**, **"Mantra, update yourself"**.
- Full workflow: checks GitHub → downloads if available → applies update → confirms by voice.
- If already up to date: *"I am already up to date."*

### Security Improvements
- **API keys moved to `.env` file** — secrets are git-ignored and never committed to your repository.
- `.env.example` template included for easy setup.
- `data/config.json` added to `.gitignore` to prevent accidental key exposure.

### Python 3.13 & 3.14 Compatibility
- Full support for Python 3.13 and 3.14 via `audioop-lts` and `PyAudioWPatch`.
- Updated `requirements.txt` with flexible `>=` version pinning.

### Codebase Cleanup
- Removed dead files (`ztest.py`, `mantra_run.out`, stale `__pycache__/` directories).
- Fixed comment numbering in tool priority chain.
- Organized `requirements.txt` with proper section headers.

---

## ⚡ Feature Matrix

| Category | Capability | Description | Example Voice Command |
|---|---|---|---|
| **Voice & Wake Word** | Continuous Background Listener | Low-latency wake word detection with active session loop | *"Hello Mantra"* |
| **Multi-Provider AI Brain** | Gemini + OpenAI + Ollama | Cloud-scale intelligence with automatic provider fallback | *"Explain quantum computing in simple words"* |
| **Long-Term Memory** | Fact & Preference Persistence | Stores key-value facts across sessions | *"Remember my car is a Honda City"*, *"What is my car?"* |
| **RAG Knowledge Base** | Document-Powered Answers | Answers questions from your local document collection | *"What is CropX?"* |
| **Speaker Biometrics** | Voiceprint Verification | Enrolls user audio fingerprint to prevent unauthorized access | `python voice/speaker_verify.py --enroll <wav>` |
| **Local Music Player** | Library Browser & Playback | Plays, shuffles, stops, and filters local music collection | *"Play Believer"*, *"Next song"*, *"Songs by Arijit Singh"* |
| **App Automation** | Natural Launch & Kill | Opens, closes, and detects running desktop software | *"Open VS Code"*, *"Close Spotify"*, *"What apps are running?"* |
| **Window Management** | Window State Control | Minimizes, maximizes, and switches active windows | *"Minimize Word"*, *"Maximize Chrome"*, *"Switch to VS Code"* |
| **File Operations** | Intelligent File Manager | Search, create, rename, copy, move, and directory navigation | *"Find file budget"*, *"Create folder Projects"*, *"Open Downloads"* |
| **Safe Recycle Bin** | Reversible Deletion | Deletes files to Windows Recycle Bin via `send2trash` | *"Delete file draft.txt"* |
| **System Hardware** | Volume, Brightness & Power | Hardware slider control and power commands with voice confirm | *"Volume 70%"*, *"Dim the screen"*, *"Lock computer"*, *"Restart"* |
| **Screen Capture** | Screenshots & MP4 Recording | Instant screen grabs and video recordings | *"Take a screenshot"*, *"Start recording"*, *"Stop recording"* |
| **Clipboard** | System Clipboard Manager | Read, write, cut, copy, paste, and clear clipboard | *"Copy that"*, *"Paste here"*, *"What's in my clipboard?"* |
| **Browser Navigation** | Tab & Bookmark Control | Searches Google/YouTube, manages tabs, opens quick bookmarks | *"Search Python tutorial on YouTube"*, *"Open bookmark email"* |
| **Web Services** | Live Weather, News & Wikipedia | Real-time weather, headline news, and Wikipedia summaries | *"Weather in Mumbai"*, *"Latest tech news"*, *"Who was APJ Abdul Kalam?"* |
| **Notes Management** | Interactive Notepad | Create, read, and delete persistent notes | *"Add note buy groceries"*, *"Read my notes"*, *"Delete note 1"* |
| **Self-Updater** | Voice Update & Version Check | GitHub release check, automatic backup, download, and safe patching via voice | *"Update yourself"*, *"Check for updates"*, *"What version are you?"* |

---

## 🏗️ System Architecture

```
                                  ┌────────────────────────────────┐
                                  │   Microphone Audio Input       │
                                  └──────────────┬─────────────────┘
                                                 │
                                                 ▼
                                  ┌────────────────────────────────┐
                                  │     voice/wake_word.py         │
                                  │   Listens for "Hello Mantra"   │
                                  └──────────────┬─────────────────┘
                                                 │  (Wake word detected)
                                                 ▼
                                  ┌────────────────────────────────┐
                                  │       main.py (Session)        │
                                  └──────────────┬─────────────────┘
                                                 │
                        ┌────────────────────────┴────────────────────────┐
                        ▼                                                ▼
         ┌───────────────────────────┐              ┌──────────────────────────────┐
         │   voice/speech_to_text.py │              │   voice/speaker_verify.py    │
         │   16kHz Mono + Normalize  │              │   Biometric Authentication   │
         └──────────────┬────────────┘              └──────────────────────────────┘
                        │ Spoken Text
                        ▼
         ┌────────────────────────────────────────────────────────────────────┐
         │                          agent/agent.py                           │
         │   Priority 1: Exit / Bye                                          │
         │   Priority 2: Built-in fast answers (Time, Date, Greetings)       │
         │   Priority 3: RAG document search                                 │
         │   Priority 4: Tool Execution (agent/tools.py)                     │
         │   Priority 5: AI Brain Fallback (brain/brain.py)                  │
         └──────────────┬──────────────────────────────────┬─────────────────┘
                        │                                  │
        ┌───────────────┴──────────────┐    ┌──────────────┴──────────────────┐
        ▼                              ▼    ▼                                 ▼
┌──────────────────────────────┐ ┌──────────────────────────────────┐ ┌──────────────────────┐
│       agent/tools.py         │ │         brain/brain.py           │ │ voice/text_to_speech  │
│ ├── apps/open_app.py         │ │ ┌─ brain/llm_api.py (Gemini)    │ │ edge-tts Neural TTS   │
│ ├── apps/music_player.py     │ │ ├─ brain/openai_llm.py (OpenAI) │ └──────────────────────┘
│ ├── system/system_control.py │ │ └─ brain/local_llm.py (Ollama)  │
│ ├── memory/memory.py         │ └──────────────────────────────────┘
│ ├── automation.py            │
│ ├── file_manager.py          │
│ ├── browser.py               │
│ ├── screen.py                │
│ ├── clipboard.py             │
│ ├── notes.py                 │
│ ├── internet.py              │
│ └── updater/updater.py       │
└──────────────────────────────┘
```

---

## 📁 Project Structure

```
MantraAI/
├── main.py                     # Entry point — wake word listener & session lifecycle loop
├── config.py                   # Centralized configuration parser (.env + config.json)
├── utils.py                    # Logging engine, NLP text normalizer, date/time utilities
├── diagnose.py                 # System diagnostic & dependency verification tool
├── requirements.txt            # Python package specifications
├── .env                        # API keys (git-ignored, never committed)
├── .env.example                # Template showing which env vars to set
│
├── agent/
│   ├── __init__.py
│   ├── agent.py                # Core Agent: session manager, built-in responses & dispatch
│   └── tools.py                # ToolRegistry: priority-based execution router for all tools
│
├── brain/
│   ├── __init__.py
│   ├── brain.py                # LLM Router: Gemini → OpenAI → Ollama → fallback
│   ├── llm_api.py              # Google Gemini Flash client with conversation memory
│   ├── openai_llm.py           # OpenAI GPT client (gpt-4o-mini / gpt-4o)
│   └── local_llm.py            # Local Ollama HTTP client (offline Llama 3 / Mistral)
│
├── voice/
│   ├── __init__.py
│   ├── wake_word.py            # Threaded continuous wake word listener ("Hello Mantra")
│   ├── speech_to_text.py       # 16kHz STT with dynamic RMS volume normalization
│   ├── text_to_speech.py       # Neural TTS via edge-tts with MP3 caching
│   └── speaker_verify.py       # Biometric speaker voiceprint enrollment and verification
│
├── apps/
│   ├── __init__.py
│   ├── open_app.py             # Application launcher, process killer, and alias resolver
│   └── music_player.py         # Local offline music player, library indexer & smart filter
│
├── memory/
│   ├── __init__.py
│   └── memory.py               # Long-term persistent key-value memory engine
│
├── system/
│   ├── __init__.py
│   └── system_control.py       # Windows volume, screen brightness & power management
│
├── updater/
│   ├── __init__.py
│   └── updater.py              # GitHub release checker, auto-backup & safe patch extractor
│
├── rag/
│   ├── __init__.py
│   ├── retriever.py            # RAG search and context builder
│   ├── vector_store.py         # ChromaDB vector database interface
│   ├── embeddings.py           # Sentence-transformer embedding model
│   ├── chunker.py              # Document text chunking
│   ├── document_loader.py      # PDF and DOCX document loader
│   └── ingest.py               # Document ingestion pipeline
│
├── Feature Modules (Root)
│   ├── automation.py           # Window management (minimize, maximize, focus)
│   ├── browser.py              # Web searches, tab operations & bookmark manager
│   ├── file_manager.py         # File search, create, rename, copy, move & safe trash
│   ├── screen.py               # Fast screen capture (mss) and video recording (OpenCV)
│   ├── clipboard.py            # Clipboard read, write, cut, copy, paste & clear
│   ├── notes.py                # Persistent interactive notes CRUD
│   └── internet.py             # Weather (OpenWeatherMap), News (NewsAPI), Wikipedia search
│
├── data/
│   ├── config.json             # Master JSON configuration (git-ignored)
│   ├── memory.json             # Stored long-term persistent memories
│   ├── notes.json              # Stored user notes
│   └── vector_db/              # ChromaDB vector database for RAG
│
└── rag_documents/              # Place PDF/DOCX files here for RAG ingestion
    └── (your documents)
```

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- **Operating System:** Windows 10 or Windows 11 (64-bit recommended)
- **Python:** Python 3.10, 3.11, 3.12, 3.13, or 3.14
- **Audio:** Working Microphone and Speakers / Headphones

### 2. Clone the Repository
```bash
git clone https://github.com/raj-aparnathi/MantraAi.git
cd MantraAi
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

> [!TIP]
> **PyAudio on Windows:** If `pip install PyAudio` fails, install via `pipwin`:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

### 4. Set Up API Keys
See the [API Key Setup](#-api-key-setup-env) section below.

### 5. Run Diagnostics (Optional but Recommended)
```bash
python diagnose.py
```

### 6. Launch Mantra AI
```bash
python main.py
```

Say **"Hello Mantra"** to wake the assistant!

---

## 🔑 API Key Setup (.env)

Mantra AI uses a `.env` file to store API keys securely. This file is **git-ignored** and never committed to your repository.

### Quick Setup

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys:
   ```env
   # Required — at least one AI provider key
   GEMINI_API_KEY=your_gemini_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here

   # Optional — for weather and news features
   OPENWEATHER_API_KEY=your_openweather_key_here
   NEWSAPI_KEY=your_newsapi_key_here
   ```

### Where to Get API Keys

| Key | Where to Get It | Required? |
|---|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) | At least one AI key needed |
| `OPENAI_API_KEY` | [OpenAI Platform](https://platform.openai.com/api-keys) | At least one AI key needed |
| `OPENWEATHER_API_KEY` | [OpenWeatherMap](https://openweathermap.org/appid) | Optional (for weather) |
| `NEWSAPI_KEY` | [NewsAPI](https://newsapi.org/register) | Optional (for news) |

> [!IMPORTANT]
> You need **at least one AI provider key** (Gemini or OpenAI) for Mantra to answer questions intelligently. If neither is set, Mantra falls back to Ollama (local LLM) or a polite fallback message.

> [!TIP]
> **Alternative:** API keys can also be set in `data/config.json` under `api_keys`, or as system environment variables. The priority order is: **Environment Variables → `.env` file → `config.json`**.

---

## ⚙️ Configuration Guide (`data/config.json`)

Mantra AI centralizes all settings in `data/config.json`:

```json
{
  "assistant": {
    "name": "Mantra",
    "wake_word": "hello mantra",
    "language": "en-US",
    "version": "3.1",
    "timezone": "Asia/Kolkata"
  },
  "tts": {
    "engine": "edge-tts",
    "voice": "en-US-AvaNeural",
    "rate": 0,
    "pitch": 0,
    "volume": 1.0,
    "voice_preference": "female",
    "english_only": true,
    "chunk_long_replies": true,
    "cache_enabled": true
  },
  "stt": {
    "language": "en-IN",
    "energy_threshold": 250,
    "pause_threshold": 0.7,
    "timeout": 6,
    "phrase_time_limit": 12,
    "sample_rate": 16000,
    "normalize_audio": true,
    "calibration_duration": 1.0
  },
  "api_keys": {
    "gemini": "",
    "openai": "",
    "openweathermap": "",
    "newsapi": ""
  },
  "v3": {
    "ai_provider": "auto",
    "openai_model": "gpt-4o-mini",
    "local_llm_url": "http://localhost:11434",
    "local_llm_model": "llama3"
  },
  "persona": {
    "default_language": "english",
    "max_history_turns": 10,
    "system_prompt": "You are MANTRA, an advanced English-speaking AI voice assistant..."
  }
}
```

> [!NOTE]
> API keys in `config.json` are used as **fallbacks** when the `.env` file or environment variables don't have them set. For security, prefer using the `.env` file.

---

## 🤖 AI Provider Switching

Mantra AI v3.1 supports three AI providers. You can switch between them by changing the `ai_provider` setting in `data/config.json`:

```json
"v3": {
  "ai_provider": "auto"
}
```

### Available Modes

| Mode | Behavior | Best For |
|---|---|---|
| `"auto"` (default) | Tries Gemini → OpenAI → Ollama in order | Maximum reliability — always finds an AI |
| `"gemini"` | Uses only Gemini API → falls back to Ollama | When you prefer Google's AI |
| `"openai"` | Uses only OpenAI API → falls back to Ollama | When you prefer ChatGPT models |

### OpenAI Model Selection

You can change which OpenAI model Mantra uses:

```json
"v3": {
  "openai_model": "gpt-4o-mini"
}
```

Supported models: `gpt-4o-mini` (fast, cheap), `gpt-4o` (most capable), `gpt-3.5-turbo` (legacy).

---

## 🗣️ Voice Command Reference

### 🧠 Memory & Personalization
```
"Remember that my birthday is November 14"
"Remember my favorite color is dark blue"
"What is my birthday?"
"What do you remember?"
"Forget my favorite color"
```

### 🎵 Local Music Player
```
"Play some music" / "Play song Kesariya"
"Next song" / "Previous song"
"Stop the music"
"List all songs" / "Show my songs"
"Songs by artist Arijit Singh"
```

### 💻 App Launching & Window Management
```
"Open Chrome" / "Open VS Code" / "Open Spotify"
"Launch Word" / "Open Excel" / "Open PowerPoint"
"Close Chrome" / "Close Notepad"
"Minimize VS Code" / "Maximize Chrome"
"Switch to Spotify"
```

### 📁 File Manager & Safe Deletion
```
"Create folder Project Alpha"
"Create file meeting_notes"
"Find file quarterly_report"
"Open Downloads" / "Open Documents" / "Open Desktop"
"Delete file draft.txt"             → Safely sent to Windows Recycle Bin
```

### 🖥️ Hardware & Power Controls
```
"Volume up" / "Volume down" / "Mute" / "Unmute"
"Set volume to 80 percent"
"Increase brightness" / "Dim the screen"
"Lock my computer" / "Go to sleep"
"Restart computer"                  → Requires voice confirmation
"Shut down"                         → Requires voice confirmation
```

### 📸 Screen Capture & Video Recording
```
"Take a screenshot"
"Start recording" / "Stop recording"
```

### 📋 Clipboard Tools
```
"Copy that" / "Paste it" / "Cut that"
"Clear clipboard" / "What's in my clipboard?"
```

### 🌐 Web, Search & Bookmarks
```
"Search Python tutorial on Google"
"Search machine learning on YouTube"
"Open YouTube" / "Open GitHub" / "Open Gmail"
"Open bookmark email" / "List my bookmarks"
```

### 🌦️ Weather, News & Knowledge
```
"What is the weather in Delhi?"
"Tell me the latest news headlines"
"Who is Nikola Tesla on Wikipedia?"
"What time is it?" / "What is today's date?"
"Tell me a joke"
```

### 🔄 Updates & Identity
```
"Update" / "Update yourself" / "Mantra, update"
"Check for updates" / "What version are you?"
"Introduce yourself" / "What can you do?"
"Goodbye" / "Bye Mantra" / "Go to sleep"
```

---

## 🧠 Multi-Provider AI Brain

Mantra AI v3.1 features a resilient three-tier AI architecture:

```
User Query ──► Gemini Flash (Online) ──► Success ──► Voice Output
                       │ (Failed / No key)
                       ▼
               OpenAI GPT (Online) ──► Success ──► Voice Output
                       │ (Failed / No key)
                       ▼
               Ollama Local LLM (Offline) ──► Success ──► Voice Output
                       │ (Not running)
                       ▼
               Safe Natural Language Fallback
```

The provider priority is controlled by the `ai_provider` config setting (see [AI Provider Switching](#-ai-provider-switching)).

### Setting up Offline Intelligence with Ollama:
1. Download and install **Ollama** from [ollama.com](https://ollama.com/download).
2. Pull your preferred model:
   ```bash
   ollama pull llama3
   ```
3. Ollama runs a local HTTP service on `http://localhost:11434`. Mantra AI will automatically detect and route queries through Ollama when cloud APIs are unavailable.

---

## 🔒 Speaker Verification (Voice Biometrics)

Optional speaker verification in `voice/speaker_verify.py`.

### Enrollment
```bash
python voice/speaker_verify.py --enroll path/to/my_voice.wav
```

### Verification Test
```bash
python voice/speaker_verify.py --verify path/to/sample.wav
```

---

## 🎵 Local Music Player

Configure your music folder in `data/config.json`:
```json
"music": {
  "folder": "D:\\Music"
}
```

**Supported Formats:** `.mp3`, `.wav`, `.flac`, `.aac`, `.m4a`, `.ogg`.

---

## 📚 RAG Knowledge Base

Mantra AI includes a Retrieval-Augmented Generation (RAG) system that lets you query your own documents.

The embedding model (`all-MiniLM-L6-v2`) is **lazy-loaded** — it only loads when you first ask a RAG question, keeping startup fast.

### Setup
1. Place PDF or DOCX files in the `rag_documents/` folder.
2. Run the ingestion pipeline:
   ```bash
   python -m rag.ingest
   ```
3. Ask Mantra questions about your documents naturally.

---

## 🔄 Self-Update System

Built-in updater (`updater/updater.py`) for safe updates from GitHub.

### Voice Commands
```
"Update"                    → Check + download + apply in one step
"Update yourself"           → Same as above
"Mantra, update"            → Same as above
"Check for updates"         → Only checks, doesn't apply
"What version are you?"     → Reports current version
```

If already on the latest version, Mantra responds: *"I am already up to date."*

### Manual Update
```bash
python updater/updater.py
```

**Safety Features:**
- Automatic code backup before updates (`data/backups/`)
- Never overwrites `config.json`, `memory.json`, `notes.json`
- Downloads and applies updates safely with error recovery

---

## 🛠️ Diagnostics & Troubleshooting

```bash
python diagnose.py
```

### Common Solutions
| Problem | Solution |
|---|---|
| Microphone not detected | Check Windows Settings → Privacy → Microphone access |
| PyAudio install error | `pip install pipwin && pipwin install pyaudio` |
| Gemini API error | Verify `GEMINI_API_KEY` in `.env` |
| OpenAI API error | Verify `OPENAI_API_KEY` in `.env` |
| Local LLM not responding | Ensure Ollama is running and `ollama pull llama3` completed |
| Volume control not working | Verify `pycaw` and `comtypes` are installed |

---

## 📦 Dependencies & Libraries

| Library | Version | Purpose |
|---|---|---|
| `SpeechRecognition` | `>=3.17.0` | Microphone audio capture and Google STT |
| `pyttsx3` | `>=2.90` | Offline TTS with SAPI5 voice selection |
| `edge-tts` | `>=7.0.0` | Neural TTS via Microsoft Edge voices |
| `pygame-ce` | `>=2.5.0` | In-process MP3 playback |
| `PyAudioWPatch` | `>=0.2.12` | Low-level audio stream I/O (Python 3.14 compatible) |
| `audioop-lts` | `>=0.2.1` | audioop shim for Python 3.13+ |
| `pyautogui` | `>=0.9.54` | Keyboard, mouse, and multimedia key emulation |
| `psutil` | `>=6.1.1` | Process management and monitoring |
| `pygetwindow` | `>=0.0.9` | Window management (minimize, maximize, focus) |
| `pycaw` | `>=20240210` | Windows Core Audio volume control |
| `screen-brightness-control` | `>=0.23.0` | Display brightness adjustment |
| `mss` | `>=9.0.2` | Ultra-fast screen grabbing |
| `opencv-python` | `>=4.10.0` | Video processing and MP4 recording |
| `Pillow` | `>=11.0.0` | Image manipulation and screenshot export |
| `pyperclip` | `>=1.9.0` | Clipboard read/write |
| `send2trash` | `>=1.8.3` | Native Recycle Bin deletion |
| `requests` | `>=2.32.3` | HTTP client for all APIs (Gemini, OpenAI, Ollama, Weather, News) |
| `wikipedia` | `>=1.4.0` | Wikipedia search and extraction |
| `python-dotenv` | `>=1.0.0` | Secure `.env` file loading for API keys |
| `chromadb` | `>=1.0.0` | Persistent vector database for RAG |
| `sentence-transformers` | `>=2.0.0` | Embedding model for RAG search (lazy-loaded) |
| `pypdf` | `>=4.0.0` | PDF document loading for RAG |
| `python-docx` | `>=1.0.0` | DOCX document loading for RAG |

---

## 👥 Authors & Acknowledgments

- **Lead Developer:** [Raj Aparnathi](https://github.com/raj-aparnathi)
- **Project:** Mantra AI — Personal Assistant & Desktop Automation Suite
- **Architecture:** Multi-Provider AI v3.1

---

<p align="center">
  <b>Mantra AI v3.1</b> • Built with ❤️ in Python
</p>
