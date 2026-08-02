"""
conversation.py – Mantra AI v2.0
Handles greetings, small talk, identity Q&A, date/time, and
Gemini API with full Hindi/Hinglish persona + session memory.

v2.0 upgrades:
  - All built-in responses in Hinglish (Hindi + English mix)
  - Session memory: keeps last N conversation turns for Gemini context
  - Gemini API uses the full system prompt from config.json → persona
  - Gemini API uses multi-turn conversation history (not single-shot)
  - reset_history() called at session end by assistant.py
"""

import random
import requests

import config
from utils import log, get_time, get_date, get_greeting_period, normalize, contains_any


# ── Hinglish Response Banks ────────────────────────────────────────────────────

_GREETINGS = [
    "Haan ji! Batao, main aapki kya madad kar sakta hoon?",
    "Namaste! Kya chal raha hai, main help karne ke liye ready hoon.",
    "Hello! Kya kaam hai aapka? Batao, main hoon na.",
]

_GOOD_MORNING = [
    "Good morning! Subah ki nayi shuruat ho rahi hai, kya plan hai aaj ka?",
    "Suprabhat! Ummid hai aapki subah achhi rahi ho. Kya kaam hai?",
]

_GOOD_AFTERNOON = [
    "Good afternoon! Din kaisa ja raha hai? Kuch kaam hai?",
    "Namaskar! Dopahar mein bhi main hoon aapke saath. Batao kya chahiye.",
]

_GOOD_EVENING = [
    "Good evening! Aaj ka din kaisa raha? Kuch chahiye?",
    "Shaam ho gayi, lekin main abhi bhi ready hoon help karne ke liye.",
]

_HOW_ARE_YOU = [
    "Bilkul theek hoon, shukriya poochne ke liye! Aap sunao, kaise hain?",
    "Main toh sab badhiya hoon, aur aapki madad ke liye poori tarah taiyaar hoon!",
    "Ekdum first class! Bolo, aaj kya karna hai?",
]

_IDENTITY = [
    f"Main hoon {config.ASSISTANT_NAME}, aapka personal AI assistant, version {config.VERSION}. "
    "Aapki baat sunna, tasks complete karna, aur questions ka jawab dena, yahi mera kaam hai.",
    f"Mera naam {config.ASSISTANT_NAME} hai. Main ek voice-controlled AI hoon, "
    "jo aapke Windows PC ko control kar sakta hoon aur aapke saare sawalon ke jawab de sakta hoon.",
]

_THANKS = [
    "Koi baat nahi! Aur kuch chahiye toh batao.",
    "Khushi hui madad karke! Aur kaam ho toh bolo.",
    "Yeh toh mera farz hai. Kuch aur?",
]

_JOKES = [
    "Ek programmer ne apne dost se kaha, main loop mein phans gaya hoon. Dost ne pucha, kab se? "
    "Programmer bola, pata nahi, loop mein hoon!",
    "Bug kya hota hai? Woh feature jo abhi document nahi hua.",
    "Maine computer se kaha, mujhe break chahiye. Ab woh baar baar Kit-Kat ads bhejta hai.",
    "Python seekhna easy hai, sirf indentation se darr lagta hai.",
]

_CAPABILITIES = (
    f"Main hoon {config.ASSISTANT_NAME} version {config.VERSION}, aapka Windows desktop assistant. "
    "Main koi bhi app open, close, minimize ya maximize kar sakta hoon. "
    "Files dhundhna, banana, rename, copy ya delete karna mujhe pata hai. "
    "Volume aur brightness control, screenshot, screen recording, aur clipboard bhi handle karta hoon. "
    "Browser mein websites open karna, Google aur YouTube search, aur bookmarks bhi. "
    "Weather, news, Wikipedia, notes, aur koi bhi sawaal, sab ke liye ready hoon. "
    "Bas boliye!"
)

_BYE = [
    f"Theek hai, phir milenge! Apna khayal rakhna.",
    f"Alvida! Jab bhi zaroorat ho, 'Hello Mantra' bolna.",
    f"Okay! Shubh {get_greeting_period()} ho. Take care!",
]


# ── Conversation Handler ───────────────────────────────────────────────────────

class Conversation:
    """
    Handles all conversational intent with Hinglish personality.

    Session memory:
        _history stores the last PERSONA_MAX_HISTORY turns as Gemini
        multi-turn messages. Call reset_history() at session start/end.
    """

    def __init__(self):
        # Multi-turn conversation history for Gemini API
        self._history: list[dict] = []
        log.info(
            f"Conversation module ready. "
            f"Language: {config.PERSONA_LANGUAGE} | "
            f"Max history: {config.PERSONA_MAX_HISTORY} turns"
        )

    # ── Public ─────────────────────────────────────────────────────────────────

    def reset_history(self) -> None:
        """Clear session memory. Call at the start/end of each wake-word session."""
        self._history.clear()
        log.debug("Conversation history cleared.")

    def handle(self, text: str) -> str | None:
        """
        Try to respond to conversational queries.
        Checks built-in Hinglish responses first; falls back to Gemini.
        Returns a response string, or None if intent not recognised.
        """
        t = normalize(text)

        # ── Greetings ──────────────────────────────────────────────────────────
        if contains_any(t, ["hello", "hi ", "hey ", "haan", "namaste", "namaskar"]):
            return random.choice(_GREETINGS)

        if "good morning" in t or "subah" in t or "suprabhat" in t:
            return random.choice(_GOOD_MORNING)

        if "good afternoon" in t or "dopahar" in t:
            return random.choice(_GOOD_AFTERNOON)

        if "good evening" in t or "good night" in t or "shaam" in t:
            return random.choice(_GOOD_EVENING)

        # ── How are you ────────────────────────────────────────────────────────
        if contains_any(t, ["how are you", "how r u", "kaisa hai", "kaisi ho",
                             "kaise ho", "kya haal hai", "sab theek"]):
            return random.choice(_HOW_ARE_YOU)

        # ── Identity ───────────────────────────────────────────────────────────
        if contains_any(t, ["who are you", "your name", "what are you",
                             "introduce yourself", "kaun ho", "tera naam",
                             "apna parichay", "tum kaun"]):
            return random.choice(_IDENTITY)

        # ── Thanks ─────────────────────────────────────────────────────────────
        if contains_any(t, ["thank you", "thanks", "thank u",
                             "shukriya", "dhanyawaad", "bahut acha"]):
            return random.choice(_THANKS)

        # ── Time ───────────────────────────────────────────────────────────────
        if contains_any(t, ["what time", "current time", "time is it",
                             "kitna baja", "time kya hai", "samay kya"]):
            return f"Abhi {get_time()} baj rahe hain."

        # ── Date ───────────────────────────────────────────────────────────────
        if contains_any(t, ["what date", "today date", "what day", "current date",
                             "aaj ki date", "aaj kaunsa din", "tarikh kya"]):
            return f"Aaj {get_date()} hai."

        # ── Jokes ──────────────────────────────────────────────────────────────
        if contains_any(t, ["joke", "make me laugh", "something funny",
                             "mazak", "hasao", "koi joke"]):
            return random.choice(_JOKES)

        # ── Capabilities ───────────────────────────────────────────────────────
        if contains_any(t, ["what can you do", "your abilities", "your features",
                             "tum kya kar sakte", "kya kya kar sakte",
                             "apni capabilities", "help me", "kya kaam karte"]):
            return _CAPABILITIES

        # ── Goodbye ────────────────────────────────────────────────────────────
        if contains_any(t, ["bye", "goodbye", "see you", "exit", "quit", "stop",
                             "alvida", "phir milenge", "band karo"]):
            return random.choice(_BYE)

        # ── Gemini API fallback (with session memory + system prompt) ──────────
        if config.GEMINI_API_KEY:
            return self._ask_gemini(text)

        return None   # caller will handle unknown

    # ── Gemini API (multi-turn + system prompt) ────────────────────────────────

    def _ask_gemini(self, prompt: str) -> str | None:
        """
        Send prompt to Gemini API with:
          - Full system prompt (Hinglish persona from config)
          - Multi-turn conversation history (session memory)
          - TTS-friendly output constraints
        Returns response text or None on failure.
        """
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={config.GEMINI_API_KEY}"
        )

        # Add current user message to history
        self._history.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        # Trim history to max allowed turns (each turn = user + model message)
        max_msgs = config.PERSONA_MAX_HISTORY * 2
        if len(self._history) > max_msgs:
            self._history = self._history[-max_msgs:]

        # Build payload with system instruction + conversation history
        payload = {
            "system_instruction": {
                "parts": [{"text": config.PERSONA_SYSTEM_PROMPT}]
            },
            "contents": self._history,
            "generationConfig": {
                "temperature":    0.7,    # natural but not too random
                "maxOutputTokens": 150,   # keep TTS-friendly (short answers)
                "topP":           0.9,
            },
        }

        try:
            resp = requests.post(url, json=payload, timeout=12)
            resp.raise_for_status()

            reply_text = (
                resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                .strip()
            )

            # Store assistant reply in history for next turn
            self._history.append({
                "role": "model",
                "parts": [{"text": reply_text}]
            })

            log.info(f"Gemini reply: '{reply_text[:80]}...' " if len(reply_text) > 80 else f"Gemini reply: '{reply_text}'")
            return reply_text

        except requests.HTTPError as e:
            log.error(f"Gemini HTTP error {resp.status_code}: {e}")
            # Remove the failed user message from history
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return "Maafi chahta hoon, abhi Gemini se connect nahi ho pa raha. Thodi der baad try karo."
        except Exception as e:
            log.error(f"Gemini API error: {e}")
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()
            return None


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    conv = Conversation()
    tests = [
        "Hello",
        "Good morning",
        "Kaisa hai tu?",
        "Kaun ho tum?",
        "Kitna baja hai?",
        "Koi joke sunao",
        "What can you do?",
        "Shukriya",
        "Bye",
    ]
    for t in tests:
        print(f"Q: {t}\nA: {conv.handle(t)}\n")
