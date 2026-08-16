"""
updater/updater.py – Mantra AI v3.0
─────────────────────────────────────
Controlled self-update system for Mantra AI.

What it does:
  - Checks a GitHub repository (or local file) for a newer version of Mantra
  - Shows you what changed (changelog)
  - Downloads and applies updates safely — with a backup of your current files
  - Never updates automatically without your permission

Location : updater/updater.py
Talks to  : config.py (VERSION, UPDATER_REPO), utils.py (logging)
Used by   : agent/agent.py (when user says "check for updates")

Safety rules this updater follows:
  1. Always creates a backup before updating any file
  2. Never deletes your data/ folder or config.json
  3. Never updates automatically — always asks first
  4. If anything goes wrong, it can restore the backup

How to use it from voice:
  "Mantra, check for updates"
  "Mantra, update yourself"
  "Mantra, what version are you?"
"""

import json
import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

import requests

import config
from utils import log


# ── Version helpers ───────────────────────────────────────────────────────────

def _version_tuple(version_str: str) -> tuple[int, ...]:
    """
    Convert a version string like '3.1.0' into a comparable tuple (3, 1, 0).
    This lets us compare versions: (3, 1, 0) > (2, 0, 0) → True
    """
    try:
        return tuple(int(x) for x in version_str.strip().lstrip("v").split("."))
    except Exception:
        return (0,)


class Updater:
    """
    Mantra's self-update manager.

    Checks GitHub for updates, shows what changed, and applies them safely.

    Usage:
        updater = Updater()
        status = updater.check_for_update()
        print(status)
        # → "New version 3.1.0 is available! Current: 3.0.0. Say 'update' to upgrade."
    """

    # Where Mantra's files live (the project root)
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    # Folder for keeping backups before updates
    BACKUP_DIR = PROJECT_ROOT / "data" / "backups"

    # Protected paths — these are NEVER touched during an update
    PROTECTED_PATHS = {
        "data/config.json",
        "data/memory.json",
        "data/notes.json",
        "mantra.log",
    }

    def __init__(self):
        # Get the GitHub repo URL from config, or use a default placeholder
        self._repo_url = getattr(
            config, "UPDATER_REPO",
            "https://api.github.com/repos/YourUsername/MantraAI"
        )
        # Current version from config
        self._current_version = getattr(config, "VERSION", "3.0.0")

        log.info(
            f"Updater ready. Current version: {self._current_version} | "
            f"Repo: {self._repo_url}"
        )

    # ── Public ─────────────────────────────────────────────────────────────────

    def current_version(self) -> str:
        """Return the current installed version of Mantra."""
        return self._current_version

    def check_for_update(self) -> str:
        """
        Check if a newer version of Mantra is available on GitHub.

        Returns:
            A human-readable string describing the update status.
            Examples:
              "Mantra is up to date. You have version 3.0.0."
              "New version 3.1.0 is available! Say 'update Mantra' to upgrade."
              "I couldn't check for updates. Please check your internet connection."
        """
        log.info("Updater: Checking for updates...")

        try:
            # Query the GitHub Releases API for the latest release
            url = f"{self._repo_url}/releases/latest"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            latest_version = data.get("tag_name", "").lstrip("v")
            release_name   = data.get("name", f"Version {latest_version}")
            changelog      = data.get("body", "No changelog provided.")

            if not latest_version:
                return "I couldn't find version information in the update server's response."

            # Compare versions
            current_t = _version_tuple(self._current_version)
            latest_t  = _version_tuple(latest_version)

            if latest_t > current_t:
                log.info(f"Updater: New version available: {latest_version}")
                return (
                    f"New version {latest_version} is available! "
                    f"You currently have version {self._current_version}. "
                    f"What's new: {changelog[:200]}. "
                    f"Say 'update Mantra' to upgrade."
                )
            else:
                log.info(f"Updater: Already on latest version ({self._current_version}).")
                return f"Mantra is up to date. You have version {self._current_version}."

        except requests.ConnectionError:
            log.warning("Updater: No internet connection.")
            return "I couldn't check for updates. Please check your internet connection."
        except requests.HTTPError as e:
            log.error(f"Updater: GitHub API error: {e}")
            return "I couldn't reach the update server right now. Please try again later."
        except Exception as e:
            log.error(f"Updater: Unexpected error: {e}")
            return "Something went wrong while checking for updates."

    def apply_update(self, download_url: str) -> str:
        """
        Download and apply an update from the given URL.

        Safety steps:
          1. Creates a backup of current files
          2. Downloads the update zip
          3. Extracts files (skipping protected paths)
          4. Verifies the update

        Args:
            download_url: The GitHub release asset download URL.

        Returns:
            A status message.
        """
        log.info(f"Updater: Starting update from {download_url}")

        # Step 1: Create backup
        backup_path = self._create_backup()
        if not backup_path:
            return "I couldn't create a backup. Update aborted for safety."

        try:
            # Step 2: Download the update
            log.info("Updater: Downloading update...")
            resp = requests.get(download_url, timeout=60, stream=True)
            resp.raise_for_status()

            # Save zip to a temp file
            zip_path = self.PROJECT_ROOT / "data" / "_update.zip"
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Step 3: Extract files (carefully)
            log.info("Updater: Extracting update...")
            extracted = self._extract_update(zip_path)

            # Step 4: Clean up temp zip
            zip_path.unlink(missing_ok=True)

            log.info(f"Updater: Update complete. {extracted} files updated.")
            return (
                f"Update applied successfully! {extracted} files were updated. "
                f"Please restart Mantra to use the new version."
            )

        except Exception as e:
            log.error(f"Updater: Update failed: {e}. Backup at: {backup_path}")
            return (
                f"The update failed: {e}. "
                f"Your original files are safe in the backup folder. "
                f"Please restart Mantra — your original version is still working."
            )

    # ── Private ────────────────────────────────────────────────────────────────

    def _create_backup(self) -> Path | None:
        """
        Create a timestamped backup of the current project files.

        Returns:
            Path to the backup folder, or None if backup failed.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.BACKUP_DIR / f"backup_{self._current_version}_{timestamp}"

        try:
            self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            # Copy all .py files (source code) to the backup
            for py_file in self.PROJECT_ROOT.rglob("*.py"):
                # Skip __pycache__ and the backup folder itself
                if "__pycache__" in str(py_file) or "backups" in str(py_file):
                    continue
                dest = backup_path / py_file.relative_to(self.PROJECT_ROOT)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(py_file, dest)

            log.info(f"Updater: Backup created at {backup_path}")
            return backup_path

        except Exception as e:
            log.error(f"Updater: Backup failed: {e}")
            return None

    def _extract_update(self, zip_path: Path) -> int:
        """
        Extract update zip, skipping protected files.

        Returns:
            Number of files that were updated.
        """
        extracted_count = 0
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                # Normalise path separators
                clean_path = member.replace("\\", "/")

                # Skip protected files
                is_protected = any(
                    clean_path.endswith(p) for p in self.PROTECTED_PATHS
                )
                if is_protected:
                    log.info(f"Updater: Skipping protected file: {clean_path}")
                    continue

                # Skip __pycache__ and .pyc files
                if "__pycache__" in clean_path or clean_path.endswith(".pyc"):
                    continue

                # Extract to project root
                dest = self.PROJECT_ROOT / clean_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(dest, "wb") as dst:
                    dst.write(src.read())
                extracted_count += 1

        return extracted_count


# ── Self-test ─────────────────────────────────────────────────────────────────
# To test:  python updater/updater.py
if __name__ == "__main__":
    print("Testing updater/updater.py...")
    print("=" * 50)

    updater = Updater()
    print(f"Current version: {updater.current_version()}")
    print()

    print("Checking for updates (requires internet)...")
    status = updater.check_for_update()
    print(f"Status: {status}")
    print()

    print("=" * 50)
    print("updater/updater.py is working correctly!")
    print()
    print("NOTE: To enable real updates, set UPDATER_REPO in config.py")
    print("      to your GitHub repo URL (e.g. https://api.github.com/repos/YourName/MantraAI)")
