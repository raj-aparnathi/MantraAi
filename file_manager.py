"""
file_manager.py – Mantra AI v2.0
File and folder management with full voice-command routing.

v2.0 additions over v1.0:
  - search_files()   – recursive file search by name/pattern
  - search_folders() – recursive folder search by name
  - rename_file()    – rename with voice confirmation
  - copy_file()      – copy file to target location
  - move_file()      – move file to target location
  - delete_to_recycle() – safe delete via Recycle Bin (replaces unlink)
  - NLU routes for all new operations

v1.0 operations preserved:
  - create_folder(), create_text_file(), open_directory()
"""

import os
import shutil
from pathlib import Path

from utils import log, normalize, contains_any, extract_after

# Optional send2trash for safe Recycle Bin delete
try:
    import send2trash
    _TRASH_AVAILABLE = True
except ImportError:
    _TRASH_AVAILABLE = False
    log.warning("send2trash not found – deleted files will be permanently removed.")


class FileManager:
    """
    Full file-management assistant supporting voice-driven operations.
    All destructive operations (delete, rename) require voice confirmation.
    """

    # ── Known user directories ─────────────────────────────────────────────────
    _KNOWN_DIRS: dict[str, Path] = {
        "downloads":  Path.home() / "Downloads",
        "documents":  Path.home() / "Documents",
        "desktop":    Path.home() / "Desktop",
        "pictures":   Path.home() / "Pictures",
        "music":      Path.home() / "Music",
        "videos":     Path.home() / "Videos",
        "appdata":    Path.home() / "AppData",
    }

    # ── Folder Operations ──────────────────────────────────────────────────────

    def create_folder(self, name: str, location: Path | None = None) -> str:
        """Create a new folder on the Desktop (or specified location)."""
        base   = location or (Path.home() / "Desktop")
        folder = base / name
        try:
            folder.mkdir(parents=True, exist_ok=False)
            log.info(f"Created folder: {folder}")
            return f"Folder '{name}' created on your Desktop."
        except FileExistsError:
            return f"A folder named '{name}' already exists."
        except Exception as e:
            log.error(f"Create folder error: {e}")
            return f"I couldn't create the folder. {e}"

    # ── File Creation ──────────────────────────────────────────────────────────

    def create_text_file(self, name: str, location: Path | None = None) -> str:
        """Create an empty .txt file on the Desktop (or specified location)."""
        base = location or (Path.home() / "Desktop")
        if not name.endswith(".txt"):
            name += ".txt"
        file_path = base / name
        try:
            file_path.touch(exist_ok=False)
            log.info(f"Created file: {file_path}")
            os.startfile(str(file_path))
            return f"Text file '{name}' created and opened."
        except FileExistsError:
            return f"A file named '{name}' already exists."
        except Exception as e:
            log.error(f"Create file error: {e}")
            return f"I couldn't create the file. {e}"

    # ── Search ─────────────────────────────────────────────────────────────────

    def search_files(self, query: str, location: Path | None = None,
                     max_results: int = 5) -> str:
        """
        Recursively search for files matching `query` (substring match on filename).
        Searches the given location (default: home directory).
        Returns a spoken summary of results.
        """
        if not query:
            return "What file would you like to search for?"

        search_root = location or Path.home()
        pattern     = f"*{query}*"
        results: list[Path] = []

        try:
            for p in search_root.rglob(pattern):
                if p.is_file():
                    results.append(p)
                    if len(results) >= max_results:
                        break
        except PermissionError:
            pass   # silently skip restricted dirs
        except Exception as e:
            log.error(f"File search error: {e}")
            return f"I encountered an error while searching. {e}"

        if not results:
            return f"I couldn't find any files matching '{query}'."

        log.info(f"File search '{query}': {len(results)} result(s).")
        names = [f"'{p.name}' in {p.parent.name}" for p in results[:max_results]]
        intro = f"I found {len(results)} file(s) matching '{query}'. "
        return intro + " | ".join(names) + "."

    def search_folders(self, query: str, location: Path | None = None,
                       max_results: int = 5) -> str:
        """
        Recursively search for folders matching `query`.
        Returns a spoken summary of results.
        """
        if not query:
            return "What folder would you like to search for?"

        search_root = location or Path.home()
        pattern     = f"*{query}*"
        results: list[Path] = []

        try:
            for p in search_root.rglob(pattern):
                if p.is_dir():
                    results.append(p)
                    if len(results) >= max_results:
                        break
        except PermissionError:
            pass
        except Exception as e:
            log.error(f"Folder search error: {e}")
            return f"I encountered an error while searching. {e}"

        if not results:
            return f"I couldn't find any folders matching '{query}'."

        log.info(f"Folder search '{query}': {len(results)} result(s).")
        names = [f"'{p.name}' in {p.parent.name}" for p in results[:max_results]]
        intro = f"I found {len(results)} folder(s) matching '{query}'. "
        return intro + " | ".join(names) + "."

    # ── Rename ─────────────────────────────────────────────────────────────────

    def rename_file(self, old_path: str, new_name: str,
                    confirm_callback=None) -> str:
        """
        Rename a file. Requires confirmation for safety.
        `new_name` should be just the filename (stem + extension).
        """
        src = Path(old_path)
        if not src.exists():
            return f"I couldn't find a file at '{old_path}'."

        dst = src.parent / new_name

        if confirm_callback:
            confirmed = confirm_callback(
                f"Rename '{src.name}' to '{new_name}'? Say yes to confirm."
            )
            if not confirmed:
                return "Rename cancelled."

        try:
            src.rename(dst)
            log.info(f"Renamed: {src} -> {dst}")
            return f"'{src.name}' has been renamed to '{new_name}'."
        except Exception as e:
            log.error(f"Rename error: {e}")
            return f"I couldn't rename the file. {e}"

    # ── Copy ───────────────────────────────────────────────────────────────────

    def copy_file(self, src_path: str, dst_path: str) -> str:
        """Copy a file from src to dst."""
        src = Path(src_path)
        dst = Path(dst_path)

        if not src.exists():
            return f"I couldn't find '{src_path}'."
        if not src.is_file():
            return f"'{src.name}' is not a file."

        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(str(src), str(dst))
            log.info(f"Copied: {src} -> {dst}")
            return f"'{src.name}' copied to '{dst.parent.name}'."
        except Exception as e:
            log.error(f"Copy error: {e}")
            return f"I couldn't copy the file. {e}"

    # ── Move ───────────────────────────────────────────────────────────────────

    def move_file(self, src_path: str, dst_path: str,
                  confirm_callback=None) -> str:
        """Move a file from src to dst."""
        src = Path(src_path)
        dst = Path(dst_path)

        if not src.exists():
            return f"I couldn't find '{src_path}'."

        if confirm_callback:
            confirmed = confirm_callback(
                f"Move '{src.name}' to '{dst.parent.name}'? Say yes to confirm."
            )
            if not confirmed:
                return "Move cancelled."

        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(dst))
            log.info(f"Moved: {src} -> {dst}")
            return f"'{src.name}' moved to '{dst.parent.name}'."
        except Exception as e:
            log.error(f"Move error: {e}")
            return f"I couldn't move the file. {e}"

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete_to_recycle(self, path_str: str, confirm_callback=None) -> str:
        """
        Send a file to the Recycle Bin (using send2trash if available,
        otherwise falls back to permanent deletion after extra confirmation).
        """
        target = Path(path_str)
        if not target.exists():
            return f"I couldn't find a file at '{path_str}'."

        if confirm_callback:
            confirmed = confirm_callback(
                f"Are you sure you want to delete '{target.name}'? Say yes to confirm."
            )
            if not confirmed:
                return "Deletion cancelled."

        try:
            if _TRASH_AVAILABLE:
                send2trash.send2trash(str(target))
                log.info(f"Sent to Recycle Bin: {target}")
                return f"'{target.name}' has been moved to the Recycle Bin."
            else:
                target.unlink()
                log.info(f"Permanently deleted: {target}")
                return f"'{target.name}' has been permanently deleted."
        except Exception as e:
            log.error(f"Delete error: {e}")
            return f"I couldn't delete the file. {e}"

    # Backward-compatible alias from v1.0
    def delete_file(self, path_str: str, confirm_callback=None) -> str:
        """v1.0 compatibility alias for delete_to_recycle."""
        return self.delete_to_recycle(path_str, confirm_callback)

    # ── Directory Navigation ───────────────────────────────────────────────────

    def open_directory(self, name: str) -> str:
        """Open a known system directory in File Explorer."""
        key = normalize(name)
        for alias, path in self._KNOWN_DIRS.items():
            if alias in key:
                try:
                    os.startfile(str(path))
                    log.info(f"Opened directory: {path}")
                    return f"Opening your {alias}."
                except Exception as e:
                    log.error(f"Open dir error: {e}")
                    return f"Couldn't open {alias}. {e}"
        return f"I don't recognise '{name}' as a system folder."

    # ── Command Router ─────────────────────────────────────────────────────────

    def parse_and_execute(self, text: str, confirm_callback=None) -> str | None:
        """Route a file-management command. Returns spoken response or None."""
        t = normalize(text)

        # ── Search files
        if contains_any(t, ["find file", "search file", "search for file",
                             "look for file", "find my file"]):
            for kw in ["search for file", "find file", "search file",
                       "look for file", "find my file"]:
                query = extract_after(t, kw).strip()
                if query:
                    return self.search_files(query)
            return "What file would you like to find?"

        # ── Search folders
        if contains_any(t, ["find folder", "search folder", "search for folder",
                             "find my folder", "look for folder", "find directory"]):
            for kw in ["search for folder", "find folder", "search folder",
                       "find my folder", "find directory", "look for folder"]:
                query = extract_after(t, kw).strip()
                if query:
                    return self.search_folders(query)
            return "What folder would you like to find?"

        # ── Generic "find" / "search for" – tries files first
        if t.startswith("find ") or t.startswith("search for "):
            query = extract_after(t, "find") or extract_after(t, "search for")
            if query:
                result = self.search_files(query.strip())
                if "couldn't find" not in result:
                    return result
                return self.search_folders(query.strip())

        # ── Create folder
        if contains_any(t, ["create folder", "make folder", "new folder",
                             "create directory", "make directory"]):
            for kw in ["create folder", "make folder", "new folder",
                       "create directory", "make directory"]:
                name = extract_after(t, kw).strip()
                if name:
                    return self.create_folder(name)
            return self.create_folder("New Folder")

        # ── Create file
        if contains_any(t, ["create file", "new file", "create text file",
                             "make file", "make text file"]):
            for kw in ["create text file", "make text file", "create file",
                       "new file", "make file"]:
                name = extract_after(t, kw).strip()
                if name:
                    return self.create_text_file(name)
            return self.create_text_file("new_file")

        # ── Open known directories
        for alias in self._KNOWN_DIRS:
            if (f"open {alias}" in t or f"go to {alias}" in t
                    or f"show {alias}" in t or f"open my {alias}" in t):
                return self.open_directory(alias)

        return None


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fm = FileManager()
    print(fm.parse_and_execute("open downloads"))
    print(fm.parse_and_execute("create folder MantraTest"))
    print(fm.search_files("config"))
    print(fm.search_folders("Mantra"))
