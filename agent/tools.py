"""
agent/tools.py – Mantra AI v3.0
──────────────────────────────────
The Tool Registry — all of Mantra's abilities in one place.

What it does:
  - Wraps every module that can DO something (open apps, control system,
    browse web, manage files, notes, internet, screen, clipboard)
  - Each module has a parse_and_execute(text) method that returns a response
    string if it handled the command, or None if it didn't
  - agent/agent.py calls tools in priority order until one responds

Location : agent/tools.py
Talks to  : All action modules (automation, browser, system_control, etc.)
Used by   : agent/agent.py

Adding a new tool:
  1. Import the module below
  2. Add it to the ToolRegistry constructor
  3. Add it to the TOOL_CHAIN list in the right priority order
  4. Done — agent.py will automatically use it
"""

# ── All action modules ────────────────────────────────────────────────────────
# These are the same modules from v2.0 — now wrapped cleanly by this registry.

from notes         import Notes
from internet      import Internet
from screen        import Screen
from clipboard     import Clipboard
from browser       import Browser
from automation    import Automation
from file_manager  import FileManager

# v3.0 new modules in their proper subfolders
from apps.open_app           import AppLauncher
from apps.music_player       import MusicPlayer
from system.system_control   import SystemControl
from memory.memory           import Memory
from updater.updater         import Updater

from utils import log


class ToolRegistry:
    """
    Holds all of Mantra's action tools and tries them in priority order.

    Usage:
        tools = ToolRegistry()
        response = tools.execute("open chrome")
        # → "Opening Chrome."
    """

    def __init__(self):
        # Create one instance of each tool module
        self.notes          = Notes()
        self.internet       = Internet()
        self.screen         = Screen()
        self.clipboard      = Clipboard()
        self.browser        = Browser()
        self.automation     = Automation()
        self.file_manager   = FileManager()
        self.app_launcher   = AppLauncher()
        self.music_player   = MusicPlayer()
        self.system_control = SystemControl()
        self.memory         = Memory()
        self.updater        = Updater()

        log.info("ToolRegistry: All tools loaded.")

    def execute(self, text: str, confirm_callback=None) -> str | None:
        """
        Try each tool in priority order.
        Returns the first non-None response, or None if no tool matched.

        Priority order (highest first):
          1.  Notes           — create, read, delete notes
          2.  Internet        — weather, news, Wikipedia
          3.  Screen          — screenshot, screen recording
          4.  Clipboard       — copy, paste, read clipboard
          5.  System Control  — volume, brightness, shutdown, lock
          6.  Music Player    — play, stop, next/previous, list local songs (v3.0)
          7.  App Launcher    — open/close Windows apps (v3.0)
          8.  File Manager    — find, create, delete, rename files
          9.  Browser         — open URLs, search Google/YouTube
          10. Automation      — desktop automation, window management
          11. Memory          — remember / recall / forget facts
          12. Updater         — check for and apply updates

        Args:
            text:             The user's spoken/typed command.
            confirm_callback: Optional function for yes/no voice confirmations.

        Returns:
            A response string if a tool handled it, or None.
        """
        # ── 1. Notes ───────────────────────────────────────────────────────────
        response = self.notes.parse_and_execute(
            text, confirm_callback=confirm_callback
        )
        if response:
            return response

        # ── 2. Internet services ───────────────────────────────────────────────
        response = self.internet.parse_and_execute(text)
        if response:
            return response

        # ── 3. Screen utilities ────────────────────────────────────────────────
        response = self.screen.parse_and_execute(text)
        if response:
            return response

        # ── 4. Clipboard ───────────────────────────────────────────────────────
        response = self.clipboard.parse_and_execute(text)
        if response:
            return response

        # ── 5. System Control ──────────────────────────────────────────────────
        response = self.system_control.parse_and_execute(
            text, confirm_callback=confirm_callback
        )
        if response:
            return response

        # ── 6. Music Player (v3.0) ─────────────────────────────────────────────
        response = self.music_player.parse_and_execute(text)
        if response:
            return response

        # ── 7. App Launcher (v3.0) ─────────────────────────────────────────────
        response = self._try_app_launch(text)
        if response:
            return response

        # ── 7. File Manager ────────────────────────────────────────────────────
        response = self.file_manager.parse_and_execute(
            text, confirm_callback=confirm_callback
        )
        if response:
            return response

        # ── 8. Browser ────────────────────────────────────────────────────────
        response = self.browser.parse_and_execute(text)
        if response:
            return response

        # ── 9. Automation ─────────────────────────────────────────────────────
        response = self.automation.parse_and_execute(text)
        if response:
            return response

        # ── 10. Memory ────────────────────────────────────────────────────────
        response = self._try_memory(text)
        if response:
            return response

        # ── 11. Updater ───────────────────────────────────────────────────────
        response = self._try_updater(text)
        if response:
            return response

        return None  # nothing matched — caller will fall back to Brain (LLM)

    # ── Tool-specific intent parsers ──────────────────────────────────────────
    # These handle tools that don't have their own parse_and_execute().

    def _try_app_launch(self, text: str) -> str | None:
        """
        Detect app open/close commands and route to AppLauncher.
        Examples:
          "open chrome"           → opens Chrome
          "close notepad"         → closes Notepad
          "open spotify"          → opens Spotify
        """
        from utils import normalize, contains_any
        t = normalize(text)

        # Open command
        if contains_any(t, ["open ", "launch ", "start ", "run "]):
            # Extract the app name: "open chrome" → "chrome"
            for trigger in ["open ", "launch ", "start ", "run "]:
                if trigger in t:
                    app_name = t.split(trigger, 1)[1].strip()
                    if app_name:
                        return self.app_launcher.open(app_name)

        # Close command
        if contains_any(t, ["close ", "quit ", "exit ", "kill "]):
            for trigger in ["close ", "quit ", "exit ", "kill "]:
                if trigger in t:
                    app_name = t.split(trigger, 1)[1].strip()
                    if app_name:
                        return self.app_launcher.close(app_name)

        return None

    def _try_memory(self, text: str) -> str | None:
        """
        Detect memory commands (remember / recall / forget).
        Examples:
          "remember my wife's name is Priya"  → stores it
          "what is my wife's name"            → recalls it
          "forget my wife's name"             → deletes it
          "what do you remember"              → lists all memories
        """
        from utils import normalize, contains_any
        t = normalize(text)

        # REMEMBER
        if contains_any(t, ["remember ", "note that ", "store that "]):
            # "remember my city is Mumbai" → key="my city", value="Mumbai"
            import re
            match = re.search(r"(?:remember|note that|store that)\s+(.+?)\s+is\s+(.+)", t)
            if match:
                key   = match.group(1).strip()
                value = match.group(2).strip()
                self.memory.remember(key, value)
                return f"Got it! I'll remember that {key} is {value}."
            # Simple: "remember: buy milk" → store as a note
            remainder = t.split("remember", 1)[-1].strip().strip(":")
            if remainder:
                self.memory.remember("last_note", remainder)
                return f"Okay, I'll remember: {remainder}."

        # RECALL
        if contains_any(t, ["what is my ", "recall ", "do you remember ", "what do you know about "]):
            import re
            # "what is my wife's name" → key="wife name"
            match = re.search(r"(?:what is my|recall|do you remember|what do you know about)\s+(.+?)[\?]?$", t)
            if match:
                key   = match.group(1).strip().replace("'s", "").strip()
                value = self.memory.recall(key)
                if value:
                    return f"I remember that {key} is {value}."
                return f"I don't have anything stored for '{key}'."

        # WHAT DO YOU REMEMBER (list all)
        if contains_any(t, ["what do you remember", "list memories", "show memories", "all memories"]):
            all_mem = self.memory.all_memories()
            if not all_mem:
                return "I don't have any memories stored yet."
            items = [f"{k}: {v}" for k, v in all_mem.items()]
            return "Here's what I remember: " + ", ".join(items) + "."

        # FORGET
        if contains_any(t, ["forget ", "delete memory ", "remove memory "]):
            import re
            match = re.search(r"(?:forget|delete memory|remove memory)\s+(.+)", t)
            if match:
                key = match.group(1).strip()
                deleted = self.memory.forget(key)
                if deleted:
                    return f"Done, I've forgotten '{key}'."
                return f"I don't have '{key}' in my memory."

        return None

    def _try_updater(self, text: str) -> str | None:
        """
        Detect update-related commands.
        Examples:
          "check for updates"
          "update yourself"
          "what version are you"
        """
        from utils import normalize, contains_any
        t = normalize(text)

        if contains_any(t, ["check for update", "check update", "any update", "new update"]):
            return self.updater.check_for_update()

        if contains_any(t, ["what version", "your version", "which version", "mantra version"]):
            return f"I am Mantra version {self.updater.current_version()}."

        return None
