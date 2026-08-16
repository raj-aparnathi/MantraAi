"""
agent/agent.py – Mantra AI v3.0
──────────────────────────────────
The Agent — Mantra's brain-to-action orchestrator.

What it does:
  1. Receives text (from speech-to-text or typed input)
  2. Tries to handle it with a tool (from agent/tools.py)
  3. If no tool matches → asks the Brain (LLM) for a conversational reply
  4. Returns the response text to the caller

This is the v3.0 evolution of assistant.py.
It is cleaner because:
  - Tools are managed by ToolRegistry (not scattered through assistant.py)
  - LLM calls go through brain/brain.py (not directly to Gemini API)
  - Built-in responses (greetings, time, date) are still here for speed
  - Memory is persistent (memory/memory.py) across sessions

Location : agent/agent.py
Talks to  : agent/tools.py, brain/brain.py
Used by   : main.py

Architecture flow:
  main.py
    ↓
  agent/agent.py  (you are here)
    ├→  agent/tools.py   (execute a tool: apps, system, browser, files...)
    └→  brain/brain.py   (ask LLM: Gemini API or local Ollama)
"""

import random
import threading

import config
from utils import log, normalize, contains_any, get_time, get_date, get_greeting_period

# v3.0 modules
from brain.brain   import Brain         # LLM router (Gemini + local LLM)
from agent.tools   import ToolRegistry  # all action tools
from memory.memory import Memory        # persistent memory


# ── Built-in response banks ───────────────────────────────────────────────────
# These handle common phrases instantly, without hitting the LLM.
# Fast, offline, and 100% reliable.

_GREETINGS = [
    "Hello! How can I help you today?",
    "Hi there! What can I do for you?",
    "Hey! I'm ready to assist. What do you need?",
]

_HOW_ARE_YOU = [
    "I'm doing great, thanks for asking! How about you?",
    "All systems running perfectly and ready to assist you!",
    "Doing fantastic! What can I help you with today?",
]

_IDENTITY = [
    f"I am {config.ASSISTANT_NAME}, your personal AI assistant, version {config.VERSION}. "
    "I can control your Windows PC, answer questions, manage files, and much more.",
    f"My name is {config.ASSISTANT_NAME}. I'm a voice-controlled AI assistant built to help you.",
]

_THANKS = [
    "You're welcome! Let me know if you need anything else.",
    "Happy to help! Feel free to ask if you need more assistance.",
    "Anytime! Is there anything else I can do for you?",
]

_JOKES = [
    "A programmer told his friend, I'm stuck in a loop. The friend asked, since when? The programmer replied, I don't know, I'm in a loop!",
    "What is a bug? It's a feature that hasn't been documented yet.",
    "I told my computer I needed a break. Now it keeps sending me Kit-Kat ads.",
]

_BYE = [
    "Alright, see you later! Take care.",
    f"Goodbye! Say '{config.WAKE_WORD.title()}' whenever you need me.",
]


class Agent:
    """
    v3.0 Agent — Mantra's command router and session manager.

    Call `run_session()` after the wake word is detected.
    It loops until the user says goodbye.
    """

    def __init__(self, tts, stt):
        """
        Args:
            tts: TextToSpeech instance (from voice/text_to_speech.py)
            stt: SpeechToText instance (from voice/speech_to_text.py)
        """
        self.tts   = tts
        self.stt   = stt
        self._lock = threading.Lock()

        # v3.0: Brain (LLM router) and Tool registry
        self.brain = Brain()
        self.tools = ToolRegistry()

        log.info("Agent v3.0 initialised. Brain and ToolRegistry ready.")

    # ── Public ─────────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """Speak a response aloud and log it."""
        self.tts.speak(text)

    def handle_command(self, text: str) -> bool:
        """
        Route a text command to the right handler.

        Priority:
          1. Exit check        → end the session
          2. Built-in replies  → greetings, time, date, jokes (fast, offline)
          3. Tools             → apps, system, browser, files, memory, etc.
          4. Brain (LLM)       → Gemini or local LLM for anything else

        Returns:
            False  → session should end (user said goodbye)
            True   → session continues
        """
        if not text:
            return True

        log.info(f"Agent handling: '{text}'")
        t = normalize(text)

        # ── 1. Exit / Goodbye ──────────────────────────────────────────────────
        if contains_any(t, ["goodbye", "bye", "exit", "quit", "stop listening",
                             "go to sleep", "see you"]):
            response = random.choice(_BYE)
            self.speak(response)
            return False   # signal session end

        # ── 2. Built-in fast replies ───────────────────────────────────────────
        builtin = self._check_builtin(t, text)
        if builtin:
            self.speak(builtin)
            return True

        # ── 3. Tools ──────────────────────────────────────────────────────────
        tool_response = self.tools.execute(text, confirm_callback=self._voice_confirm)
        if tool_response:
            self.speak(tool_response)
            return True

        # ── 4. Brain (LLM) — last resort ──────────────────────────────────────
        log.info("Agent: No tool matched. Asking Brain (LLM)...")
        llm_response = self.brain.think(text)
        self.speak(llm_response)
        return True

    def run_session(self) -> None:
        """
        Active voice session: listen for commands until the user says goodbye.
        Called by main.py after the wake word is detected.
        """
        # Reset LLM conversation memory at the start of each new session
        self.brain.reset_history()

        self.speak(
            f"Hello! I am {config.ASSISTANT_NAME} version {config.VERSION}. "
            "How can I help you?"
        )
        session_active = True

        while session_active:
            log.info("Agent: Awaiting command...")
            text = self.stt.listen_and_recognize()

            if text is None:
                # Nothing heard — give one more chance
                self.speak("I didn't hear anything. Could you say that again?")
                text = self.stt.listen_and_recognize()
                if text is None:
                    self.speak(
                        "Alright, going to sleep. "
                        f"Say '{config.WAKE_WORD.title()}' whenever you need me."
                    )
                    break

            session_active = self.handle_command(text)

        # Clear LLM history at session end (don't leak memory between sessions)
        self.brain.reset_history()
        log.info("Agent: Session ended.")

    # ── Private ────────────────────────────────────────────────────────────────

    def _check_builtin(self, t: str, original: str) -> str | None:
        """
        Check for common built-in phrases that don't need the LLM.
        These respond instantly without network access.

        Args:
            t:        Normalised (lowercase) text for pattern matching.
            original: Original text for passing to LLM if needed.

        Returns:
            A response string, or None if no built-in matched.
        """
        # Greetings
        if contains_any(t, ["hello", "hi ", "hey ", "good day"]):
            return random.choice(_GREETINGS)

        if "good morning" in t:
            return f"Good morning! Hope you have a great day ahead. What can I help with?"

        if "good afternoon" in t:
            return f"Good afternoon! I'm here and ready. What do you need?"

        if "good evening" in t or "good night" in t:
            return f"Good evening! How was your day? What can I do for you?"

        # How are you
        if contains_any(t, ["how are you", "how r u", "how do you do"]):
            return random.choice(_HOW_ARE_YOU)

        # Identity
        if contains_any(t, ["who are you", "your name", "what are you", "introduce yourself"]):
            return random.choice(_IDENTITY)

        # Thanks
        if contains_any(t, ["thank you", "thanks", "thank u", "cheers"]):
            return random.choice(_THANKS)

        # Time — answered locally (no LLM needed!)
        if contains_any(t, ["what time", "current time", "time is it"]):
            return f"The current time is {get_time()}."

        # Date — answered locally
        if contains_any(t, ["what date", "today date", "what day", "current date"]):
            return f"Today is {get_date()}."

        # Jokes
        if contains_any(t, ["joke", "make me laugh", "something funny"]):
            return random.choice(_JOKES)

        # Capabilities
        if contains_any(t, ["what can you do", "your abilities", "your features",
                             "capabilities", "help me"]):
            return (
                f"I am {config.ASSISTANT_NAME} version {config.VERSION}. "
                "I can open, close, and control any Windows app. "
                "I can manage files, control volume and brightness, "
                "take screenshots, search the web, check the weather, "
                "remember things, and answer any question. "
                "Just tell me what you need!"
            )

        return None  # no built-in matched

    def _voice_confirm(self, prompt: str) -> bool:
        """
        Ask a yes/no question via voice and return the user's answer.

        Args:
            prompt: The yes/no question to ask (e.g. "Are you sure you want to shut down?")

        Returns:
            True if user confirmed (yes/yeah/ok/sure).
            False otherwise (and Mantra says "Okay, cancelled.").
        """
        self.speak(prompt)
        answer = self.stt.listen_and_recognize()
        if answer and contains_any(
            normalize(answer), ["yes", "yeah", "yep", "sure", "ok", "confirm", "do it"]
        ):
            return True
        self.speak("Okay, cancelled.")
        return False
