"""
brain/local_llm.py – Mantra AI v3.0
────────────────────────────────────
Communicates with a locally running LLM via Ollama.

What it does:
  - Sends the user's text to a local AI model running on YOUR computer
  - Works completely OFFLINE – no internet needed
  - Uses Ollama (free, open-source local LLM runner) at http://localhost:11434
  - If Ollama is not installed/running, it returns None gracefully

Where it fits:
  brain/local_llm.py  ←  called by brain/brain.py (as the fallback LLM)
  brain/brain.py      ←  tries API first, then falls back to this

How to enable it (one-time setup):
  1. Install Ollama: https://ollama.com/download
  2. Open a terminal and run: ollama pull llama3
  3. Ollama runs automatically in the background after install.

Does NOT know about:
  - Voice, windows, files, or any tools
  - Whether the user spoke or typed
  - It is ONLY about talking to a local AI model
"""

import sys
from pathlib import Path

# Add project root to sys.path if running this file directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import requests   # sends HTTP requests to the local Ollama server

import config     # reads LOCAL_LLM_URL and LOCAL_LLM_MODEL from config
from utils import log


class LocalLLM:
    """
    Talks to a locally running LLM using Ollama's HTTP API.

    Ollama listens on http://localhost:11434 by default.
    It can run models like: llama3, mistral, phi3, gemma2, etc.

    Usage:
        llm = LocalLLM()
        if llm.is_available():
            reply = llm.ask("What is the capital of France?")
            print(reply)
    """

    # Ollama's chat endpoint – we use /api/chat for multi-turn conversations
    OLLAMA_CHAT_URL = "{base_url}/api/chat"

    # Ollama's version endpoint – used to check if Ollama is running
    OLLAMA_HEALTH_URL = "{base_url}/api/version"

    def __init__(self):
        # Read the Ollama base URL from config (default: http://localhost:11434)
        # getattr with default makes this safe even if config doesn't have this key yet
        self._base_url = getattr(config, "LOCAL_LLM_URL", "http://localhost:11434")

        # Read which model to use (default: llama3)
        self._model = getattr(config, "LOCAL_LLM_MODEL", "llama3")

        # Conversation history (same format as OpenAI/Ollama chat API)
        # Each item: {"role": "user"/"assistant", "content": "message text"}
        self._history: list[dict] = []

        log.info(f"LocalLLM ready. Model: '{self._model}' at {self._base_url}")

    # ── Public ─────────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """
        Check if Ollama is running on this computer.

        Returns:
            True  → Ollama is running and we can use the local LLM
            False → Ollama is not installed or not running
        """
        try:
            url = self.OLLAMA_HEALTH_URL.format(base_url=self._base_url)
            # Short timeout – if Ollama doesn't respond in 2 seconds, it's not running
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except Exception:
            # Any error (connection refused, timeout, etc.) → Ollama not available
            return False

    def ask(self, user_text: str) -> str | None:
        """
        Send a message to the local LLM and get a reply.

        Args:
            user_text: What the user said or typed.

        Returns:
            The local LLM's reply as a plain text string.
            Returns None if Ollama is not running or an error occurs.
        """
        if not self.is_available():
            log.warning("LocalLLM: Ollama is not running. Cannot use local LLM.")
            return None

        # Add the user message to the conversation history
        self._history.append({
            "role": "user",
            "content": user_text
        })

        # Build the request to send to Ollama
        # We include the system prompt so the local model knows it is Mantra
        payload = {
            "model": self._model,   # e.g. "llama3" or "mistral"
            "messages": [
                # First message is always the system prompt (Mantra's personality)
                {
                    "role": "system",
                    "content": getattr(
                        config,
                        "PERSONA_SYSTEM_PROMPT",
                        f"You are Mantra, a helpful voice assistant. Keep replies short and clear."
                    )
                },
                # Then all conversation history
                *self._history
            ],
            "stream": False,        # False = wait for the full reply (not streamed)
            "options": {
                "temperature": 0.7, # same creativity level as our Gemini calls
                "num_predict": 150, # limit output length (TTS-friendly)
            }
        }

        try:
            url = self.OLLAMA_CHAT_URL.format(base_url=self._base_url)
            # Longer timeout for local models – they can be slower than cloud APIs
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()

            # Extract the reply text from Ollama's response
            # Ollama returns: {"message": {"role": "assistant", "content": "reply here"}}
            reply = response.json()["message"]["content"].strip()

            # Save the model's reply to history for next turn
            self._history.append({
                "role": "assistant",
                "content": reply
            })

            preview = reply[:80] + "..." if len(reply) > 80 else reply
            log.info(f"LocalLLM ({self._model}) reply: '{preview}'")
            return reply

        except requests.ConnectionError:
            log.warning("LocalLLM: Could not connect to Ollama (connection refused).")
            # Remove the failed user message so history stays clean
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None

        except requests.Timeout:
            log.warning("LocalLLM: Ollama took too long to reply (timeout).")
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None

        except Exception as e:
            log.error(f"LocalLLM unexpected error: {e}")
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None

    def reset_history(self) -> None:
        """
        Clear the conversation memory.
        Call at the start/end of each voice session.
        """
        self._history.clear()
        log.debug("LocalLLM: Conversation history cleared.")

    def get_model_name(self) -> str:
        """Return the name of the local model being used (e.g. 'llama3')."""
        return self._model


# ── Self-test ────────────────────────────────────────────────────────────────
# To test:  python brain/local_llm.py
# Make sure Ollama is running first: https://ollama.com/download
if __name__ == "__main__":
    print("Testing brain/local_llm.py...")
    print("=" * 50)

    llm = LocalLLM()

    print(f"Checking if Ollama is running at {llm._base_url}...")
    if not llm.is_available():
        print()
        print("Ollama is NOT running (or not installed).")
        print()
        print("To install Ollama:")
        print("  1. Go to https://ollama.com/download")
        print("  2. Install for Windows")
        print("  3. Open a terminal and run: ollama pull llama3")
        print()
        print("This is OPTIONAL. Mantra works fine with just the Gemini API.")
        print("Local LLM is only used as a FALLBACK when there is no internet.")
    else:
        print(f"Ollama is running! Using model: {llm.get_model_name()}")
        print()
        print(f"Test: Asking '{llm.get_model_name()}' to say hello...")
        reply = llm.ask("Say hello in exactly one sentence.")
        print(f"Local LLM said: {reply}")
        print()
        print("=" * 50)
        print("brain/local_llm.py is working correctly!")
