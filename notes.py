"""
notes.py – Mantra AI v1.0
Save, read, and delete notes stored in data/notes.json.
"""

import json
from datetime import datetime

import config
from utils import log, normalize, contains_any, extract_after


class Notes:

    def __init__(self):
        self._ensure_file()

    # ── File Helpers ───────────────────────────────────────────────────────────

    def _ensure_file(self) -> None:
        """Create notes.json if it doesn't exist."""
        if not config.NOTES_FILE.exists():
            config.NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
            config.NOTES_FILE.write_text("[]", encoding="utf-8")

    def _load(self) -> list[dict]:
        try:
            return json.loads(config.NOTES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log.error(f"Failed to load notes: {e}")
            return []

    def _save(self, notes: list[dict]) -> None:
        try:
            config.NOTES_FILE.write_text(
                json.dumps(notes, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except OSError as e:
            log.error(f"Failed to save notes: {e}")

    # ── CRUD ───────────────────────────────────────────────────────────────────

    def save_note(self, content: str) -> str:
        """Append a new note with a timestamp."""
        if not content.strip():
            return "What would you like me to remember? Please say the note content."

        notes = self._load()
        entry = {
            "id":        len(notes) + 1,
            "content":   content.strip(),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        notes.append(entry)
        self._save(notes)
        log.info(f"Note saved: '{content[:50]}'")
        return f"Got it! I've saved your note: {content}."

    def read_notes(self) -> str:
        """Return all notes as a spoken string."""
        notes = self._load()
        if not notes:
            return "You have no saved notes."

        if len(notes) == 1:
            n = notes[0]
            return f"You have 1 note from {self._friendly_date(n['timestamp'])}: {n['content']}."

        lines = [f"You have {len(notes)} notes."]
        for i, n in enumerate(notes, start=1):
            lines.append(f"Note {i}: {n['content']}. Saved on {self._friendly_date(n['timestamp'])}.")
        return " ".join(lines)

    def delete_notes(self, confirm_callback=None) -> str:
        """Clear all notes after optional voice confirmation."""
        notes = self._load()
        if not notes:
            return "There are no notes to delete."

        if confirm_callback:
            confirmed = confirm_callback(
                f"Are you sure you want to delete all {len(notes)} notes? Say yes to confirm."
            )
            if not confirmed:
                return "Note deletion cancelled."

        self._save([])
        log.info("All notes deleted.")
        return "All notes have been deleted."

    def delete_note_by_id(self, note_id: int) -> str:
        """Delete a specific note by its ID."""
        notes = self._load()
        original_count = len(notes)
        notes = [n for n in notes if n["id"] != note_id]
        if len(notes) == original_count:
            return f"I couldn't find note number {note_id}."
        self._save(notes)
        return f"Note {note_id} deleted."

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _friendly_date(iso: str) -> str:
        try:
            dt = datetime.fromisoformat(iso)
            return dt.strftime("%B %d at %I:%M %p")
        except ValueError:
            return iso

    # ── Command Router ─────────────────────────────────────────────────────────

    def parse_and_execute(self, text: str, confirm_callback=None) -> str | None:
        """Route a notes command. Returns spoken response or None."""
        t = normalize(text)

        # Save / Remember
        if contains_any(t, ["save a note", "take a note", "remember that", "make a note", "add a note"]):
            for kw in ["save a note", "take a note", "remember that", "make a note", "add a note"]:
                content = extract_after(t, kw)
                if content:
                    return self.save_note(content)
            return "What would you like me to note down?"

        # Read / Show
        if contains_any(t, ["read my notes", "show my notes", "what are my notes",
                             "read notes", "show notes", "my notes"]):
            return self.read_notes()

        # Delete all
        if contains_any(t, ["delete all notes", "clear all notes",
                             "delete my notes", "erase notes"]):
            return self.delete_notes(confirm_callback=confirm_callback)

        return None


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    n = Notes()
    print(n.save_note("Buy groceries – milk, eggs, and bread"))
    print(n.save_note("Meeting with team tomorrow at 10 AM"))
    print(n.read_notes())
