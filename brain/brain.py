"""
brain/brain.py – Mantra AI v3.0
────────────────────────────────
The LLM Router — Mantra's decision-maker for which AI to talk to.

What it does:
  - Tries the Gemini API first (fast, smart, needs internet)
  - If Gemini fails or is unavailable → falls back to the Local LLM (Ollama)
  - If both fail → returns a polite fallback message
  - Manages conversation history across both LLMs

The "brain" of Mantra. Everything asking an AI question goes through here.

Where it fits:
  agent/agent.py  →  brain/brain.py  →  brain/llm_api.py   (online)
                                     →  brain/local_llm.py (offline)

Does NOT know about:
  - Voice, windows, tools, files
  - It is ONLY about routing questions to the right AI
"""

import sys
from pathlib import Path

# Add project root to sys.path if running this file directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config
from utils import log
from brain.llm_api     import LLMApi      # online  Gemini API
from brain.openai_llm  import OpenAILLM   # online  OpenAI API
from brain.local_llm   import LocalLLM    # offline local LLM (Ollama)


class Brain:
    """
    Mantra's LLM router.

    Tries API first → falls back to local LLM → falls back to a default message.

    Usage:
        brain = Brain()
        reply = brain.think("What is the speed of light?")
        print(reply)
    """

    # Message returned if BOTH the API LLM and local LLM fail
    FALLBACK_MESSAGE = (
        "I'm sorry, I can't connect to my AI brain right now. "
        "Please check your internet connection or make sure Ollama is running."
    )

    def __init__(self):
        # Create all LLM clients
        self._api_llm    = LLMApi()      # Gemini (online)
        self._openai_llm = OpenAILLM()   # OpenAI (online)
        self._local_llm  = LocalLLM()    # Ollama  (offline)

        # Which provider to prefer: 'gemini', 'openai', or 'auto'
        self._provider = getattr(config, "AI_PROVIDER", "auto").lower()

        log.info(
            f"Brain initialised. Provider: '{self._provider}' | "
            f"Gemini available: {self._api_llm.is_available()} | "
            f"OpenAI available: {self._openai_llm.is_available()} | "
            f"Local LLM available: {self._local_llm.is_available()}"
        )



    # ── Public ─────────────────────────────────────────────────────────────────

    def think(self, user_text: str) -> str:
        """
        Send a question/prompt to the best available LLM and return the reply.

        Routing is controlled by config.AI_PROVIDER:
          - 'gemini'  → Gemini → Ollama → fallback
          - 'openai'  → OpenAI → Ollama → fallback
          - 'auto'    → Gemini → OpenAI → Ollama → fallback  (default)

        Args:
            user_text: The user's question or command text.

        Returns:
            A plain text response string. Never returns None.
        """
        log.info(f"Brain.think called with: '{user_text[:60]}...' " if len(user_text) > 60 else f"Brain.think: '{user_text}'")

        # Build the ordered list of LLMs to try based on provider setting
        if self._provider == "gemini":
            cloud_order = [(self._api_llm, "Gemini API")]
        elif self._provider == "openai":
            cloud_order = [(self._openai_llm, "OpenAI API")]
        else:  # "auto" — try all
            cloud_order = [
                (self._api_llm, "Gemini API"),
                (self._openai_llm, "OpenAI API"),
            ]

        # ── Try cloud LLMs in order ────────────────────────────────────────
        for llm, name in cloud_order:
            if llm.is_available():
                log.debug(f"Brain: Trying {name}...")
                reply = llm.ask(user_text)
                if reply:
                    log.info(f"Brain: Used {name} successfully.")
                    return reply
                log.warning(f"Brain: {name} returned no reply.")
            else:
                log.info(f"Brain: {name} not available (no key).")

        # ── Fall back to Local LLM (Ollama) ────────────────────────────────
        if self._local_llm.is_available():
            log.debug(f"Brain: Trying Local LLM ({self._local_llm.get_model_name()})...")
            reply = self._local_llm.ask(user_text)
            if reply:
                log.info(f"Brain: Used Local LLM ({self._local_llm.get_model_name()}) as fallback.")
                return reply
            log.warning("Brain: Local LLM also returned no reply.")
        else:
            log.info("Brain: Local LLM not available (Ollama not running).")

        # ── All failed ─────────────────────────────────────────────────────
        log.error("Brain: All LLM providers failed. Using fallback message.")
        return self.FALLBACK_MESSAGE

    def reset_history(self) -> None:
        """
        Clear conversation memory in ALL LLMs.
        Call this at the start and end of every voice session.
        """
        self._api_llm.reset_history()
        self._openai_llm.reset_history()
        self._local_llm.reset_history()
        log.debug("Brain: All conversation history cleared.")

    def status(self) -> dict:
        """
        Returns a dict showing which LLMs are currently available.
        Useful for debugging or a "Mantra, what's your status?" command.
        """
        return {
            "ai_provider":          self._provider,
            "gemini_available":     self._api_llm.is_available(),
            "openai_available":     self._openai_llm.is_available(),
            "openai_model":         self._openai_llm.get_model_name(),
            "local_llm_available":  self._local_llm.is_available(),
            "local_llm_model":      self._local_llm.get_model_name(),
        }
        # ── RAG ───────────────────────────────────────────────────────────────────

    def think_with_rag(self, user_text: str, context: str) -> str:
        """
        Answer a question using pre-retrieved RAG context.

        The agent retrieves relevant document chunks and passes
        the formatted context here. Brain just builds the augmented
        prompt and routes it through the normal LLM pipeline.

        Args:
            user_text: User's original question.
            context:   Pre-built context string from Agent's retriever.

        Returns:
            A response from Gemini, Ollama, or the fallback system.
        """
        if not user_text or not user_text.strip():
            return self.think(user_text)

        rag_prompt = f"""
You are Mantra, a helpful personal AI assistant.

Use the DOCUMENT CONTEXT below to answer the user's question.

Rules:
1. Answer primarily using the provided document context.
2. Do not invent information that is not supported by the context.
3. If the context does not contain enough information, clearly say so.
4. Keep the answer natural, clear, and suitable for a voice assistant.
5. Do not mention "vector database", "embedding", or "RAG" unless the user specifically asks about them.

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{user_text}

ANSWER:
"""

        log.info("RAG context provided. Sending contextual prompt to LLM.")
        return self.think(rag_prompt)

# ── Self-test ─────────────────────────────────────────────────────────────────
# To test:  python brain/brain.py
if __name__ == "__main__":
    print("Testing brain/brain.py (the LLM router)...")
    print("=" * 50)

    brain = Brain()

    # Show which LLMs are available
    s = brain.status()
    print(f"Gemini API available : {s['gemini_available']}")
    print(f"OpenAI API available : {s['openai_available']}")
    print(f"Local LLM available  : {s['local_llm_available']}")
    if s["local_llm_available"]:
        print(f"Local LLM model      : {s['local_llm_model']}")
    print()

    # Test a question – brain will automatically pick the best LLM
    question = "In one sentence, what is artificial intelligence?"
    print(f"Asking: '{question}'")
    reply = brain.think(question)
    print(f"Reply : {reply}")
    print()

    # Test follow-up (tests conversation memory)
    followup = "Give me one example of that."
    print(f"Follow-up: '{followup}'")
    reply2 = brain.think(followup)
    print(f"Reply    : {reply2}")
    print()

    # Reset history
    brain.reset_history()
    print("History cleared.")
    print()

    print("=" * 50)
    print("brain/brain.py is working correctly!")