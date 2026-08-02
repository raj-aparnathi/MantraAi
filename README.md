<<<<<<< HEAD
# Mantra AI v2.0 — Desktop Automation Assistant

> **Version 2.0** — Windows Desktop Automation Edition  
> Fully voice-controlled. Wake word: **"Hello Mantra"**

---

## Features

### v1.0 (Preserved)
| Feature | Example Commands |
|---|---|
| Wake Word | *"Hello Mantra"* |
| Greetings & Small Talk | *"How are you?", "Tell me a joke"* |
| Time & Date | *"What time is it?", "What's today's date?"* |
| AI Conversation (Gemini) | Any question |
| Weather | *"What's the weather in Mumbai?"* |
| News Headlines | *"Tell me the latest news"* |
| Wikipedia Search | *"What is quantum computing?"* |
| Notes | *"Add a note: buy milk", "Read my notes"* |
| Open Apps | *"Open Chrome", "Open VS Code"* |
| Browser Search | *"Search Python tutorials on Google"* |
| System Volume | *"Volume up", "Mute"* |
| PC Power | *"Lock my computer", "Restart"* |
| File Creation | *"Create folder Projects", "Create file notes"* |

### v2.0 (New)
| Feature | Example Commands |
|---|---|
| **Natural Language App Launch** | *"Open my coding software", "I want to listen to music"* |
| **Office Apps** | *"Open Word", "Open Excel", "Open PowerPoint"* |
| **Window Control** | *"Minimize VS Code", "Maximize Chrome", "Switch to Spotify"* |
| **Screen Brightness** | *"Increase brightness", "Dim the screen"* |
| **Screenshots** | *"Take a screenshot"* |
| **Screen Recording** | *"Start recording", "Stop recording"* |
| **Clipboard** | *"Copy that", "Paste it", "Clear clipboard", "What's in clipboard?"* |
| **File Search** | *"Find file config", "Search for my AI project"* |
| **File Operations** | *"Rename file", "Copy file", "Move file"* |
| **Safe Delete** | *"Delete file X"* (→ Recycle Bin, not permanent) |
| **Tab Management** | *"Open new tab", "Close tab", "Refresh page"* |
| **Bookmarks** | *"Open bookmark email", "List my bookmarks"* |
| **Running Apps List** | *"What apps are running?"* |

---

## Project Structure

```
MantraAI/
├── main.py              Entry point – wake word loop
├── assistant.py         Command orchestrator / router
├── config.py            Configuration loader
│
├── ── Input/Output ──────────────────────────────────
├── wake_word.py         Wake word detection thread
├── speech_to_text.py    STT via Google Speech API
├── text_to_speech.py    TTS via pyttsx3
│
├── ── Feature Modules ───────────────────────────────
├── conversation.py      Greetings, small talk, Gemini AI
├── automation.py        App open/close/minimize/maximize  [v2.0 extended]
├── browser.py           Web search, tabs, bookmarks       [v2.0 extended]
├── system_control.py    Volume, brightness, power         [v2.0 extended]
├── file_manager.py      Files, search, rename, copy, move [v2.0 extended]
├── notes.py             Note CRUD
├── internet.py          Weather, news, Wikipedia
├── clipboard.py         Copy/paste/cut/clear              [v2.0 new]
├── screen.py            Screenshots & screen recording    [v2.0 new]
│
├── utils.py             Logging, NLP helpers, date/time
│
└── data/
    ├── config.json      All configuration
    └── notes.json       Stored notes
```

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

> **PyAudio on Windows** may fail with pip. Use pipwin instead:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

### 2. Configure `data/config.json`

| Section | What to set |
|---|---|
| `api_keys.gemini` | Your Gemini API key (for AI answers) |
| `api_keys.openweathermap` | For weather feature |
| `api_keys.newsapi` | For news headlines |
| `apps.*` | Verify app paths match your installation |
| `v2.bookmarks` | Add named browser bookmarks |
| `v2.screenshots_dir` | Custom screenshot save folder (optional) |
| `v2.recordings_dir` | Custom recording save folder (optional) |

**Office App Paths** — update these if you use a different Office version:
```json
"word":       "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
"excel":      "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
"powerpoint": "C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE"
```

### 3. Run
```bash
python main.py
```

Say **"Hello Mantra"** to wake up the assistant.

---

## Voice Command Reference

### App Control
```
Open Chrome / VS Code / Spotify / Word / Excel / PowerPoint
Open my coding software         → VS Code
I want to listen to music       → Spotify
Launch the spreadsheet          → Excel
Close Chrome
Minimize VS Code
Maximize Spotify
Switch to Chrome
What apps are running?
```

### File Management
```
Create folder Projects
Create file meeting_notes
Find file config
Search for my AI project folder
Open Downloads / Documents / Desktop
Delete file [name]              → goes to Recycle Bin
```

### System Control
```
Volume up / Volume down
Mute / Unmute
Increase brightness / Dim the screen
Lock my computer
Put the computer to sleep
Restart / Shut down            → voice confirmation required
```

### Screenshots & Recording
```
Take a screenshot              → saved to ~/Pictures/MantraScreenshots/
Start recording                → saved to ~/Videos/MantraRecordings/
Stop recording
```

### Clipboard
```
Copy that / Copy this
Paste it / Paste here
Cut that
Clear clipboard
What's in clipboard?
```

### Browser
```
Open new tab
Close tab
Refresh page
Search Python on Google
Search music videos on YouTube
Open YouTube / GitHub / Gmail
Open bookmark email
List my bookmarks
```

---

## Libraries Used

| Library | Purpose |
|---|---|
| `SpeechRecognition` | Voice → text |
| `pyttsx3` | Text → voice |
| `PyAudio` | Microphone input |
| `pyautogui` | Keyboard/mouse automation |
| `psutil` | Process management |
| `keyboard` | Global hotkeys |
| `pygetwindow` | Window minimize/maximize/focus |
| `pycaw` | Windows volume control |
| `screen-brightness-control` | Screen brightness |
| `mss` | Fast screen capture |
| `opencv-python` | Screen recording (MP4) |
| `Pillow` | Screenshot image saving |
| `pyperclip` | Clipboard read/write |
| `send2trash` | Safe Recycle Bin deletion |
| `requests` | API calls |
| `wikipedia` | Wikipedia search |

---

## Saved File Locations

| Type | Default Location |
|---|---|
| Screenshots | `~/Pictures/MantraScreenshots/screenshot_YYYYMMDD_HHMMSS.png` |
| Recordings | `~/Videos/MantraRecordings/recording_YYYYMMDD_HHMMSS.mp4` |
| Notes | `data/notes.json` |
| Logs | `mantra.log` |

---

## Architecture Notes

- **Modular** – each capability is a self-contained class with `parse_and_execute(text)`
- **Priority routing** – screen/clipboard checked before system control to avoid conflicts
- **NLU intents** – longest-alias-wins matching for natural phrasing
- **Graceful degradation** – missing optional libraries (pygetwindow, sbc, send2trash) fall back with clear messages
- **Safe operations** – destructive actions (shutdown, delete, rename) require voice confirmation

---

*Mantra AI v2.0 — Built with Python*
=======
# MantraAi
Mantra AI – An open-source personal AI assistant with voice interaction, desktop automation, LLM integration, and intelligent task execution.
>>>>>>> 2aeaaed65ff7966a4b6472670b758879e9fd9045
