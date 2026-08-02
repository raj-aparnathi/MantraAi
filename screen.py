"""
screen.py – Mantra AI v2.0
Screenshot capture and screen recording using mss (fast screen capture),
OpenCV (video encoding), and Pillow (image saving).

Saved files:
    Screenshots : ~/Pictures/MantraScreenshots/screenshot_YYYYMMDD_HHMMSS.png
    Recordings  : ~/Videos/MantraRecordings/recording_YYYYMMDD_HHMMSS.mp4
"""

import threading
import time
from datetime import datetime
from pathlib import Path

import mss
import mss.tools
import cv2
import numpy as np
from PIL import Image

import config
from utils import log, normalize, contains_any


class Screen:
    """
    Provides screenshot and screen recording capabilities via voice commands.

    Usage:
        screen.take_screenshot()        -> saves PNG, returns spoken response
        screen.start_recording()        -> begins background recording thread
        screen.stop_recording()         -> stops recording, saves MP4
        screen.parse_and_execute(text)  -> routes voice commands
    """

    # Recording parameters
    _FPS: int = 20
    _CODEC: str = "mp4v"

    def __init__(self):
        # Resolve save directories from config (fall back to defaults)
        self._screenshots_dir: Path = self._resolve_dir(
            getattr(config, "SCREENSHOTS_DIR", ""),
            Path.home() / "Pictures" / "MantraScreenshots"
        )
        self._recordings_dir: Path = self._resolve_dir(
            getattr(config, "RECORDINGS_DIR", ""),
            Path.home() / "Videos" / "MantraRecordings"
        )

        # Recording state
        self._recording: bool = False
        self._record_thread: threading.Thread | None = None
        self._record_stop: threading.Event = threading.Event()

        log.info(
            f"Screen module ready. "
            f"Screenshots: {self._screenshots_dir}, "
            f"Recordings: {self._recordings_dir}"
        )

    # ── Screenshot ─────────────────────────────────────────────────────────────

    def take_screenshot(self) -> str:
        """
        Capture the full screen and save it as a PNG.
        Returns a spoken response with the save path.
        """
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self._screenshots_dir / f"screenshot_{timestamp}.png"

        try:
            with mss.mss() as sct:
                monitor = sct.monitors[0]   # all monitors combined
                sct_img = sct.grab(monitor)
                # Convert to PIL and save
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img.save(str(filename))

            log.info(f"Screenshot saved: {filename}")
            return f"Screenshot saved as {filename.name}."
        except Exception as e:
            log.error(f"Screenshot error: {e}")
            return f"Sorry, I couldn't take the screenshot. {e}"

    # ── Screen Recording ───────────────────────────────────────────────────────

    def start_recording(self) -> str:
        """
        Start recording the screen in a background thread.
        Returns a spoken response.
        """
        if self._recording:
            return "I'm already recording the screen."

        self._recordings_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self._recordings_dir / f"recording_{timestamp}.mp4"

        self._record_stop.clear()
        self._recording = True
        self._record_thread = threading.Thread(
            target=self._record_loop,
            args=(filename,),
            name="ScreenRecordThread",
            daemon=True,
        )
        self._record_thread.start()

        log.info(f"Screen recording started: {filename}")
        return f"Screen recording started. Say 'stop recording' when you're done."

    def stop_recording(self) -> str:
        """
        Stop the active screen recording.
        Returns a spoken response.
        """
        if not self._recording:
            return "I'm not currently recording the screen."

        self._record_stop.set()
        if self._record_thread:
            self._record_thread.join(timeout=5)
        self._recording = False
        log.info("Screen recording stopped.")
        return "Screen recording stopped and saved."

    @property
    def is_recording(self) -> bool:
        """True if a screen recording is currently in progress."""
        return self._recording

    # ── Command Router ─────────────────────────────────────────────────────────

    def parse_and_execute(self, text: str) -> str | None:
        """
        Parse a screen-related voice command and execute it.
        Returns a spoken response, or None if not a screen command.
        """
        t = normalize(text)

        # Stop recording
        if contains_any(t, ["stop recording", "end recording", "finish recording",
                             "stop screen recording", "end screen recording"]):
            return self.stop_recording()

        # Start recording
        if contains_any(t, ["start recording", "record screen", "record my screen",
                             "begin recording", "screen record"]):
            return self.start_recording()

        # Screenshot
        if contains_any(t, ["take screenshot", "take a screenshot", "screenshot",
                             "capture screen", "capture the screen", "snap screen",
                             "take screen capture", "grab screen"]):
            return self.take_screenshot()

        return None

    # ── Internal Recording Loop ────────────────────────────────────────────────

    def _record_loop(self, output_path: Path) -> None:
        """
        Background thread: captures frames and writes to an MP4 file.
        Runs until _record_stop is set.
        """
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                width  = monitor["width"]
                height = monitor["height"]

                fourcc = cv2.VideoWriter_fourcc(*self._CODEC)
                writer = cv2.VideoWriter(
                    str(output_path), fourcc, self._FPS, (width, height)
                )

                frame_delay = 1.0 / self._FPS
                while not self._record_stop.is_set():
                    frame_start = time.monotonic()

                    raw = sct.grab(monitor)
                    # mss returns BGRA; cv2 expects BGR
                    frame = np.array(raw)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    writer.write(frame)

                    elapsed = time.monotonic() - frame_start
                    sleep_time = frame_delay - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

                writer.release()
                log.info(f"Recording saved: {output_path} ({output_path.stat().st_size // 1024} KB)")

        except Exception as e:
            log.error(f"Screen recording error: {e}")
            self._recording = False

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_dir(configured: str, default: Path) -> Path:
        """Return configured path if set and valid, else the default."""
        if configured and configured.strip():
            return Path(configured.strip())
        return default


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    s = Screen()
    print(s.take_screenshot())
    print("Testing 3-second recording...")
    print(s.start_recording())
    time.sleep(3)
    print(s.stop_recording())
