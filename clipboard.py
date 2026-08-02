"""
clipboard.py – Mantra AI v2.0
Clipboard automation: copy, paste, cut, and clear clipboard contents
using pyperclip (cross-platform) with full voice-command routing.
"""

import pyperclip
import pyautogui
import time

from utils import log, normalize, contains_any


class Clipboard:
    """
    Provides clipboard operations accessible via natural voice commands.

    Supported actions:
        copy   – copy currently selected text (Ctrl+C) and report contents
        paste  – paste current clipboard at cursor position (Ctrl+V)
        cut    – cut currently selected text (Ctrl+X)
        clear  – empty the clipboard
        read   – speak the current clipboard contents
    """

    # ── Public API ─────────────────────────────────────────────────────────────

    def copy(self) -> str:
        """
        Simulate Ctrl+C to copy selected text and confirm contents.
        Returns a spoken response.
        """
        try:
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.15)          # let OS populate the clipboard
            contents = pyperclip.paste().strip()
            if contents:
                preview = contents[:60] + ("..." if len(contents) > 60 else "")
                log.info(f"Clipboard copy: '{preview}'")
                return f"Copied to clipboard: {preview}"
            log.info("Clipboard copy executed (clipboard appears empty).")
            return "Copied to clipboard."
        except Exception as e:
            log.error(f"Clipboard copy error: {e}")
            return f"Sorry, I couldn't copy. {e}"

    def paste(self) -> str:
        """
        Simulate Ctrl+V to paste clipboard contents at cursor position.
        Returns a spoken response.
        """
        try:
            contents = pyperclip.paste().strip()
            if not contents:
                return "The clipboard is empty, nothing to paste."
            pyautogui.hotkey("ctrl", "v")
            log.info("Clipboard paste executed.")
            return "Pasted from clipboard."
        except Exception as e:
            log.error(f"Clipboard paste error: {e}")
            return f"Sorry, I couldn't paste. {e}"

    def cut(self) -> str:
        """
        Simulate Ctrl+X to cut selected text.
        Returns a spoken response.
        """
        try:
            pyautogui.hotkey("ctrl", "x")
            time.sleep(0.15)
            contents = pyperclip.paste().strip()
            if contents:
                preview = contents[:60] + ("..." if len(contents) > 60 else "")
                log.info(f"Clipboard cut: '{preview}'")
                return f"Cut to clipboard: {preview}"
            log.info("Clipboard cut executed.")
            return "Cut to clipboard."
        except Exception as e:
            log.error(f"Clipboard cut error: {e}")
            return f"Sorry, I couldn't cut. {e}"

    def clear(self) -> str:
        """
        Empty the clipboard.
        Returns a spoken response.
        """
        try:
            pyperclip.copy("")
            log.info("Clipboard cleared.")
            return "Clipboard has been cleared."
        except Exception as e:
            log.error(f"Clipboard clear error: {e}")
            return f"Sorry, I couldn't clear the clipboard. {e}"

    def read_clipboard(self) -> str:
        """
        Read and speak the current clipboard contents.
        Returns a spoken response.
        """
        try:
            contents = pyperclip.paste().strip()
            if not contents:
                return "The clipboard is empty."
            preview = contents[:200] + (" and more" if len(contents) > 200 else "")
            log.info(f"Clipboard read: {len(contents)} chars.")
            return f"Your clipboard contains: {preview}"
        except Exception as e:
            log.error(f"Clipboard read error: {e}")
            return "Sorry, I couldn't read the clipboard."

    def set_text(self, text: str) -> str:
        """
        Programmatically write `text` to the clipboard.
        Returns a spoken response.
        """
        try:
            pyperclip.copy(text)
            log.info(f"Clipboard set to: '{text[:60]}'")
            return f"Copied '{text}' to clipboard."
        except Exception as e:
            log.error(f"Clipboard set error: {e}")
            return f"Sorry, I couldn't write to the clipboard. {e}"

    # ── Command Router ─────────────────────────────────────────────────────────

    def parse_and_execute(self, text: str) -> str | None:
        """
        Parse a clipboard-related voice command and execute it.
        Returns a spoken response, or None if not a clipboard command.
        """
        t = normalize(text)

        # Clear
        if contains_any(t, ["clear clipboard", "empty clipboard", "wipe clipboard",
                             "delete clipboard", "erase clipboard"]):
            return self.clear()

        # Read / show clipboard
        if contains_any(t, ["read clipboard", "what is in clipboard", "show clipboard",
                             "whats in clipboard", "clipboard contents", "clipboard content"]):
            return self.read_clipboard()

        # Cut
        if contains_any(t, ["cut that", "cut this", "cut selection", "cut selected",
                             "cut the text"]):
            return self.cut()

        # Copy
        if contains_any(t, ["copy that", "copy this", "copy selection", "copy selected",
                             "copy the text", "copy it"]):
            return self.copy()

        # Paste
        if contains_any(t, ["paste that", "paste this", "paste it", "paste here",
                             "paste text", "paste clipboard"]):
            return self.paste()

        return None


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cb = Clipboard()
    print(cb.set_text("Hello from Mantra AI v2.0!"))
    print(cb.read_clipboard())
    print(cb.clear())
    print(cb.read_clipboard())
