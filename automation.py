"""
automation.py – Mantra AI v2.0
Desktop application management: open, close, switch, minimize, maximize windows.
Upgraded with:
  - Extended NLU intent matching (natural-language aliases)
  - Window management via pygetwindow (minimize / maximize / switch focus)
  - Support for Microsoft Office apps (Word, Excel, PowerPoint)
  - Dynamic system app search via shutil.which / winreg fallback

Backward compatible with all v1.0 commands.
"""

import subprocess
import os
import shutil
import time
import psutil

import config
from utils import log, normalize, contains_any

# Optional pygetwindow – gracefully degrade if not installed
try:
    import pygetwindow as gw
    _GW_AVAILABLE = True
except ImportError:
    _GW_AVAILABLE = False
    log.warning("pygetwindow not found – window minimize/maximize/switch limited.")


# ── App name aliases → config key ─────────────────────────────────────────────
# v1.0 aliases preserved; v2.0 aliases added below
_APP_ALIASES: dict[str, str] = {
    # Chrome
    "chrome":                "chrome",
    "google chrome":         "chrome",
    "browser":               "chrome",
    "web browser":           "chrome",
    "internet":              "chrome",
    "go online":             "chrome",

    # VS Code
    "vscode":                "vscode",
    "vs code":               "vscode",
    "visual studio code":    "vscode",
    "code":                  "vscode",
    "my coding software":    "vscode",     # NLU
    "code editor":           "vscode",     # NLU
    "programming":           "vscode",     # NLU
    "editor":                "vscode",     # NLU

    # Spotify
    "spotify":               "spotify",
    "music":                 "spotify",
    "music player":          "spotify",
    "listen to music":       "spotify",    # NLU
    "i want to listen to music": "spotify", # NLU
    "want to listen to music":   "spotify", # NLU
    "play music":            "spotify",    # NLU
    "songs":                 "spotify",    # NLU

    # Notepad
    "notepad":               "notepad",
    "text editor":           "notepad",
    "note editor":           "notepad",

    # Calculator
    "calculator":            "calculator",
    "calc":                  "calculator",
    "do math":               "calculator", # NLU

    # File Explorer
    "file explorer":         "explorer",
    "explorer":              "explorer",
    "files":                 "explorer",
    "my computer":           "explorer",
    "my files":              "explorer",   # NLU
    "file manager":          "explorer",   # NLU
    "my documents":          "explorer",   # NLU

    # Microsoft Word
    "word":                  "word",
    "microsoft word":        "word",
    "word document":         "word",
    "word processor":        "word",       # NLU
    "write document":        "word",       # NLU

    # Microsoft Excel
    "excel":                 "excel",
    "microsoft excel":       "excel",
    "spreadsheet":           "excel",      # NLU
    "excel file":            "excel",

    # Microsoft PowerPoint
    "powerpoint":            "powerpoint",
    "microsoft powerpoint":  "powerpoint",
    "presentation":          "powerpoint", # NLU
    "slides":                "powerpoint", # NLU

    # Microsoft Teams
    "teams":                 "teams",
    "microsoft teams":       "teams",
    "meeting":               "teams",      # NLU

    # Task Manager
    "task manager":          "taskmgr",
    "processes":             "taskmgr",    # NLU
}

# ── Process names for psutil matching ────────────────────────────────────────
_PROCESS_NAMES: dict[str, list[str]] = {
    "chrome":      ["chrome.exe"],
    "vscode":      ["code.exe"],
    "spotify":     ["spotify.exe"],
    "notepad":     ["notepad.exe"],
    "calculator":  ["calculatorapp.exe", "calculator.exe"],
    "explorer":    ["explorer.exe"],
    "word":        ["winword.exe"],
    "excel":       ["excel.exe"],
    "powerpoint":  ["powerpnt.exe"],
    "teams":       ["teams.exe", "ms-teams.exe"],
    "taskmgr":     ["taskmgr.exe"],
}

# ── Window title fragments for pygetwindow matching ───────────────────────────
_WINDOW_TITLES: dict[str, list[str]] = {
    "chrome":      ["google chrome", "chrome"],
    "vscode":      ["visual studio code", "vs code"],
    "spotify":     ["spotify"],
    "notepad":     ["notepad"],
    "calculator":  ["calculator"],
    "explorer":    ["file explorer", "this pc", "windows explorer"],
    "word":        ["word"],
    "excel":       ["excel"],
    "powerpoint":  ["powerpoint"],
    "teams":       ["microsoft teams", "teams"],
    "taskmgr":     ["task manager"],
}


class Automation:
    """
    v2.0 desktop automation: open, close, switch, minimize, maximize applications.
    Fully backward compatible with v1.0 command routing.
    """

    # ── Open ───────────────────────────────────────────────────────────────────

    def open_app(self, name: str) -> str:
        """Open application by name. Returns a spoken response."""
        key = self._resolve_key(name)
        if not key:
            # Try system PATH as last resort
            return self._open_from_path(name)

        path = config.APP_PATHS.get(key, "")
        if not path:
            return (
                f"Path for {name} is not configured. "
                "Please update data/config.json."
            )

        try:
            # Built-in shell commands
            if key in ("notepad", "calculator", "explorer", "taskmgr"):
                subprocess.Popen(path, shell=True)
            else:
                subprocess.Popen([path])
            log.info(f"Opened: {key} ({path})")
            return f"Opening {name}."
        except FileNotFoundError:
            log.error(f"App not found at path: {path}")
            return (
                f"I couldn't find {name} at the configured path. "
                "Please update the path in data/config.json."
            )
        except Exception as e:
            log.error(f"Error opening {name}: {e}")
            return f"Sorry, I couldn't open {name}. {e}"

    def _open_from_path(self, name: str) -> str:
        """Attempt to launch an app by searching system PATH."""
        exe = shutil.which(name) or shutil.which(f"{name}.exe")
        if exe:
            try:
                subprocess.Popen([exe])
                log.info(f"Opened system app: {exe}")
                return f"Opening {name}."
            except Exception as e:
                log.error(f"Failed to open {name} from PATH: {e}")
        return f"Sorry, I don't know how to open '{name}'."

    # ── Close ──────────────────────────────────────────────────────────────────

    def close_app(self, name: str) -> str:
        """Terminate all processes matching the app name."""
        key = self._resolve_key(name)
        if not key:
            return f"I don't recognise the application '{name}'."

        proc_names = _PROCESS_NAMES.get(key, [])
        killed = 0
        for proc in psutil.process_iter(["name"]):
            if proc.info["name"] and proc.info["name"].lower() in proc_names:
                try:
                    proc.terminate()
                    killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        if killed:
            log.info(f"Closed {killed} instance(s) of {key}.")
            return f"{name.capitalize()} has been closed."
        return f"{name.capitalize()} doesn't seem to be running."

    # ── Window Control (pygetwindow) ───────────────────────────────────────────

    def switch_to_app(self, name: str) -> str:
        """Bring a running application window to the foreground."""
        key = self._resolve_key(name)
        if key and _GW_AVAILABLE:
            window = self._find_window(key)
            if window:
                try:
                    window.activate()
                    log.info(f"Switched focus to: {name}")
                    return f"Switched to {name}."
                except Exception as e:
                    log.warning(f"Window activate failed ({e}), trying open_app.")
        # Fallback: open the app (Windows brings existing instance to front)
        return self.open_app(name)

    def minimize_window(self, name: str) -> str:
        """Minimize the named application window."""
        key = self._resolve_key(name)
        if _GW_AVAILABLE and key:
            window = self._find_window(key)
            if window:
                try:
                    window.minimize()
                    log.info(f"Minimized: {name}")
                    return f"{name.capitalize()} has been minimized."
                except Exception as e:
                    log.error(f"Minimize error ({name}): {e}")
                    return f"Sorry, I couldn't minimize {name}."
            return f"{name.capitalize()} doesn't seem to be open."
        if not _GW_AVAILABLE:
            return "Window control requires pygetwindow. Please install it."
        return f"I don't recognise '{name}'."

    def maximize_window(self, name: str) -> str:
        """Maximize the named application window."""
        key = self._resolve_key(name)
        if _GW_AVAILABLE and key:
            window = self._find_window(key)
            if window:
                try:
                    window.maximize()
                    log.info(f"Maximized: {name}")
                    return f"{name.capitalize()} has been maximized."
                except Exception as e:
                    log.error(f"Maximize error ({name}): {e}")
                    return f"Sorry, I couldn't maximize {name}."
            return f"{name.capitalize()} doesn't seem to be open."
        if not _GW_AVAILABLE:
            return "Window control requires pygetwindow. Please install it."
        return f"I don't recognise '{name}'."

    def minimize_all(self) -> str:
        """Minimize all open windows (Win+D)."""
        try:
            import pyautogui
            pyautogui.hotkey("win", "d")
            log.info("Minimized all windows (Win+D).")
            return "All windows minimized."
        except Exception as e:
            log.error(f"Minimize all error: {e}")
            return "Sorry, I couldn't minimize all windows."

    def list_running_apps(self) -> str:
        """Return a spoken list of known running applications."""
        running = []
        for key, proc_names in _PROCESS_NAMES.items():
            for proc in psutil.process_iter(["name"]):
                if proc.info.get("name", "").lower() in proc_names:
                    running.append(key.replace("vscode", "VS Code").capitalize())
                    break
        if running:
            return "Currently running: " + ", ".join(running) + "."
        return "I don't see any of the known applications running."

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _resolve_key(self, name: str) -> str | None:
        """Resolve spoken app name to internal config key (longest match wins)."""
        n = normalize(name)
        # Longest alias wins to avoid 'music' matching before 'listen to music'
        matches = [(alias, key) for alias, key in _APP_ALIASES.items() if alias in n]
        if matches:
            return max(matches, key=lambda x: len(x[0]))[1]
        return None

    def _find_window(self, key: str):
        """Find a pygetwindow window by title fragments for the given app key."""
        if not _GW_AVAILABLE:
            return None
        title_fragments = _WINDOW_TITLES.get(key, [key])
        all_windows = gw.getAllWindows()
        for frag in title_fragments:
            for win in all_windows:
                if frag in win.title.lower() and win.visible:
                    return win
        return None

    def parse_and_execute(self, text: str) -> str | None:
        """
        Parse a desktop-automation command and execute it.
        Returns a spoken response or None if command not matched.
        """
        t = normalize(text)

        # Minimize all / show desktop
        if contains_any(t, ["minimize all", "show desktop", "clear desktop",
                             "hide all windows"]):
            return self.minimize_all()

        # List running apps
        if contains_any(t, ["what is running", "list running", "what apps are open",
                             "running apps", "what programs are open", "what apps are running",
                             "list apps", "show running apps", "apps running"]):
            return self.list_running_apps()

        # ── Pure NLU intent matching (no open/launch verb required) ───────────
        # These long-phrase aliases express intent without traditional verbs.
        # Must be checked BEFORE the shorter keyword-gated blocks below.
        _NLU_ONLY_INTENTS: list[tuple[list[str], str]] = [
            (["i want to listen to music", "want to listen to music",
              "listen to some music", "play some music"],              "spotify"),
            (["my coding software", "my code editor", "my programming"],  "vscode"),
            (["my word processor", "write a document", "open a document"], "word"),
            (["do some math", "do math", "need a calculator"],             "calculator"),
            (["my files", "browse files", "view my files"],                "explorer"),
            (["create a presentation", "make a presentation"],             "powerpoint"),
            (["open a spreadsheet", "work on a spreadsheet"],              "excel"),
        ]
        for phrases, key in _NLU_ONLY_INTENTS:
            if any(phrase in t for phrase in phrases):
                return self.open_app(key)

        # Minimize specific window
        if contains_any(t, ["minimize ", "minimise "]):
            for alias in sorted(_APP_ALIASES, key=len, reverse=True):
                if alias in t:
                    return self.minimize_window(alias)

        # Maximize specific window
        if contains_any(t, ["maximize ", "maximise ", "full screen ", "fullscreen "]):
            for alias in sorted(_APP_ALIASES, key=len, reverse=True):
                if alias in t:
                    return self.maximize_window(alias)

        # Close
        if contains_any(t, ["close ", "quit ", "exit ", "kill "]):
            for alias in sorted(_APP_ALIASES, key=len, reverse=True):
                if alias in t:
                    return self.close_app(alias)

        # Switch / bring to foreground
        if contains_any(t, ["switch to ", "go to ", "bring up ", "focus on ",
                             "show ", "open ", "launch ", "start ", "run "]):
            # NLU: check full-phrase aliases first (longest match)
            for alias in sorted(_APP_ALIASES, key=len, reverse=True):
                if alias in t:
                    action = "switch" if contains_any(
                        t, ["switch to", "go to", "bring up", "focus on"]
                    ) else "open"
                    return (
                        self.switch_to_app(alias)
                        if action == "switch"
                        else self.open_app(alias)
                    )

        return None


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    auto = Automation()
    tests = [
        "open my coding software",
        "I want to listen to music",
        "launch the spreadsheet",
        "close chrome",
        "minimize VS Code",
        "what apps are running",
    ]
    for cmd in tests:
        result = auto.parse_and_execute(cmd)
        print(f"CMD: {cmd}\nRES: {result}\n")
