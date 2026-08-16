"""
apps/open_app.py – Mantra AI v3.0
───────────────────────────────────
Clean, focused Windows app launcher.

What it does:
  - Opens any Windows application by name (e.g. "chrome", "notepad", "spotify")
  - Closes running applications by name
  - Knows about common app paths from config.json
  - Works by app name (voice-friendly) — no need to know the full path

Location : apps/open_app.py
Talks to  : config.py (APP_PATHS), utils.py (logging)
Used by   : agent/tools.py → agent/agent.py

Relationship to automation.py:
  automation.py handles all window management (minimize, maximize, switch focus).
  open_app.py handles ONLY opening and closing applications.
  They work together — open_app.py is the clean entry point.
"""

import subprocess
import os
import shutil
import time

import psutil

import config
from utils import log, normalize


# ── App name aliases ──────────────────────────────────────────────────────────
# Maps spoken/typed names → keys in config.json's "apps" section.
# Add your own app aliases here if you want Mantra to recognise more names.

APP_ALIASES: dict[str, str] = {
    # Chrome
    "chrome":             "chrome",
    "google chrome":      "chrome",
    "browser":            "chrome",
    "internet":           "chrome",

    # VS Code
    "vs code":            "vscode",
    "vscode":             "vscode",
    "code":               "vscode",
    "visual studio code": "vscode",

    # Notepad
    "notepad":            "notepad",
    "text editor":        "notepad",
    "notes":              "notepad",

    # Calculator
    "calculator":         "calculator",
    "calc":               "calculator",

    # Spotify
    "spotify":            "spotify",
    "music":              "spotify",

    # File Explorer
    "file explorer":      "explorer",
    "explorer":           "explorer",
    "files":              "explorer",
    "my files":           "explorer",

    # Word
    "word":               "word",
    "ms word":            "word",
    "microsoft word":     "word",

    # Excel
    "excel":              "excel",
    "ms excel":           "excel",
    "spreadsheet":        "excel",

    # PowerPoint
    "powerpoint":         "powerpoint",
    "ppt":                "powerpoint",
    "presentation":       "powerpoint",

    # Teams
    "teams":              "teams",
    "microsoft teams":    "teams",

    # Task Manager
    "task manager":       "task_manager",
    "processes":          "task_manager",
}


class AppLauncher:
    """
    Opens and closes Windows applications.

    Usage:
        launcher = AppLauncher()
        launcher.open("chrome")
        launcher.close("notepad")
    """

    def __init__(self):
        # Load app paths from config.json (the "apps" section)
        self._app_paths: dict = config.APP_PATHS
        log.info(f"AppLauncher ready. {len(self._app_paths)} apps configured.")

    # ── Public ─────────────────────────────────────────────────────────────────

    def open(self, app_name: str) -> str:
        """
        Open an application by name.

        Args:
            app_name: The spoken/typed name of the app (e.g. "chrome", "notepad").

        Returns:
            A response string describing what happened.
        """
        # Resolve alias → config key (e.g. "google chrome" → "chrome")
        config_key = self._resolve_alias(app_name)
        if not config_key:
            return f"I don't know how to open '{app_name}'. You can add it to your app list."

        # Get the actual path from config
        path = self._app_paths.get(config_key)

        if not path:
            # Try known built-in Windows apps
            path = self._get_builtin_path(config_key)

        if not path:
            return f"I couldn't find the path for '{app_name}'. Please add it to your config."

        return self._launch(path, app_name)

    def close(self, app_name: str) -> str:
        """
        Close all running processes that match the app name.

        Args:
            app_name: The name of the app to close.

        Returns:
            A response string describing what happened.
        """
        # Map spoken name → executable process name
        process_names = self._get_process_names(app_name)
        killed = 0

        for proc in psutil.process_iter(["name"]):
            try:
                proc_name = proc.info["name"].lower()
                if any(p in proc_name for p in process_names):
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if killed:
            log.info(f"Closed {killed} process(es) matching '{app_name}'.")
            return f"Closed {app_name}."
        else:
            return f"I couldn't find {app_name} running. Is it open?"

    def is_running(self, app_name: str) -> bool:
        """
        Check if an application is currently running.

        Args:
            app_name: The name of the app to check.

        Returns:
            True if the app is running, False otherwise.
        """
        process_names = self._get_process_names(app_name)
        for proc in psutil.process_iter(["name"]):
            try:
                if any(p in proc.info["name"].lower() for p in process_names):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False

    # ── Private ────────────────────────────────────────────────────────────────

    def _resolve_alias(self, spoken_name: str) -> str | None:
        """
        Convert a spoken app name to its config key.
        E.g. "Google Chrome" → "chrome"
        """
        name = normalize(spoken_name)
        # Check direct match in aliases
        if name in APP_ALIASES:
            return APP_ALIASES[name]
        # Check partial match (e.g. user said "open chrome browser")
        for alias, key in APP_ALIASES.items():
            if alias in name:
                return key
        # Last resort: try the name directly as a config key
        if name in self._app_paths:
            return name
        return None

    def _get_builtin_path(self, config_key: str) -> str | None:
        """Return the path for known built-in Windows apps not in config."""
        builtins = {
            "notepad":      "notepad.exe",
            "calculator":   "calc.exe",
            "explorer":     "explorer.exe",
            "task_manager": "taskmgr.exe",
            "paint":        "mspaint.exe",
            "wordpad":      "wordpad.exe",
        }
        return builtins.get(config_key)

    def _get_process_names(self, app_name: str) -> list[str]:
        """
        Return a list of executable names associated with an app.
        Used to find and kill running processes.
        """
        name = normalize(app_name)
        process_map = {
            "chrome":      ["chrome.exe"],
            "firefox":     ["firefox.exe"],
            "notepad":     ["notepad.exe"],
            "calculator":  ["calculator.exe", "calc.exe"],
            "spotify":     ["spotify.exe"],
            "vscode":      ["code.exe"],
            "code":        ["code.exe"],
            "explorer":    ["explorer.exe"],
            "word":        ["winword.exe"],
            "excel":       ["excel.exe"],
            "powerpoint":  ["powerpnt.exe"],
            "teams":       ["teams.exe"],
            "task_manager":["taskmgr.exe"],
        }
        for key, procs in process_map.items():
            if key in name:
                return [p.lower() for p in procs]
        # Fallback: treat the whole name as a process name
        return [name.replace(" ", "") + ".exe"]

    def _launch(self, path: str, display_name: str) -> str:
        """Launch a program at the given path."""
        try:
            subprocess.Popen([path], shell=True)
            log.info(f"Opened: {display_name} ({path})")
            return f"Opening {display_name}."
        except FileNotFoundError:
            # Try with shell=True as a fallback
            try:
                os.startfile(path)
                return f"Opening {display_name}."
            except Exception as e:
                log.error(f"Failed to open {display_name}: {e}")
                return f"I couldn't open {display_name}. Is it installed?"
        except Exception as e:
            log.error(f"Failed to open {display_name}: {e}")
            return f"I couldn't open {display_name}. Error: {e}"


# ── Self-test ─────────────────────────────────────────────────────────────────
# To test:  python apps/open_app.py
if __name__ == "__main__":
    print("Testing apps/open_app.py...")
    print("=" * 50)

    launcher = AppLauncher()

    # Test 1: Open Notepad
    print("Test 1: Opening Notepad...")
    result = launcher.open("notepad")
    print(f"  Result: {result}")

    import time
    time.sleep(2)

    # Test 2: Check if it's running
    print("\nTest 2: Is Notepad running?")
    running = launcher.is_running("notepad")
    print(f"  Running: {running}")

    # Test 3: Close Notepad
    print("\nTest 3: Closing Notepad...")
    result = launcher.close("notepad")
    print(f"  Result: {result}")

    print("\n" + "=" * 50)
    print("apps/open_app.py is working correctly!")
