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
from brain.llm_api   import LLMApi    # online  Gemini API
from brain.local_llm import LocalLLM  # offline local LLM (Ollama)

# RAG document retriever
from rag.retriever import Retriever
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
        # Create the two LLM clients
        self._api_llm   = LLMApi()    # Gemini (online)
        self._local_llm = LocalLLM()  # Ollama  (offline)

        log.info(
            f"Brain initialised. "
            f"API LLM available: {self._api_llm.is_available()} | "
            f"Local LLM available: {self._local_llm.is_available()}"
        )
                # ── RAG Retriever ────────────────────────────────────────────────────
        # Connect Mantra's brain to the local document knowledge base.
        # If RAG fails for any reason, Mantra should still work normally.
        try:
            self._retriever = Retriever()

            log.info(
                f"RAG initialised. "
                f"Documents available: {self._retriever.has_documents()} | "
                f"Chunks: {self._retriever.document_count()}"
            )

        except Exception as e:
            self._retriever = None

            log.warning(
                f"RAG could not be initialised. "
                f"Mantra will continue without RAG. Error: {e}"
            )

    # ── Public ─────────────────────────────────────────────────────────────────

    def think(self, user_text: str) -> str:
        """
        Send a question/prompt to the best available LLM and return the reply.

        Priority order:
          1. Gemini API  (if API key is set and internet works)
          2. Local LLM   (if Ollama is running)
          3. Fallback message

        Args:
            user_text: The user's question or command text.

        Returns:
            A plain text response string. Never returns None.
        """
        log.info(f"Brain.think called with: '{user_text[:60]}...' " if len(user_text) > 60 else f"Brain.think: '{user_text}'")

        # ── Step 1: Try the Gemini API ─────────────────────────────────────────
        if self._api_llm.is_available():
            log.debug("Brain: Trying Gemini API...")
            reply = self._api_llm.ask(user_text)
            if reply:
                log.info("Brain: Used Gemini API successfully.")
                return reply
            log.warning("Brain: Gemini API returned no reply. Trying local LLM...")
        else:
            log.info("Brain: Gemini API not available (no key). Trying local LLM...")

        # ── Step 2: Fall back to the Local LLM (Ollama) ───────────────────────
        if self._local_llm.is_available():
            log.debug(f"Brain: Trying Local LLM ({self._local_llm.get_model_name()})...")
            reply = self._local_llm.ask(user_text)
            if reply:
                log.info(f"Brain: Used Local LLM ({self._local_llm.get_model_name()}) as fallback.")
                return reply
            log.warning("Brain: Local LLM also returned no reply.")
        else:
            log.info("Brain: Local LLM not available (Ollama not running).")

        # ── Step 3: Both failed – return a safe fallback message ──────────────
        log.error("Brain: Both API and Local LLM failed. Using fallback message.")
        return self.FALLBACK_MESSAGE

    def reset_history(self) -> None:
        """
        Clear conversation memory in BOTH LLMs.
        Call this at the start and end of every voice session.
        """
        self._api_llm.reset_history()
        self._local_llm.reset_history()
        log.debug("Brain: All conversation history cleared.")

    def status(self) -> dict:
        """
        Returns a dict showing which LLMs are currently available.
        Useful for debugging or a "Mantra, what's your status?" command.

        Returns:
            {
                "api_llm_available":   True/False,
                "local_llm_available": True/False,
                "local_llm_model":     "llama3" / "mistral" / ...
            }
        """
        return {
            "api_llm_available":   self._api_llm.is_available(),
            "local_llm_available": self._local_llm.is_available(),
            "local_llm_model":     self._local_llm.get_model_name(),
        }
        # ── RAG ───────────────────────────────────────────────────────────────────

    def think_with_rag(
        self,
        user_text: str,
        n_results: int = 3,
        distance_threshold: float = 0.85
    ) -> str:
        """
        Answer a question using Mantra's document knowledge base when
        relevant information is found.

        Flow:
            User Question
                ↓
            Search Vector Database
                ↓
            Relevant document found?
                ├── YES → Send Context + Question to LLM
                └── NO  → Use normal Brain.think()

        Args:
            user_text:
                User's original question.

            n_results:
                Maximum number of document chunks to retrieve.

            distance_threshold:
                Maximum allowed vector distance for a result to be
                considered relevant. Lower distance = more relevant.

        Returns:
            A response from Gemini, Ollama, or the fallback system.
        """

        # Empty input → use normal brain behaviour
        if not user_text or not user_text.strip():
            return self.think(user_text)

        # If RAG failed during initialisation, continue normally
        if self._retriever is None:
            log.debug(
                "RAG unavailable. Using normal LLM pipeline."
            )

            return self.think(user_text)

        try:

            # Check whether any documents exist
            if not self._retriever.has_documents():

                log.debug(
                    "RAG database is empty. Using normal LLM pipeline."
                )

                return self.think(user_text)

            # Search for relevant chunks
            results = self._retriever.retrieve(
                query=user_text,
                n_results=n_results
            )

            # No results → normal LLM
            if not results:

                log.info(
                    "RAG found no relevant results. "
                    "Using normal LLM."
                )

                return self.think(user_text)

            # Filter results based on vector distance.
            # Lower distance means the document chunk is more relevant.
            relevant_results = [
                result
                for result in results
                if result.get("distance", 999)
                <= distance_threshold
            ]

            # If nothing is relevant enough, don't force RAG context.
            # Mantra will answer normally using Gemini/Ollama.
            if not relevant_results:

                best_distance = results[0].get(
                    "distance",
                    None
                )

                log.info(
                    f"RAG results not relevant enough. "
                    f"Best distance: {best_distance}. "
                    f"Using normal LLM."
                )

                return self.think(user_text)

            # Build context manually from only relevant chunks
            context_parts = []

            for index, result in enumerate(
                relevant_results,
                start=1
            ):

                context_parts.append(
                    f"[Source {index}: "
                    f"{result['source']} | "
                    f"Chunk {result['chunk_number']}]\n"
                    f"{result['text']}"
                )

            context = "\n\n---\n\n".join(
                context_parts
            )

            log.info(
                f"RAG found {len(relevant_results)} "
                f"relevant document chunk(s)."
            )

            # Create an augmented prompt.
            # The LLM gets the user's question plus information retrieved
            # from Mantra's local document knowledge base.
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

            log.info(
                "RAG context found. Sending contextual prompt "
                "to LLM."
            )

            # Reuse the existing Gemini → Ollama → fallback pipeline.
            # This means we do NOT duplicate or change existing LLM logic.
            return self.think(rag_prompt)

        except Exception as e:

            # RAG must never break Mantra.
            # If anything goes wrong, simply use the normal brain.
            log.error(
                f"RAG processing failed: {e}. "
                f"Falling back to normal LLM.",
                exc_info=True
            )

            return self.think(user_text)


    def rag_status(self) -> dict:
        """
        Return the current status of Mantra's RAG system.

        Useful for debugging or future commands such as:
        'Mantra, how many documents do you know?'
        """

        if self._retriever is None:

            return {
                "rag_available": False,
                "has_documents": False,
                "document_count": 0
            }

        try:

            return {
                "rag_available": True,
                "has_documents": (
                    self._retriever.has_documents()
                ),
                "document_count": (
                    self._retriever.document_count()
                )
            }

        except Exception as e:

            log.warning(
                f"Could not get RAG status: {e}"
            )

            return {
                "rag_available": False,
                "has_documents": False,
                "document_count": 0
            }

# ── Self-test ─────────────────────────────────────────────────────────────────
# To test:  python brain/brain.py
if __name__ == "__main__":
    print("Testing brain/brain.py (the LLM router)...")
    print("=" * 50)

    brain = Brain()

    # Show which LLMs are available
    s = brain.status()
    print(f"Gemini API available : {s['api_llm_available']}")
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
    print()
    print("=" * 50)
    print("Testing RAG Brain Integration...")
    print()

    rag_question = "What is CropX?"

    print(f"Question: {rag_question}")

    rag_reply = brain.think_with_rag(
        rag_question
    )

    print(f"\nRAG Reply:\n{rag_reply}")

    print()
    print("RAG Status:")

    print(
        brain.rag_status()
    )