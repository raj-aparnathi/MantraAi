"""
apps/music_player.py – Mantra AI v3.0
──────────────────────────────────────
Local music player module to play, browse, and stop local audio files.

Location : apps/music_player.py
Talks to  : config.py (MUSIC_DIR), utils.py (logging, normalize)
Used by   : agent/tools.py → agent/agent.py
"""

from pathlib import Path
import random
import os
import subprocess
import re

import config
from utils import log, normalize, contains_any

MUSIC_FOLDER = Path(getattr(config, "MUSIC_DIR", r"D:\R09\Music"))
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"}


def _safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode())


class MusicPlayer:
    def __init__(self, music_folder: Path | str | None = None):
        if music_folder is not None:
            self.music_folder = Path(music_folder)
        else:
            self.music_folder = MUSIC_FOLDER
        self.audio_extensions = AUDIO_EXTENSIONS
        self.songs: list[Path] = self._load_songs()
        self.current_index: int = 0
        log.info(f"MusicPlayer initialised with {len(self.songs)} songs from {self.music_folder}")

    def _load_songs(self) -> list[Path]:
        """Load all audio files recursively from the music directory."""
        if not self.music_folder.exists():
            log.warning(f"Music folder does not exist: {self.music_folder}")
            return []
        songs = []
        try:
            for file in self.music_folder.rglob("*"):
                if file.is_file() and file.suffix.lower() in self.audio_extensions:
                    songs.append(file)
        except Exception as e:
            log.error(f"Error loading songs from {self.music_folder}: {e}")
        return songs

    def _clean_song_title(self, path: Path) -> str:
        """Format filename into a clean, spoken title."""
        name = path.stem
        cleaned = re.sub(r"[_\s]+", " ", name)
        cleaned = re.sub(r"\([^)]*\)|\[[^\]]*\]", "", cleaned).strip()
        return cleaned or name

    def _play_file(self, song: Path) -> str:
        """Helper to start audio playback via Windows default association."""
        try:
            os.startfile(str(song.resolve()))
        except Exception:
            try:
                subprocess.run(["start", "", song.as_posix()], shell=True, check=False)
            except Exception as e:
                log.error(f"Failed to play {song}: {e}")
                return f"Sorry, could not play {song.name}."

        title = self._clean_song_title(song)
        log.info(f"Playing song: {title} ({song.name})")
        _safe_print(f"Playing: {song.name}")
        return f"Playing {title}."

    # ── Playback Controls ──────────────────────────────────────────────────────

    def play_random_song(self) -> str:
        """Play a random song from the music library."""
        if not self.songs:
            self.songs = self._load_songs()
        if not self.songs:
            msg = "Your music folder is empty or not found."
            _safe_print(msg)
            return msg
        self.current_index = random.randrange(len(self.songs))
        song = self.songs[self.current_index]
        return self._play_file(song)

    def play_specific_song(self, song_name: str) -> str:
        """Search and play a specific song matching song_name."""
        if not self.songs:
            self.songs = self._load_songs()
        if not self.songs:
            msg = "No songs available in your music folder."
            _safe_print(msg)
            return msg

        query = normalize(song_name).replace(" ", "")
        
        # 1. Exact or partial match in normalized song stem
        matched_song = None
        for idx, song in enumerate(self.songs):
            norm_name = normalize(song.stem).replace(" ", "").replace("_", "")
            if query in norm_name:
                matched_song = song
                self.current_index = idx
                break

        # 2. Token match if query words are scattered
        if not matched_song:
            tokens = [t for t in normalize(song_name).split() if len(t) > 2]
            for idx, song in enumerate(self.songs):
                norm_stem = normalize(song.stem).replace("_", " ")
                if all(token in norm_stem for token in tokens):
                    matched_song = song
                    self.current_index = idx
                    break

        if matched_song:
            return self._play_file(matched_song)

        direct_file = self.music_folder / f"{song_name}.mp3"
        if direct_file.exists():
            return self._play_file(direct_file)

        msg = f"Could not find any song matching '{song_name}'."
        _safe_print(msg)
        return msg

    def play_next_song(self) -> str:
        """Play the next song in the library."""
        if not self.songs:
            self.songs = self._load_songs()
        if not self.songs:
            return "No songs found in music folder."
        self.current_index = (self.current_index + 1) % len(self.songs)
        song = self.songs[self.current_index]
        return self._play_file(song)

    def play_previous_song(self) -> str:
        """Play the previous song in the library."""
        if not self.songs:
            self.songs = self._load_songs()
        if not self.songs:
            return "No songs found in music folder."
        self.current_index = (self.current_index - 1) % len(self.songs)
        song = self.songs[self.current_index]
        return self._play_file(song)

    def stop_song(self) -> str:
        """Stop playback by closing Windows media players."""
        players = [
            "wmplayer.exe",
            "Microsoft.Media.Player.exe",
            "Music.UI.exe",
            "vlc.exe",
            "foobar2000.exe",
            "AIMP.exe",
        ]
        for player in players:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", player],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            except Exception:
                pass

        _safe_print("Stopped")
        log.info("Music player stopped.")
        return "Music stopped."

    # ── Song Listing & Filtering ───────────────────────────────────────────────

    def list_songs(self) -> list[str]:
        """List all songs in the music folder."""
        if not self.songs:
            self.songs = self._load_songs()
        names = []
        for song in self.songs:
            _safe_print(song.name)
            names.append(song.name)
        return names

    def _filter_songs(self, query: str) -> list[str]:
        """Helper to filter songs containing query in name or path."""
        if not self.songs:
            self.songs = self._load_songs()
        q = normalize(str(query)).replace("_", " ")
        matched = []
        for song in self.songs:
            norm_name = normalize(song.name).replace("_", " ")
            if q in norm_name or q in normalize(str(song)):
                _safe_print(song.name)
                matched.append(song.name)
        return matched

    def list_songs_by_artist(self, artist_name: str) -> list[str]:
        return self._filter_songs(artist_name)

    def list_songs_by_album(self, album_name: str) -> list[str]:
        return self._filter_songs(album_name)

    def list_songs_by_genre(self, genre_name: str) -> list[str]:
        return self._filter_songs(genre_name)

    def list_songs_by_year(self, year: str | int) -> list[str]:
        return self._filter_songs(str(year))

    def list_songs_by_duration(self, duration: str) -> list[str]:
        return self._filter_songs(duration)

    def list_songs_by_rating(self, rating: str) -> list[str]:
        return self._filter_songs(rating)

    def list_songs_by_play_count(self, play_count: str) -> list[str]:
        return self._filter_songs(play_count)

    def list_songs_by_last_played(self, last_played: str) -> list[str]:
        return self._filter_songs(last_played)

    def list_songs_by_date_added(self, date_added: str) -> list[str]:
        return self._filter_songs(date_added)

    def list_songs_by_lyrics(self, lyrics: str) -> list[str]:
        return self._filter_songs(lyrics)

    def list_songs_by_composer(self, composer: str) -> list[str]:
        return self._filter_songs(composer)

    def list_songs_by_producer(self, producer: str) -> list[str]:
        return self._filter_songs(producer)

    # ── Tool Parser & Natural Language Execution ──────────────────────────────

    def parse_and_execute(self, text: str) -> str | None:
        """
        Parse user command and trigger the corresponding MusicPlayer action.
        Returns response string if handled, or None if not a music command.
        """
        t = normalize(text)

        # 1. Stop Music
        if contains_any(t, [
            "stop music", "stop the music", "stop song", "stop songs",
            "music stop", "pause music", "band karo gana", "gana band karo",
            "music band karo", "stop playing"
        ]):
            return self.stop_song()

        # 2. Next Song
        if contains_any(t, ["next song", "play next song", "next track", "agla gana", "skip song"]):
            return self.play_next_song()

        # 3. Previous Song
        if contains_any(t, ["previous song", "play previous song", "prev song", "pichla gana"]):
            return self.play_previous_song()

        # 4. List songs by filter
        filter_triggers = [
            ("artist", ["songs by artist", "song by artist", "music by artist", "songs of artist"]),
            ("album", ["songs by album", "song by album", "from album", "songs of album"]),
            ("genre", ["songs by genre", "song by genre", "genre songs"]),
            ("year", ["songs by year", "songs from year", "released in"]),
            ("composer", ["songs by composer", "composer"]),
            ("producer", ["songs by producer", "producer"]),
            ("lyrics", ["songs by lyrics", "lyrics containing"]),
        ]
        for filter_type, patterns in filter_triggers:
            for pat in patterns:
                if pat in t:
                    query = t.split(pat, 1)[-1].strip()
                    if query:
                        if filter_type == "artist":
                            matches = self.list_songs_by_artist(query)
                        elif filter_type == "album":
                            matches = self.list_songs_by_album(query)
                        elif filter_type == "genre":
                            matches = self.list_songs_by_genre(query)
                        elif filter_type == "year":
                            matches = self.list_songs_by_year(query)
                        elif filter_type == "composer":
                            matches = self.list_songs_by_composer(query)
                        elif filter_type == "producer":
                            matches = self.list_songs_by_producer(query)
                        else:
                            matches = self.list_songs_by_lyrics(query)

                        if matches:
                            return f"Found {len(matches)} songs matching {query}."
                        return f"No songs found for {query}."

        # 5. List all songs
        if contains_any(t, ["list songs", "show songs", "show my songs", "what songs do i have", "all songs", "list all songs"]):
            songs = self.list_songs()
            if not songs:
                return "You don't have any songs in your music folder."
            sample = [self._clean_song_title(Path(s)) for s in songs[:3]]
            return f"You have {len(songs)} songs in your library, such as: {', '.join(sample)}."

        # 6. Play specific song or random song
        if contains_any(t, ["play song", "play track", "play music", "play a song", "play some music", "gana bajao", "kuch gana bajao", "music chalao", "play "]):
            # Check if user specified a song title
            for prefix in ["play song ", "play track ", "play "]:
                if prefix in t:
                    song_query = t.split(prefix, 1)[1].strip()
                    # Filter out generic words
                    if song_query in ["music", "a music", "a song", "some music", "some songs", "something"]:
                        return self.play_random_song()
                    if song_query:
                        return self.play_specific_song(song_query)

            # Generic play commands
            if contains_any(t, ["play music", "play a song", "play some music", "gana bajao", "kuch gana bajao", "music chalao"]):
                return self.play_random_song()

        return None
