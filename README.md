# 🎙️ Mantra AI v3.0 — Intelligent Voice & Desktop Automation Agent

<p align="center">
  <img src="https://img.shields.io/badge/Version-3.0_Clean_Architecture-blue.svg?style=for-the-badge" alt="Version 3.0" />
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-brightgreen.svg?style=for-the-badge" alt="Python Version" />
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg?style=for-the-badge&logo=windows" alt="Platform" />
  <img src="https://img.shields.io/badge/AI%20Brain-Gemini%20%2B%20Ollama%20Fallback-orange.svg?style=for-the-badge" alt="Dual Brain" />
  <img src="https://img.shields.io/badge/Voice%20Control-Wake%20Word%20Enabled-red.svg?style=for-the-badge" alt="Voice Control" />
</p>

> **Mantra AI v3.0** is an enterprise-grade, voice-controlled AI desktop assistant and automation system built specifically for Windows. Powered by a **Hybrid Dual-LLM Brain** (Google Gemini Cloud + Local Ollama Offline Fallback), persistent cross-session memory, biometric speaker verification, local media control, and full-spectrum desktop automation.
>
> 🗣️ **Default Wake Word:** `"Hello Mantra"`  
> 🌐 **Persona:** Bilingual Natural Hinglish / English Conversational Agent

---

## 📑 Table of Contents

- [✨ What's New in v3.0](#-whats-new-in-v30)
- [⚡ Feature Matrix](#-feature-matrix)
- [🏗️ System Architecture](#️-system-architecture)
- [📁 Project Structure](#-project-structure)
- [🚀 Quick Start & Installation](#-quick-start--installation)
- [⚙️ Configuration Guide (`data/config.json`)](#️-configuration-guide-dataconfigjson)
- [🗣️ Voice Command Reference](#️-voice-command-reference)
- [🧠 Hybrid Brain & Local LLM (Ollama)](#-hybrid-brain--local-llm-ollama)
- [🔒 Speaker Verification (Voice Biometrics)](#-speaker-verification-voice-biometrics)
- [🎵 Local Music Player](#-local-music-player)
- [🔄 Self-Update System](#-self-update-system)
- [🛠️ Diagnostics & Troubleshooting](#️-diagnostics--troubleshooting)
- [📦 Dependencies & Libraries](#-dependencies--libraries)

---

## ✨ What's New in v3.0

Mantra AI v3.0 represents a complete architectural evolution from a monolithic script into a clean, modular, production-ready system:

1. **Clean Modular Architecture (`agent/`, `brain/`, `voice/`, `apps/`, `memory/`, `system/`, `updater/`)**:
   - Replaced legacy monolithic routing with a dedicated **`Agent` orchestrator** and **`ToolRegistry`** pipeline.
   - Decoupled voice I/O, intelligence reasoning, and system execution into discrete testable packages.

2. **Dual-Brain Hybrid Intelligence (Online + Offline LLM)**:
   - **Primary**: Google Gemini API with persistent multi-turn conversational context and Hinglish persona tuning.
   - **Offline Fallback**: Seamless automatic handover to local **Ollama** (`llama3`, `mistral`, `phi3`) when offline or on API timeout.

3. **Long-Term Persistent Memory Engine (`memory/memory.py`)**:
   - Remembers user preferences, facts, and relationships across restarts (`data/memory.json`).
   - Natural language commands to `remember`, `recall`, `list`, and `forget` facts.

4. **Biometric Speaker Verification (`voice/speaker_verify.py`)**:
   - Optional voiceprint enrollment and cosine similarity verification using Mel-Frequency Cepstral audio embeddings via `resemblyzer`.
   - Restricts assistant activation exclusively to your voice.

5. **Local Music Engine (`apps/music_player.py`)**:
   - Recursive audio indexing (`.mp3`, `.wav`, `.flac`, `.m4a`, `.aac`, `.ogg`).
   - Fuzzy search, random shuffle, playlist traversal (next/prev/stop), and advanced filters (by artist, album, genre, year, composer, lyrics).

6. **Automated Safe Self-Updater (`updater/updater.py`)**:
   - Checks GitHub releases for new updates with changelog inspection.
   - Automatic pre-update timestamped backups of all code files (`data/backups/`).
   - Preserves user configurations (`config.json`, `memory.json`, `notes.json`).

7. **Advanced Audio Processing & Voice Pipeline**:
   - 16 kHz Mono capture with dynamic RMS volume normalization.
   - Ambient noise calibration and exponential network error backoff.

---

## ⚡ Feature Matrix

| Category | Capability | Description | Example Voice Command |
|---|---|---|---|
| **Voice & Wake Word** | Continuous Background Listener | Low-latency wake word detection with active session loop | *"Hello Mantra"* |
| **Hybrid Brain** | Google Gemini + Ollama Fallback | Cloud-scale intelligence with offline local LLM backup | *"Explain quantum computing in simple words"* |
| **Long-Term Memory** | Fact & Preference Persistence | Stores key-value facts across sessions | *"Remember my car is a Honda City"*, *"What is my car?"* |
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
| **Self-Updater** | Version Check & Upgrade | GitHub release inspection, automatic backup, and safe patching | *"Check for updates"*, *"What version are you?"* |

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
                        ▼                                                         ▼
         ┌───────────────────────────────┐                 ┌──────────────────────────────┐
         │     voice/speech_to_text.py        │                 │   voice/speaker_verify.py          │
         │  16kHz Mono + Normalization        │                 │   Biometric Authentication.        │
         └──────────────┬────────────────┘                 └──────────────────────────────┘
                        │ Spoken Text
                        ▼
         ┌────────────────────────────────────────────────────────────────────────┐
         │                          agent/agent.py                                             │
         │   Priority 1: Exit / Bye                                                            │
         │   Priority 2: Built-in fast answers (Time, Date, Greetings, Jokes)                  │
         │   Priority 3: Tool Execution (agent/tools.py)                                       │
         │   Priority 4: AI Reasoning Fallback (brain/brain.py)                                │
         └──────────────┬──────────────────────────────────────────┬──────────────┘
                           │                                                │
        ┌───────────────┴───────────────┐          ┌───────────────┴──────────────┐
        ▼                                    ▼         ▼                                   ▼
┌───────────────────────────────┐ ┌────────────────────────────────┐ ┌───────────────────────────┐
│       agent/tools.py                │ │       brain/brain.py                │ │   voice/text_to_speech.py      │
│ ├── apps/open_app.py               │ │ ├── brain/llm_api.py (Gemini)       │ │ SAPI5 / pyttsx3 Engine         │
│ ├── apps/music_player.py           │ │ └── brain/local_llm.py (Ollama).    │ └───────────────────────────┘
│ ├── system/system_control.py.      │ └────────────────────────────────┘
│ ├── memory/memory.py               │
│ ├── automation.py                  │
│ ├── file_manager.py                │
│ ├── browser.py                     │
│ ├── screen.py                      │
│ ├── clipboard.py                   │
│ ├── notes.py                       │
│ ├── internet.py                    │
│ └── updater/updater.py             │
└───────────────────────────────┘
```

---

## 📁 Project Structure

```
MantraAI/
├── main.py                     # Entry point — wake word listener & session lifecycle loop
├── config.py                   # Centralized configuration parser and global settings
├── utils.py                    # Logging engine, NLP text normalizer, date/time utilities
├── diagnose.py                 # System diagnostic & dependency verification tool
├── requirements.txt            # Python package specifications
├── mantra.log                  # Rolling application log file
│
├── ── agent/ ─────────────────────────────────────────────────────────────
│   ├── __init__.py
│   ├── agent.py                # Core Agent: session manager, built-in responses & dispatch
│   └── tools.py                # ToolRegistry: priority-based execution router for all tools
│
├── ── brain/ ─────────────────────────────────────────────────────────────
│   ├── __init__.py
│   ├── brain.py                # LLM Router: tries Gemini Cloud API → falls back to Ollama
│   ├── llm_api.py              # Google Gemini 2.5/3.6 Flash client with conversation memory
│   └── local_llm.py            # Local Ollama HTTP client (offline Llama 3 / Mistral)
│
├── ── voice/ ─────────────────────────────────────────────────────────────
│   ├── __init__.py
│   ├── wake_word.py            # Threaded continuous wake word listener ("Hello Mantra")
│   ├── speech_to_text.py       # 16kHz STT with dynamic RMS volume normalization
│   ├── text_to_speech.py       # Thread-safe Windows SAPI5 TTS engine
│   └── speaker_verify.py       # Biometric speaker voiceprint enrollment and verification
│
├── ── apps/ ──────────────────────────────────────────────────────────────
│   ├── __init__.py
│   ├── open_app.py             # Application launcher, process killer, and alias resolver
│   └── music_player.py         # Local offline music player, library indexer & smart filter
│
├── ── memory/ ────────────────────────────────────────────────────────────
│   ├── __init__.py
│   └── memory.py               # Long-term persistent key-value memory engine
│
├── ── system/ ────────────────────────────────────────────────────────────
│   ├── __init__.py
│   └── system_control.py       # Windows master volume, screen brightness & power management
│
├── ── updater/ ───────────────────────────────────────────────────────────
│   ├── __init__.py
│   └── updater.py              # GitHub release checker, auto-backup & safe patch extractor
│
├── ── Feature Modules (Root) ─────────────────────────────────────────────
│   ├── automation.py           # Window management (minimize, maximize, focus, Office 365)
│   ├── browser.py              # Web searches, tab operations & bookmark manager
│   ├── file_manager.py         # File search, create, rename, copy, move & safe trash
│   ├── screen.py               # Fast screen capture (mss) and video recording (OpenCV)
│   ├── clipboard.py            # Clipboard read, write, cut, copy, paste & clear
│   ├── notes.py                # Persistent interactive notes CRUD
│   └── internet.py             # Weather (OpenWeatherMap), News (NewsAPI), Wikipedia search
│
└── ── data/ ──────────────────────────────────────────────────────────────
    ├── config.json             # Master JSON configuration (keys, paths, settings)
    ├── memory.json             # Stored long-term persistent memories
    ├── notes.json              # Stored user notes
    └── backups/                # Automatic pre-update backup archives
```

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- **Operating System:** Windows 10 or Windows 11 (64-bit recommended)
- **Python:** Python 3.10, 3.11, or 3.12
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

### 4. Configure `data/config.json`
Add your API keys in `data/config.json`:
- **Gemini API Key:** Required for cloud AI conversation ([Get a free key from Google AI Studio](https://aistudio.google.com/)).
- **OpenWeatherMap Key:** (Optional) For live weather updates.
- **NewsAPI Key:** (Optional) For live news headlines.

### 5. Run Diagnostics (Optional but Recommended)
Verify your audio devices, libraries, and configurations:
```bash
python diagnose.py
```

### 6. Launch Mantra AI
```bash
python main.py
```

Say **"Hello Mantra"** to wake the assistant!

---

## ⚙️ Configuration Guide (`data/config.json`)

Mantra AI v3.0 centralizes all settings in `data/config.json`:

```json
{
  "assistant": {
    "name": "Mantra",
    "wake_word": "hello mantra",
    "language": "en-US",
    "version": "3.0",
    "timezone": "Asia/Kolkata"
  },
  "tts": {
    "rate": 0,
    "volume": 1.0,
    "voice_preference": "female"
  },
  "stt": {
    "energy_threshold": 200,
    "pause_threshold": 1.2,
    "timeout": 10,
    "phrase_time_limit": 20,
    "sample_rate": 16000,
    "normalize_audio": true,
    "calibration_duration": 2.0
  },
  "api_keys": {
    "gemini": "YOUR_GEMINI_API_KEY",
    "openweathermap": "YOUR_OPENWEATHER_KEY",
    "newsapi": "YOUR_NEWSAPI_KEY"
  },
  "weather": {
    "default_city": "Mumbai",
    "units": "metric"
  },
  "apps": {
    "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "vscode": "C:\\Users\\Username\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe",
    "spotify": "C:\\Users\\Username\\AppData\\Roaming\\Spotify\\Spotify.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "word": "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
    "excel": "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
    "powerpoint": "C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE"
  },
  "music": {
    "folder": "D:\\Music"
  },
  "v2": {
    "screenshots_dir": "D:\\Pictures\\Screenshots",
    "recordings_dir": "D:\\Videos\\Screen Recordings",
    "volume_step": 0.1,
    "brightness_step": 10,
    "bookmarks": {
      "email": "https://mail.google.com",
      "calendar": "https://calendar.google.com",
      "drive": "https://drive.google.com",
      "github": "https://github.com"
    }
  },
  "v3": {
    "local_llm_url": "http://localhost:11434",
    "local_llm_model": "llama3",
    "memory_file": "",
    "updater_repo": "https://github.com/raj-aparnathi/MantraAi.git"
  },
  "persona": {
    "default_language": "hinglish",
    "max_history_turns": 10,
    "system_prompt": "You are MANTRA, an advanced AI assistant designed to communicate naturally, intelligently, and helpfully in Hinglish or English..."
  }
}
```

---

## 🗣️ Voice Command Reference

### 🧠 Memory & Personalization (v3.0)
```
"Remember that my birthday is November 14"
"Remember my favorite color is dark blue"
"What is my birthday?"
"What do you remember?"
"Forget my favorite color"
```

### 🎵 Local Music Player (v3.0)
```
"Play some music" / "Gana bajao"
"Play song Kesariya" / "Play Believer"
"Next song" / "Previous song" / "Agla gana"
"Stop the music" / "Music band karo"
"List all songs" / "Show my songs"
"Songs by artist Arijit Singh"
"Songs from album Rockstar"
```

### 💻 App Launching & Window Management
```
"Open Chrome" / "Open VS Code" / "Open Spotify"
"Launch Word" / "Open Excel" / "Open PowerPoint"
"Open my coding software"           → Opens VS Code
"I want to listen to music"         → Opens Spotify
"Close Chrome" / "Close Notepad"
"Minimize VS Code" / "Maximize Chrome"
"Switch to Spotify"
"What apps are running?"
```

### 📁 File Manager & Safe Deletion
```
"Create folder Project Alpha"
"Create file meeting_notes"
"Find file quarterly_report"
"Search for AI project folder"
"Open Downloads" / "Open Documents" / "Open Desktop"
"Delete file draft.txt"             → Safely sent to Windows Recycle Bin
```

### 🖥️ Hardware & Power Controls
```
"Volume up" / "Volume down" / "Mute" / "Unmute"
"Set volume to 80 percent"
"Increase brightness" / "Dim the screen" / "Set brightness to 50"
"Lock my computer" / "Go to sleep"
"Restart computer"                  → Requires voice confirmation ("yes"/"no")
"Shut down"                         → Requires voice confirmation
"Cancel shutdown"
```

### 📸 Screen Capture & Video Recording
```
"Take a screenshot"                 → Saved to configured Screenshots folder
"Start recording"                   → Records screen in MP4 format
"Stop recording"                    → Finalizes and saves MP4 video
```

### 📋 Clipboard Tools
```
"Copy that" / "Copy this"
"Paste it" / "Paste here"
"Cut that"
"Clear clipboard"
"What's in my clipboard?"
```

### 🌐 Web, Search & Bookmarks
```
"Search Python tutorial on Google"
"Search machine learning on YouTube"
"Open YouTube" / "Open GitHub" / "Open Gmail"
"Open bookmark email" / "Open bookmark drive"
"List my bookmarks"
"Open new tab" / "Close tab" / "Refresh page"
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
"Check for updates"
"What version are you?"
"Introduce yourself" / "What can you do?"
"Goodbye" / "Bye Mantra" / "Go to sleep"
```

---

## 🧠 Hybrid Brain & Local LLM (Ollama)

Mantra AI v3.0 features a resilient two-tier AI architecture:

```
User Query ──► Gemini 2.5/3.6 Flash (Online) ──► Success ──► Voice Output
                       │ (Network failure / No key / Rate limit)
                       ▼
               Ollama Local LLM (Offline Llama 3 / Mistral) ──► Voice Output
                       │ (Ollama not running)
                       ▼
               Safe Natural Language Fallback
```

### Setting up Offline Intelligence with Ollama:
1. Download and install **Ollama** from [ollama.com](https://ollama.com/download).
2. Pull your preferred model in your terminal:
   ```bash
   ollama pull llama3
   ```
3. Ollama runs a local HTTP service on `http://localhost:11434`. Mantra AI will automatically detect and route queries through Ollama when offline!

---

## 🔒 Speaker Verification (Voice Biometrics)

Mantra AI v3.0 includes an optional speaker verification subsystem located in `voice/speaker_verify.py`.

### 1. Enrollment
Record a 5–10 second WAV file of yourself speaking naturally (e.g., saying *"Hello Mantra"* 4–5 times) using Windows Sound Recorder, then run:
```bash
python voice/speaker_verify.py --enroll path/to/my_voice.wav
```
This extracts your MFCC voiceprint embedding and saves it securely to `data/voiceprint.json`.

### 2. Verification Test
```bash
python voice/speaker_verify.py --verify path/to/sample.wav
```

---

## 🎵 Local Music Player

Mantra AI v3.0 includes a dedicated local audio player (`apps/music_player.py`) that scans your personal library without needing third-party streaming services:

- **Configure your music folder** in `data/config.json`:
  ```json
  "music": {
    "folder": "D:\\Music"
  }
  ```
- **Supported Formats:** `.mp3`, `.wav`, `.flac`, `.aac`, `.m4a`, `.ogg`.
- Supports random shuffle, exact song search, and attribute filters (artist, album, genre, year, composer, lyrics).

---

## 🔄 Self-Update System

Mantra AI v3.0 includes a built-in updater (`updater/updater.py`) for safe updates from GitHub:

```bash
# Test update status directly
python updater/updater.py
```

### Safety Features:
- **Automatic Code Backup:** Creates a timestamped archive of all source files in `data/backups/` before any files are modified.
- **Protected User Data:** Never overwrites or touches `data/config.json`, `data/memory.json`, `data/notes.json`, or log files.
- **Voice Confirmation Required:** Never updates without user authorization.

---

## 🛠️ Diagnostics & Troubleshooting

Run the included diagnostic script to test your environment:
```bash
python diagnose.py
```

### Common Solutions:
- **Microphone not detected:** Check Windows Settings > Privacy & Security > Microphone and ensure desktop apps have access.
- **PyAudio install error:** Run `pip install pipwin` followed by `pipwin install pyaudio`.
- **Gemini API Error:** Verify your API key in `data/config.json` or ensure `GEMINI_API_KEY` is set in your environment.
- **Local LLM not responding:** Ensure Ollama is running (`ollama serve` or desktop tray app) and `ollama pull llama3` has finished.
- **Volume control not working:** Verify `pycaw` and `comtypes` are installed.

---

## 📦 Dependencies & Libraries

| Library | Version | Purpose |
|---|---|---|
| `SpeechRecognition` | `3.17.0` | Microphone audio capture and Google Speech-to-Text conversion |
| `pyttsx3` | `2.90` | Offline text-to-speech synthesis with SAPI5 voice selection |
| `PyAudio` | `0.2.14` | Low-level cross-platform audio stream I/O |
| `pyautogui` | `0.9.54` | Programmatic keyboard, mouse, and multimedia key emulation |
| `psutil` | `6.1.1` | Process management, app lifecycle monitoring, and process termination |
| `pygetwindow` | `0.0.9` | Windows GUI management (minimize, maximize, window focus) |
| `pycaw` | `20240210` | Core Audio Windows API wrapper for precision volume control |
| `screen-brightness-control`| `0.23.0` | Display brightness querying and adjustment |
| `mss` | `9.0.2` | Ultra-fast cross-platform screen grabbing |
| `opencv-python` | `4.10.0.84` | Video stream processing and MP4 screen recording |
| `Pillow` | `11.2.1` | Image manipulation and screenshot file export |
| `pyperclip` | `1.9.0` | Cross-platform clipboard read/write engine |
| `send2trash` | `1.8.3` | Native Windows Recycle Bin deletion (prevents accidental file loss) |
| `requests` | `2.32.3` | HTTP client for Gemini API, Ollama server, Weather, and News APIs |
| `wikipedia` | `1.4.0` | Wikipedia encyclopedia search and extraction |
| `resemblyzer` *(Optional)* | Latest | Deep learning voice encoder for biometric speaker verification |

---

## 👥 Authors & Acknowledgments

- **Lead Developer:** [Raj Aparnathi](https://github.com/raj-aparnathi)
- **Project:** Mantra AI — Personal Assistant & Desktop Automation Suite
- **Architecture:** Clean Architecture v3.0

---

<p align="center">
  <b>Mantra AI v3.0</b> • Built with ❤️ in Python
</p>
