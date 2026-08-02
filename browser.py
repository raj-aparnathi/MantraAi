"""
browser.py – Mantra AI v2.0
Web browsing automation using the standard webbrowser module and pyautogui
for tab management.

v2.0 additions:
  - open_new_tab()     – Ctrl+T in the active browser window
  - close_tab()        – Ctrl+W in the active browser window
  - open_bookmark()    – opens named bookmarks from config.json
  - More natural NLU routes ("show me", "take me to", "browse to")

v1.0 operations preserved:
  - open_website(), search_google(), search_youtube(), open_shortcut()
  - All existing parse_and_execute routes
"""

import webbrowser
from urllib.parse import quote_plus

import pyautogui

import config
from utils import log, normalize, contains_any, extract_after


class Browser:
    """
    v2.0 browser automation with tab management and configurable bookmarks.
    Fully backward compatible with v1.0.
    """

    # ── Built-in site shortcuts ────────────────────────────────────────────────
    _SITE_SHORTCUTS: dict[str, str] = {
        "youtube":   "https://www.youtube.com",
        "google":    "https://www.google.com",
        "gmail":     "https://mail.google.com",
        "chatgpt":   "https://chat.openai.com",
        "github":    "https://github.com",
        "wikipedia": "https://www.wikipedia.org",
        "reddit":    "https://www.reddit.com",
        "twitter":   "https://www.twitter.com",
        "instagram": "https://www.instagram.com",
        "linkedin":  "https://www.linkedin.com",
        "netflix":   "https://www.netflix.com",
        "amazon":    "https://www.amazon.com",
        "whatsapp":  "https://web.whatsapp.com",
        "maps":      "https://maps.google.com",
        "translate": "https://translate.google.com",
        "drive":     "https://drive.google.com",
        "meet":      "https://meet.google.com",
    }

    def __init__(self):
        # Load bookmarks from config (v2.0 feature)
        raw_bookmarks: dict = getattr(config, "BOOKMARKS", {})
        self._bookmarks: dict[str, str] = {
            normalize(k): v for k, v in raw_bookmarks.items()
        }
        log.info(
            f"Browser module ready. "
            f"{len(self._bookmarks)} bookmarks loaded."
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def open_website(self, url: str) -> str:
        """Open a URL directly in the default browser."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        webbrowser.open(url)
        log.info(f"Opened URL: {url}")
        return f"Opening {url}."

    def search_google(self, query: str) -> str:
        """Search Google for `query`."""
        if not query:
            return "What would you like to search for on Google?"
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        webbrowser.open(url)
        log.info(f"Google search: '{query}'")
        return f"Searching Google for {query}."

    def search_youtube(self, query: str) -> str:
        """Search YouTube for `query`."""
        if not query:
            return "What would you like to search for on YouTube?"
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        webbrowser.open(url)
        log.info(f"YouTube search: '{query}'")
        return f"Searching YouTube for {query}."

    def open_shortcut(self, site: str) -> str:
        """Open a known site by shorthand name."""
        url = self._SITE_SHORTCUTS.get(normalize(site))
        if url:
            webbrowser.open(url)
            log.info(f"Opened shortcut: {site} -> {url}")
            return f"Opening {site}."
        return f"I don't have a shortcut for {site}."

    # ── v2.0 Tab Management ────────────────────────────────────────────────────

    def open_new_tab(self) -> str:
        """Open a new tab in the currently focused browser (Ctrl+T)."""
        try:
            pyautogui.hotkey("ctrl", "t")
            log.info("Opened new browser tab.")
            return "New tab opened."
        except Exception as e:
            log.error(f"New tab error: {e}")
            return f"Sorry, I couldn't open a new tab. {e}"

    def close_tab(self) -> str:
        """Close the current browser tab (Ctrl+W)."""
        try:
            pyautogui.hotkey("ctrl", "w")
            log.info("Closed browser tab.")
            return "Tab closed."
        except Exception as e:
            log.error(f"Close tab error: {e}")
            return f"Sorry, I couldn't close the tab. {e}"

    def refresh_page(self) -> str:
        """Refresh the current browser page (F5)."""
        try:
            pyautogui.press("f5")
            log.info("Page refreshed.")
            return "Page refreshed."
        except Exception as e:
            log.error(f"Refresh error: {e}")
            return f"Sorry, I couldn't refresh the page. {e}"

    # ── v2.0 Bookmarks ─────────────────────────────────────────────────────────

    def open_bookmark(self, name: str) -> str:
        """Open a named bookmark from config.json."""
        key = normalize(name)
        # Exact match first
        if key in self._bookmarks:
            return self.open_website(self._bookmarks[key])
        # Partial match
        for bm_key, url in self._bookmarks.items():
            if key in bm_key or bm_key in key:
                return self.open_website(url)
        return (
            f"I don't have a bookmark named '{name}'. "
            "You can add bookmarks in data/config.json under 'v2.bookmarks'."
        )

    def list_bookmarks(self) -> str:
        """Speak the list of available bookmarks."""
        if not self._bookmarks:
            return (
                "You don't have any bookmarks configured. "
                "Add them to data/config.json under 'v2.bookmarks'."
            )
        names = ", ".join(self._bookmarks.keys())
        return f"Your bookmarks are: {names}."

    # ── Command Router ─────────────────────────────────────────────────────────

    def parse_and_execute(self, text: str) -> str | None:
        """
        Parse a browser-related command and execute.
        Returns spoken response or None if not matched.
        """
        t = normalize(text)

        # ── Tab management ──────────────────────────────────────────────────
        if contains_any(t, ["new tab", "open new tab", "open a new tab",
                             "open tab"]):
            return self.open_new_tab()

        if contains_any(t, ["close tab", "close this tab", "close current tab",
                             "shut tab"]):
            return self.close_tab()

        if contains_any(t, ["refresh page", "refresh the page", "reload page",
                             "reload the page", "refresh browser"]):
            return self.refresh_page()

        # ── Bookmarks ───────────────────────────────────────────────────────
        if contains_any(t, ["list bookmarks", "show bookmarks", "my bookmarks",
                             "what bookmarks"]):
            return self.list_bookmarks()

        if contains_any(t, ["open bookmark", "go to bookmark", "bookmark"]):
            for kw in ["open bookmark", "go to bookmark", "bookmark"]:
                name = extract_after(t, kw).strip()
                if name:
                    return self.open_bookmark(name)

        # ── YouTube search ──────────────────────────────────────────────────
        if "on youtube" in t or "youtube search" in t or "search youtube" in t:
            query = self._extract_search_query(
                t, ["on youtube", "youtube search", "search youtube"]
            )
            return self.search_youtube(query)

        # ── Google search ───────────────────────────────────────────────────
        if "on google" in t or "google search" in t or "search google" in t:
            query = self._extract_search_query(
                t, ["on google", "google search", "search google"]
            )
            return self.search_google(query)

        # ── Generic search (defaults to Google) ────────────────────────────
        if t.startswith("search ") and "youtube" not in t:
            query = extract_after(t, "search")
            return self.search_google(query)

        # ── Site shortcuts ──────────────────────────────────────────────────
        if contains_any(t, ["open ", "go to ", "visit ", "navigate to ",
                             "show me ", "take me to ", "browse to "]):
            for site in self._SITE_SHORTCUTS:
                if site in t:
                    return self.open_shortcut(site)

        # ── Direct URL ("open google.com") ──────────────────────────────────
        if ".com" in t or ".org" in t or ".io" in t or ".net" in t:
            words = t.split()
            for word in words:
                if any(ext in word for ext in [".com", ".org", ".io", ".net"]):
                    return self.open_website(word)

        return None

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_search_query(text: str, markers: list[str]) -> str:
        """
        Extract search query from phrases like 'search python tutorials on google'.
        Removes 'search' prefix and any trailing marker.
        """
        t = text
        if t.startswith("search "):
            t = t[len("search "):].strip()
        for marker in markers:
            if t.endswith(marker):
                t = t[: -len(marker)].strip()
            clean_marker = marker.replace("on ", "").replace("search ", "")
            if t.startswith(clean_marker):
                t = t[len(clean_marker):].strip()
        return t


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    b = Browser()
    tests = [
        "search Python tutorials on Google",
        "open YouTube",
        "search AI news on YouTube",
        "open ChatGPT",
        "open new tab",
        "list bookmarks",
        "open google.com",
        "navigate to github",
    ]
    for cmd in tests:
        result = b.parse_and_execute(cmd)
        print(f"CMD: {cmd}\nRES: {result}\n")
