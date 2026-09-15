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
from pathlib import Path

import config
from utils import log, normalize, contains_any, get_time, get_date, get_greeting_period

# v3.0 modules
from brain.brain   import Brain         # LLM router (Gemini + local LLM)
from agent.tools   import ToolRegistry  # all action tools
from memory.memory import Memory        # persistent memory
from rag.retriever import Retriever

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

# Short, natural session openers. A quick "yes?" feels far more human than
# re-introducing itself every time — and it gets to listening ~2 s sooner.
_SESSION_OPENERS = [
    "Yes? I'm listening.",
    "I'm here. What do you need?",
    "Hey, what can I do for you?",
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

        # RAG retriever — initialised here so we can check for relevant
        # documents BEFORE the command reaches generic tools (Wikipedia etc.).
        try:
            self.retriever = Retriever()
            log.info(
                f"Agent: RAG Retriever ready. "
                f"Documents: {self.retriever.document_count()}"
            )
        except Exception as e:
            self.retriever = None
            log.warning(f"Agent: RAG Retriever unavailable: {e}")

        log.info("Agent v3.0 initialised. Brain and ToolRegistry ready.")

    # ── Public ─────────────────────────────────────────────────────────────────

    def common_phrases(self) -> list[str]:
        """
        Stock lines Mantra says over and over. main.py hands these to
        TextToSpeech.prewarm() so they are cached and play with no delay.
        """
        return [
            *_SESSION_OPENERS,
            *_BYE,
            *_GREETINGS,
            *_HOW_ARE_YOU,
            *_THANKS,
            "Sorry, I didn't catch that. Say it again?",
            "Okay, cancelled.",
        ]

    def speak(self, text: str) -> None:
        """Speak a response aloud and log it."""
        self.tts.speak(text)

    def handle_command(self, text: str) -> bool:
        """
        Route a text command to the right handler.

        Priority:
          1. Exit check              → end the session
          2. Built-in replies        → greetings, time, date, jokes (fast, offline)
          3. RAG document search     → answer from local knowledge base
          4. Tools                   → apps, system, browser, files, memory, etc.
          5. Brain (LLM)             → Gemini or local LLM for anything else

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

        # ── 3. RAG document search ─────────────────────────────────────────────
        rag_response = self._try_rag(text)
        if rag_response:
            self.speak(rag_response)
            return True

        # ── 4. Tools ──────────────────────────────────────────────────────────
        tool_response = self.tools.execute(text, confirm_callback=self._voice_confirm)
        if tool_response:
            self.speak(tool_response)
            return True

        # ── 5. Brain (LLM) — last resort ──────────────────────────────────────
        log.info("Agent: No tool matched. Asking Brain (LLM)...")
        llm_response = self.brain.think(text)
        self.speak(llm_response)
        return True

    def run_session(self) -> None:
        """
        Active voice session: listen for commands until the user says goodbye.
        Called by main.py after the wake word is detected.

        The microphone is opened once for the whole session (instead of per
        command), which removes ~0.3 s of device setup from every turn.
        """
        # Reset LLM conversation memory at the start of each new session
        self.brain.reset_history()

        # Hold the mic open for the whole session – much snappier per command.
        self.stt.open_stream()

        try:
            self.speak(random.choice(_SESSION_OPENERS))
            session_active = True

            while session_active:
                log.info("Agent: Awaiting command...")
                text = self.stt.listen_and_recognize()

                if text is None:
                    # Nothing heard — give one more chance
                    self.speak("Sorry, I didn't catch that. Say it again?")
                    text = self.stt.listen_and_recognize()
                    if text is None:
                        self.speak(
                            "Okay, I'll go back to sleep. "
                            f"Just say '{config.WAKE_WORD.title()}' when you need me."
                        )
                        break

                session_active = self.handle_command(text)
        finally:
            # Always release the mic so the wake word detector can re-arm.
            self.stt.close_stream()

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

        # Projects — scan the user's project folder and list them
        if contains_any(t, ["how many project", "my project", "list my project",
                             "list project", "show my project", "show project",
                             "current project", "working on",
                             "what project", "which project"]):
            return self._list_projects()

        return None  # no built-in matched

    # ── Project listing ────────────────────────────────────────────────────────

    _PROJECTS_DIR = Path(r"D:\R09\My Project")

    def _list_projects(self) -> str:
        """
        Scan the user's project folder and return a spoken summary
        of all project directories found.
        """
        try:
            if not self._PROJECTS_DIR.exists():
                return f"I couldn't find your projects folder at {self._PROJECTS_DIR}."

            projects = sorted(
                d.name for d in self._PROJECTS_DIR.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            )

            if not projects:
                return "Your projects folder is empty. No projects found."

            count = len(projects)
            names = ", ".join(projects)
            return (
                f"You have {count} project{'s' if count != 1 else ''} "
                f"in your projects folder. "
                f"{'They are' if count > 1 else 'It is'}: {names}."
            )
        except PermissionError:
            return "I don't have permission to access your projects folder."
        except Exception as e:
            log.warning(f"Project listing failed: {e}")
            return "Sorry, I had trouble scanning your projects folder."
    # ── RAG lookup ─────────────────────────────────────────────────────────────

    # Speech-to-text often splits compound names (e.g. "CropX" → "Crop X").
    # This map lets us normalise those variants before querying the vector DB.
    _SPEECH_ALIASES: dict[str, str] = {
        "crop x":  "CropX",
        "cropx":   "CropX",
        # Add more aliases here as needed, e.g.:
        # "dev ops": "DevOps",
    }

    def _try_rag(self, text: str, distance_threshold: float = 0.85) -> str | None:
        """
        Check the RAG knowledge base for relevant documents.

        Returns a contextual LLM answer when the vector database contains
        matching content, or None so the caller continues to the next
        routing step (tools → brain).

        Args:
            text:               The user's original spoken/typed input.
            distance_threshold: Maximum vector distance to consider relevant.
        """
        if self.retriever is None:
            return None

        try:
            if not self.retriever.has_documents():
                return None

            # Normalise speech variations before querying
            query = text
            t_lower = normalize(text)
            for alias, canonical in self._SPEECH_ALIASES.items():
                if alias in t_lower:
                    query = text.replace(
                        # Find the alias in original text (case-insensitive)
                        next((
                            text[i:i+len(alias)]
                            for i in range(len(text) - len(alias) + 1)
                            if text[i:i+len(alias)].lower() == alias
                        ), alias),
                        canonical
                    )
                    log.debug(f"RAG: Normalised query '{text}' → '{query}'")
                    break

            # Search the vector store
            results = self.retriever.retrieve(query=query, n_results=3)
            if not results:
                return None

            # Only proceed if the best result is relevant enough
            best_distance = results[0].get("distance", 999)
            if best_distance > distance_threshold:
                log.info(
                    f"Agent RAG: Best distance {best_distance:.4f} exceeds "
                    f"threshold {distance_threshold}. Skipping RAG."
                )
                return None

            # Build context from relevant results for the Brain
            context_parts = []
            for index, result in enumerate(results, start=1):
                if result.get("distance", 999) <= distance_threshold:
                    context_parts.append(
                        f"[Source {index}: "
                        f"{result['source']} | "
                        f"Chunk {result['chunk_number']}]\n"
                        f"{result['text']}"
                    )

            context = "\n\n---\n\n".join(context_parts)

            log.info(
                f"Agent RAG: Found {len(context_parts)} relevant doc(s) "
                f"(best distance: {best_distance:.4f}). Using RAG answer."
            )
            return self.brain.think_with_rag(query, context)

        except Exception as e:
            log.warning(f"Agent RAG lookup failed: {e}")
            return None

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
