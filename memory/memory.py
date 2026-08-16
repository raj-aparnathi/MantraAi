"""
memory/memory.py – Mantra AI v3.0
───────────────────────────────────
Mantra's persistent memory — stores and retrieves facts across sessions.

What it does:
  - Remembers things you tell Mantra (e.g. "remember my birthday is March 5")
  - Stores them in data/memory.json so they survive restarts
  - Lets Mantra recall, update, or forget any stored fact

Where it fits:
  agent/agent.py  →  memory/memory.py  ←→  data/memory.json

Example use cases:
  User: "Remember that my wife's name is Priya."
  User: "What is my wife's name?"
  User: "Forget my wife's name."

Does NOT know about:
  - Voice, LLMs, windows, tools
  - It is ONLY a simple key-value storage system
"""

import json
from pathlib import Path

import config
from utils import log


class Memory:
    """
    Persistent key-value memory backed by a JSON file.

    Keys are short names like "wife_name" or "favourite_colour".
    Values are strings (what Mantra should remember).

    Usage:
        mem = Memory()
        mem.remember("city", "Mumbai")
        mem.recall("city")     # → "Mumbai"
        mem.forget("city")
    """

    # Where to save the memory file
    # Defaults to data/memory.json inside the project folder
    DEFAULT_MEMORY_FILE = Path(__file__).resolve().parent.parent / "data" / "memory.json"

    def __init__(self):
        # Get the memory file path from config (or use the default above)
        memory_path = getattr(config, "MEMORY_FILE", None)
        if memory_path:
            self._file = Path(memory_path)
        else:
            self._file = self.DEFAULT_MEMORY_FILE

        # Make sure the data/ folder exists
        self._file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing memories from disk into a Python dictionary
        self._data: dict[str, str] = self._load()

        log.info(f"Memory loaded. {len(self._data)} facts stored. File: {self._file}")

    # ── Public ─────────────────────────────────────────────────────────────────

    def remember(self, key: str, value: str) -> None:
        """
        Store a fact in memory.

        Args:
            key:   A short identifier (e.g. "wife_name", "home_city")
            value: The thing to remember (e.g. "Priya", "Mumbai")

        Example:
            mem.remember("favourite_food", "biryani")
        """
        key = self._clean_key(key)  # normalise the key (lowercase, no spaces)
        self._data[key] = value
        self._save()
        log.info(f"Memory: Remembered '{key}' = '{value}'")

    def recall(self, key: str) -> str | None:
        """
        Retrieve a stored fact.

        Args:
            key: The identifier of the fact to retrieve.

        Returns:
            The stored value, or None if not found.

        Example:
            name = mem.recall("wife_name")  # → "Priya" or None
        """
        key = self._clean_key(key)
        value = self._data.get(key)
        if value:
            log.info(f"Memory: Recalled '{key}' = '{value}'")
        else:
            log.info(f"Memory: '{key}' not found.")
        return value

    def forget(self, key: str) -> bool:
        """
        Delete a stored fact.

        Args:
            key: The identifier of the fact to forget.

        Returns:
            True if it was found and deleted, False if it didn't exist.

        Example:
            mem.forget("wife_name")  # → True
        """
        key = self._clean_key(key)
        if key in self._data:
            del self._data[key]
            self._save()
            log.info(f"Memory: Forgot '{key}'")
            return True
        log.info(f"Memory: '{key}' not found (nothing to forget).")
        return False

    def all_memories(self) -> dict[str, str]:
        """
        Return everything Mantra currently remembers.

        Returns:
            A copy of the memory dictionary.
            Example: {"wife_name": "Priya", "home_city": "Mumbai"}
        """
        return dict(self._data)   # return a copy so the original can't be edited accidentally

    def clear_all(self) -> None:
        """
        Delete ALL memories. Use with caution!
        This permanently erases data/memory.json.
        """
        self._data.clear()
        self._save()
        log.warning("Memory: ALL memories cleared.")

    def count(self) -> int:
        """Return how many facts Mantra remembers."""
        return len(self._data)

    # ── Private ────────────────────────────────────────────────────────────────

    def _clean_key(self, key: str) -> str:
        """
        Normalise a key:
          - Convert to lowercase
          - Replace spaces with underscores
          - Strip leading/trailing whitespace
        Example: "Wife Name " → "wife_name"
        """
        return key.strip().lower().replace(" ", "_")

    def _load(self) -> dict[str, str]:
        """Read memory.json from disk. Returns empty dict if file doesn't exist."""
        if not self._file.exists():
            return {}
        try:
            with open(self._file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Make sure it's a plain dictionary (guard against corrupted file)
            if isinstance(data, dict):
                return data
            log.warning("Memory: memory.json has unexpected format. Starting fresh.")
            return {}
        except json.JSONDecodeError:
            log.error("Memory: memory.json is corrupted. Starting with empty memory.")
            return {}

    def _save(self) -> None:
        """Write the current memory dictionary to memory.json on disk."""
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                # indent=2 makes the JSON file human-readable when you open it
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Memory: Failed to save memory.json: {e}")


# ── Self-test ─────────────────────────────────────────────────────────────────
# To test:  python memory/memory.py
if __name__ == "__main__":
    print("Testing memory/memory.py...")
    print("=" * 50)

    mem = Memory()
    print(f"Starting with {mem.count()} memories.\n")

    # Test 1: Remember something
    print("Test 1: remember('city', 'Mumbai')")
    mem.remember("city", "Mumbai")
    print(f"  Stored: city = {mem.recall('city')}")

    # Test 2: Remember with spaces in key
    print("\nTest 2: remember('wife name', 'Priya')")
    mem.remember("wife name", "Priya")  # key will be saved as "wife_name"
    print(f"  Stored: wife_name = {mem.recall('wife_name')}")

    # Test 3: Recall something that exists
    print("\nTest 3: recall('city')")
    value = mem.recall("city")
    print(f"  Result: {value}")

    # Test 4: Recall something that doesn't exist
    print("\nTest 4: recall('favourite_food')")
    value = mem.recall("favourite_food")
    print(f"  Result: {value}  (None = not found, as expected)")

    # Test 5: All memories
    print("\nTest 5: all_memories()")
    all_mem = mem.all_memories()
    for k, v in all_mem.items():
        print(f"  {k}: {v}")

    # Test 6: Forget
    print("\nTest 6: forget('city')")
    result = mem.forget("city")
    print(f"  Deleted: {result}")
    print(f"  recall('city') now: {mem.recall('city')}  (None = deleted, as expected)")

    print(f"\nFinal memory count: {mem.count()}")
    print("=" * 50)
    print("memory/memory.py is working correctly!")
    print(f"Check your data/memory.json file to see the stored data.")
