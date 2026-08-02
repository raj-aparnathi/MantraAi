"""
assistant.py – Mantra AI v2.0
Core orchestrator. Routes recognized commands to the correct module,
manages the active-session loop, and handles confirmations.

v2.0 additions:
  - Clipboard module integration
  - Screen (screenshot + recording) module integration
  - Routing priority updated to check screen/clipboard early
  - All v1.0 routing preserved and unchanged
"""

import threading

import config
from utils import log, normalize, contains_any
from text_to_speech    import TextToSpeech
from speech_to_text    import SpeechToText
from conversation      import Conversation
from automation        import Automation
from browser           import Browser
from system_control    import SystemControl
from file_manager      import FileManager
from notes             import Notes
from internet          import Internet
from clipboard         import Clipboard   # v2.0
from screen            import Screen      # v2.0


class Assistant:
    """
    Single point of entry for all Mantra AI logic.
    Call `handle_command(text)` with a recognized spoken phrase.
    """

    def __init__(self, tts: TextToSpeech, stt: SpeechToText):
        self.tts   = tts
        self.stt   = stt
        self._lock = threading.Lock()

        # ── v1.0 Feature modules ───────────────────────────────────────────────
        self.conversation   = Conversation()
        self.automation     = Automation()
        self.browser        = Browser()
        self.system_control = SystemControl()
        self.file_manager   = FileManager()
        self.notes          = Notes()
        self.internet       = Internet()

        # ── v2.0 Feature modules ───────────────────────────────────────────────
        self.clipboard      = Clipboard()
        self.screen         = Screen()

        log.info("Assistant v2.0 initialised. All modules loaded.")

    # ── Public ─────────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """Speak a response aloud and log it."""
        self.tts.speak(text)

    def handle_command(self, text: str) -> bool:
        """
        Route a text command to the correct module.

        Returns:
            False if the user said goodbye/exit (signal to end session).
            True  otherwise.
        """
        if not text:
            return True

        log.info(f"Handling command: '{text}'")
        t = normalize(text)

        # ── Exit / Goodbye ─────────────────────────────────────────────────
        if contains_any(t, ["goodbye", "bye", "exit", "quit", "stop listening",
                             "go to sleep", "see you"]):
            response = self.conversation.handle(text)
            self.speak(response or "Goodbye! See you soon.")
            return False          # signal session end

        # ── Notes ──────────────────────────────────────────────────────────
        response = self.notes.parse_and_execute(
            text, confirm_callback=self._voice_confirm
        )
        if response:
            self.speak(response)
            return True

        # ── Internet Services ──────────────────────────────────────────────
        response = self.internet.parse_and_execute(text)
        if response:
            self.speak(response)
            return True

        # ── Screen Utilities (v2.0) ────────────────────────────────────────
        response = self.screen.parse_and_execute(text)
        if response:
            self.speak(response)
            return True

        # ── Clipboard (v2.0) ───────────────────────────────────────────────
        response = self.clipboard.parse_and_execute(text)
        if response:
            self.speak(response)
            return True

        # ── System Control ─────────────────────────────────────────────────
        response = self.system_control.parse_and_execute(
            text, confirm_callback=self._voice_confirm
        )
        if response:
            self.speak(response)
            return True

        # ── File Manager ───────────────────────────────────────────────────
        response = self.file_manager.parse_and_execute(
            text, confirm_callback=self._voice_confirm
        )
        if response:
            self.speak(response)
            return True

        # ── Browser ────────────────────────────────────────────────────────
        response = self.browser.parse_and_execute(text)
        if response:
            self.speak(response)
            return True

        # ── Desktop Automation ─────────────────────────────────────────────
        response = self.automation.parse_and_execute(text)
        if response:
            self.speak(response)
            return True

        # ── Conversation (last resort) ─────────────────────────────────────
        response = self.conversation.handle(text)
        if response:
            self.speak(response)
            return True

        # ── Unknown ────────────────────────────────────────────────────────
        self.speak(
            "Yeh mujhe samajh nahi aaya. Kya aap phir se bata sakte hain?"
        )
        return True

    def run_session(self) -> None:
        """
        Active session: listen for commands until the user says goodbye.
        Called after the wake word is detected.
        """
        # Fresh memory for each new session
        self.conversation.reset_history()

        self.speak(f"Hello! Main hoon {config.ASSISTANT_NAME} version {config.VERSION}. Batao, kya kaam hai?")
        session_active = True

        while session_active:
            log.info("Awaiting command...")
            text = self.stt.listen_and_recognize()

            if text is None:
                # Brief silence / timeout – give one more chance
                self.speak("Kuch sunai nahi diya. Ek baar phir bologe?")
                text = self.stt.listen_and_recognize()
                if text is None:
                    self.speak(
                        "Theek hai, main so jata hoon. "
                        f"Jab zaroorat ho, '{config.WAKE_WORD.title()}' bolna."
                    )
                    break

            session_active = self.handle_command(text)

        log.info("Session ended.")
        self.conversation.reset_history()   # clear memory after session

    # ── Private ────────────────────────────────────────────────────────────────

    def _voice_confirm(self, prompt: str) -> bool:
        """
        Ask a yes/no question via voice.
        Returns True if user responds affirmatively.
        """
        self.speak(prompt)
        answer = self.stt.listen_and_recognize()
        if answer and contains_any(
            normalize(answer), ["yes", "yeah", "yep", "sure", "ok", "confirm"]
        ):
            return True
        self.speak("Okay, cancelled.")
        return False
