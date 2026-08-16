"""
system/system_control.py – Mantra AI v3.0
──────────────────────────────────────────
PC power management, audio volume, and screen brightness control.

Location : system/system_control.py
Talks to  : config.py, utils.py
Used by   : agent/agent.py (via agent/tools.py)

This file is a clean copy of the root-level system_control.py,
moved to the system/ package as part of the v3.0 architecture refactor.

v2.0 operations preserved:
  - shutdown, restart, lock, sleep, cancel_shutdown
  - volume_up, volume_down, mute, unmute, get_volume
  - brightness_up, brightness_down (via screen-brightness-control)
  - parse_and_execute() for natural-language command routing
"""

import os
import subprocess
import ctypes

from utils import log, normalize, contains_any

import config


# ── Volume Control (pycaw) ────────────────────────────────────────────────────

def _get_volume_interface():
    """Return the Windows Core Audio volume interface, or None if unavailable."""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception as e:
        log.warning(f"pycaw not available: {e}")
        return None


# ── Brightness Control ────────────────────────────────────────────────────────

def _get_brightness() -> int | None:
    """Return current brightness (0-100) or None if unavailable."""
    try:
        import screen_brightness_control as sbc
        val = sbc.get_brightness()
        return val[0] if isinstance(val, list) else val
    except Exception:
        return None


def _set_brightness(value: int) -> bool:
    """Set brightness to value (0-100). Returns True on success."""
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(max(0, min(100, value)))
        return True
    except Exception as e:
        log.error(f"Brightness control failed: {e}")
        return False


# ── SystemControl Class ───────────────────────────────────────────────────────

class SystemControl:
    """
    Windows system control: power, volume, brightness.

    Usage:
        sc = SystemControl()
        sc.shutdown(delay=60)
        sc.volume_up()
        sc.brightness_down()
    """

    def __init__(self):
        self._vol = _get_volume_interface()
        log.info(f"SystemControl ready. pycaw available: {self._vol is not None}")

    # ── Power ──────────────────────────────────────────────────────────────────

    def shutdown(self, delay: int = 60) -> str:
        """Schedule a shutdown in `delay` seconds."""
        os.system(f"shutdown /s /t {delay}")
        log.info(f"Shutdown scheduled in {delay}s.")
        return f"Shutting down in {delay} seconds. Say 'cancel shutdown' to abort."

    def restart(self, delay: int = 10) -> str:
        """Schedule a restart in `delay` seconds."""
        os.system(f"shutdown /r /t {delay}")
        log.info(f"Restart scheduled in {delay}s.")
        return f"Restarting in {delay} seconds."

    def lock(self) -> str:
        """Lock the Windows screen."""
        ctypes.windll.user32.LockWorkStation()
        return "Screen locked."

    def sleep(self) -> str:
        """Put the PC to sleep."""
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Going to sleep."

    def cancel_shutdown(self) -> str:
        """Cancel a scheduled shutdown."""
        os.system("shutdown /a")
        return "Shutdown cancelled."

    # ── Volume ─────────────────────────────────────────────────────────────────

    def get_volume(self) -> str:
        """Return current volume as a percentage string."""
        if self._vol:
            try:
                level = self._vol.GetMasterVolumeLevelScalar()
                pct = int(level * 100)
                return f"Volume is at {pct} percent."
            except Exception:
                pass
        return "I can't read the volume level right now."

    def volume_up(self) -> str:
        """Increase volume by VOLUME_STEP."""
        if self._vol:
            try:
                current = self._vol.GetMasterVolumeLevelScalar()
                new_vol = min(1.0, current + config.VOLUME_STEP)
                self._vol.SetMasterVolumeLevelScalar(new_vol, None)
                return f"Volume increased to {int(new_vol * 100)} percent."
            except Exception as e:
                log.error(f"volume_up error: {e}")
        # Fallback: Windows keyboard shortcut
        import pyautogui
        pyautogui.press("volumeup", presses=5)
        return "Volume increased."

    def volume_down(self) -> str:
        """Decrease volume by VOLUME_STEP."""
        if self._vol:
            try:
                current = self._vol.GetMasterVolumeLevelScalar()
                new_vol = max(0.0, current - config.VOLUME_STEP)
                self._vol.SetMasterVolumeLevelScalar(new_vol, None)
                return f"Volume decreased to {int(new_vol * 100)} percent."
            except Exception as e:
                log.error(f"volume_down error: {e}")
        import pyautogui
        pyautogui.press("volumedown", presses=5)
        return "Volume decreased."

    def mute(self) -> str:
        """Mute the system volume."""
        if self._vol:
            try:
                self._vol.SetMute(1, None)
                return "Volume muted."
            except Exception:
                pass
        import pyautogui
        pyautogui.press("volumemute")
        return "Volume muted."

    def unmute(self) -> str:
        """Unmute the system volume."""
        if self._vol:
            try:
                self._vol.SetMute(0, None)
                return "Volume unmuted."
            except Exception:
                pass
        import pyautogui
        pyautogui.press("volumemute")
        return "Volume unmuted."

    # ── Brightness ─────────────────────────────────────────────────────────────

    def brightness_up(self) -> str:
        """Increase brightness by BRIGHTNESS_STEP."""
        current = _get_brightness()
        if current is None:
            return "Sorry, I can't control brightness on this display."
        new_val = min(100, current + config.BRIGHTNESS_STEP)
        _set_brightness(new_val)
        return f"Brightness increased to {new_val} percent."

    def brightness_down(self) -> str:
        """Decrease brightness by BRIGHTNESS_STEP."""
        current = _get_brightness()
        if current is None:
            return "Sorry, I can't control brightness on this display."
        new_val = max(10, current - config.BRIGHTNESS_STEP)
        _set_brightness(new_val)
        return f"Brightness decreased to {new_val} percent."

    def set_brightness(self, level: int) -> str:
        """Set brightness to a specific level (0–100)."""
        if _set_brightness(level):
            return f"Brightness set to {level} percent."
        return "Sorry, I couldn't change the brightness."

    # ── Natural Language Routing ───────────────────────────────────────────────

    def parse_and_execute(self, text: str, confirm_callback=None) -> str | None:
        """
        Parse a natural-language command and execute the matching system action.
        Returns a response string, or None if no system command was matched.
        """
        t = normalize(text)

        # ── Shutdown ───────────────────────────────────────────────────────────
        if contains_any(t, ["shut down", "shutdown", "turn off"]):
            if confirm_callback:
                if not confirm_callback("Are you sure you want to shut down?"):
                    return "Shutdown cancelled."
            return self.shutdown()

        if contains_any(t, ["cancel shutdown", "abort shutdown", "stop shutdown"]):
            return self.cancel_shutdown()

        # ── Restart ────────────────────────────────────────────────────────────
        if contains_any(t, ["restart", "reboot"]):
            if confirm_callback:
                if not confirm_callback("Are you sure you want to restart?"):
                    return "Restart cancelled."
            return self.restart()

        # ── Lock / Sleep ───────────────────────────────────────────────────────
        if contains_any(t, ["lock", "lock screen", "lock computer"]):
            return self.lock()

        if contains_any(t, ["sleep", "hibernate", "suspend"]):
            return self.sleep()

        # ── Volume ─────────────────────────────────────────────────────────────
        if contains_any(t, ["volume up", "increase volume", "louder", "turn up"]):
            return self.volume_up()

        if contains_any(t, ["volume down", "decrease volume", "quieter", "turn down", "lower volume"]):
            return self.volume_down()

        if contains_any(t, ["mute", "silence", "shut up"]):
            return self.mute()

        if contains_any(t, ["unmute", "turn on volume", "restore volume"]):
            return self.unmute()

        if contains_any(t, ["volume", "how loud", "current volume"]):
            return self.get_volume()

        # ── Brightness ─────────────────────────────────────────────────────────
        if contains_any(t, ["brightness up", "increase brightness", "brighter", "more brightness"]):
            return self.brightness_up()

        if contains_any(t, ["brightness down", "decrease brightness", "dimmer", "less brightness", "reduce brightness"]):
            return self.brightness_down()

        # Specific level: "set brightness to 70"
        if "brightness" in t and ("set" in t or "percent" in t or "%"):
            import re
            match = re.search(r"(\d+)", t)
            if match:
                level = int(match.group(1))
                return self.set_brightness(level)

        return None  # not a system command


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sc = SystemControl()
    print("SystemControl loaded.")
    print(sc.get_volume())
    print("Volume up...")
    print(sc.volume_up())
    print("Volume down...")
    print(sc.volume_down())
