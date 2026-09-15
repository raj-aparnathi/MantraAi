"""
brain/openai_llm.py – Mantra AI v3.1
──────────────────────────────────────
Communicates with the OpenAI API (ChatGPT models).

What it does:
  - Sends the user's text to OpenAI's chat completions endpoint
  - Keeps a conversation history so the model remembers earlier messages
  - Returns the model's reply as plain text
  - Handles errors gracefully (network failure, bad API key, etc.)

Where it fits:
  brain/openai_llm.py  ←  called by brain/brain.py
  brain/brain.py       ←  called by agent/agent.py

Does NOT know about:
  - Voice, windows, files, or any tools
  - Whether the user spoke or typed
  - It is ONLY about talking to OpenAI

Note:
  Uses raw HTTP requests (same as llm_api.py for Gemini).
  No 'openai' SDK dependency needed — keeps the project lightweight.
"""

import sys
from pathlib import Path

# Add project root to sys.path if running this file directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import requests

import config
from utils import log


class OpenAILLM:
    """
    Handles all communication with the OpenAI Chat Completions API.

    Usage:
        api = OpenAILLM()
        reply = api.ask("What is the capital of France?")
        print(reply)  # → "The capital of France is Paris."
    """

    # OpenAI Chat Completions endpoint
    OPENAI_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self):
        # Conversation history (OpenAI chat format)
        # Each item: {"role": "user"/"assistant", "content": "message text"}
        self._history: list[dict] = []

        # Read the model from config (default: gpt-4o-mini)
        self._model = getattr(config, "OPENAI_MODEL", "gpt-4o-mini")

        log.info(f"OpenAILLM ready. Model: {self._model}")

    # ── Public ─────────────────────────────────────────────────────────────────

    def ask(self, user_text: str) -> str | None:
        """
        Send a message to OpenAI and get a reply.

        Args:
            user_text: What the user said or typed.

        Returns:
            OpenAI's reply as a plain text string.
            Returns None if there's no API key or a network error occurs.
        """
        if not self.is_available():
            log.warning("OpenAILLM: OPENAI_API_KEY not set. Skipping API call.")
            return None

        # Add the user's message to conversation history
        self._history.append({
            "role": "user",
            "content": user_text
        })

        # Keep history within the limit
        max_msgs = config.PERSONA_MAX_HISTORY * 2
        if len(self._history) > max_msgs:
            self._history = self._history[-max_msgs:]

        # Build the request payload
        payload = {
            "model": self._model,
            "messages": [
                # System prompt (Mantra's personality)
                {
                    "role": "system",
                    "content": config.PERSONA_SYSTEM_PROMPT
                },
                # Conversation history
                *self._history
            ],
            "temperature": 0.7,
            "max_tokens": 150,
            "top_p": 0.9,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        }

        try:
            response = requests.post(
                self.OPENAI_URL,
                json=payload,
                headers=headers,
                timeout=12
            )
            response.raise_for_status()

            # Extract the reply from OpenAI's response
            reply = (
                response.json()
                ["choices"][0]
                ["message"]["content"]
                .strip()
            )

            # Save the reply to history for context
            self._history.append({
                "role": "assistant",
                "content": reply
            })

            preview = reply[:80] + "..." if len(reply) > 80 else reply
            log.info(f"OpenAI ({self._model}) reply: '{preview}'")
            return reply

        except requests.HTTPError as e:
            log.error(f"OpenAI HTTP error {response.status_code}: {e}")
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None

        except requests.ConnectionError:
            log.warning("OpenAI API: No internet connection.")
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None

        except requests.Timeout:
            log.warning("OpenAI API: Request timed out.")
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None

        except Exception as e:
            log.error(f"OpenAI API unexpected error: {e}")
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None

    def reset_history(self) -> None:
        """
        Clear the conversation memory.
        Call this at the start or end of each voice session.
        """
        self._history.clear()
        log.debug("OpenAILLM: Conversation history cleared.")

    def is_available(self) -> bool:
        """
        Quick check: do we have an OpenAI API key configured?
        Returns True if we can try to use the API.
        """
        return bool(getattr(config, "OPENAI_API_KEY", ""))

    def get_model_name(self) -> str:
        """Return the name of the OpenAI model being used."""
        return self._model


# ── Self-test (run this file directly to test it) ─────────────────────────────
# To test:  python brain/openai_llm.py
if __name__ == "__main__":
    print("Testing brain/openai_llm.py...")
    print("=" * 50)

    api = OpenAILLM()

    if not api.is_available():
        print("OPENAI_API_KEY is not set.")
        print("Add your OpenAI API key to .env or data/config.json under 'api_keys.openai'")
        print()
        print("This is OPTIONAL. Mantra works fine with just the Gemini API.")
        print("OpenAI is an alternative AI provider you can switch to.")
    else:
        print(f"Using model: {api.get_model_name()}")
        print()

        # Test 1: Simple question
        print("Test 1: Asking 'What is 2 + 2?'")
        reply = api.ask("What is 2 + 2?")
        print(f"OpenAI said: {reply}")
        print()

        # Test 2: Follow-up (tests conversation memory)
        print("Test 2: Follow-up 'And multiply that by 3?'")
        reply = api.ask("And multiply that by 3?")
        print(f"OpenAI said: {reply}")
        print()

        # Test 3: Reset history
        api.reset_history()
        print("Test 3: History cleared. Session memory reset.")
        print()

        print("=" * 50)
        print("brain/openai_llm.py is working correctly!")
