"""
system_control.py – Mantra AI v2.0
PC power management, audio volume, and screen brightness control.

v2.0 additions:
  - brightness_up() / brightness_down() via screen-brightness-control
  - Configurable volume step from config.json
  - Natural-language brightness aliases

v1.0 operations preserved:
  - shutdown, restart, lock, sleep, cancel_shutdown
  - volume_up, volume_down, mute, unmute, get_volume
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
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return volume
    except Exception as e:
        log.error(f"pycaw unavailable: {e}")
        return None


# ── Brightness Control (screen-brightness-control) ────────────────────────────

def _get_brightness_module():
    """Return the screen_brightness_control module, or None if unavailable."""
    try:
        import screen_brightness_control as sbc
        return sbc
    except ImportError:
        log.warning("screen-brightness-control not installed. Brightness control unavailable.")
        return None


class SystemControl:
    """
    v2.0 system control: power, volume, and brightness management.
    All v1.0 commands remain fully functional.
    """

    VOLUME_STEP: float = 0.1       # 10 % per command (configurable via config)
    BRIGHTNESS_STEP: int = 10      # 10 % per command

    def __init__(self):
        # Allow config override for volume step
        self.VOLUME_STEP = getattr(config, "VOLUME_STEP", 0.1)

    # ── Power Controls ─────────────────────────────────────────────────────────

    def shutdown(self) -> str:
        log.warning("Shutdown command issued.")
        subprocess.run(["shutdown", "/s", "/t", "5"], shell=True)
        return "Shutting down your computer in 5 seconds. Goodbye!"

    def restart(self) -> str:
        log.warning("Restart command issued.")
        subprocess.run(["shutdown", "/r", "/t", "5"], shell=True)
        return "Restarting your computer in 5 seconds."

    def lock(self) -> str:
        log.info("Locking computer.")
        ctypes.windll.user32.LockWorkStation()
        return "Computer locked."

    def sleep(self) -> str:
        log.info("Putting computer to sleep.")
        subprocess.run(
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=True
        )
        return "Putting your computer to sleep. Good night!"

    def cancel_shutdown(self) -> str:
        subprocess.run(["shutdown", "/a"], shell=True)
        return "Shutdown cancelled."

    # ── Volume Controls ────────────────────────────────────────────────────────

    def volume_up(self) -> str:
        vol = _get_volume_interface()
        if vol:
            current = vol.GetMasterVolumeLevelScalar()
            new_vol = min(1.0, current + self.VOLUME_STEP)
            vol.SetMasterVolumeLevelScalar(new_vol, None)
            log.info(f"Volume up: {current:.0%} -> {new_vol:.0%}")
            return f"Volume increased to {int(new_vol * 100)} percent."
        return "Sorry, I couldn't control the volume."

    def volume_down(self) -> str:
        vol = _get_volume_interface()
        if vol:
            current = vol.GetMasterVolumeLevelScalar()
            new_vol = max(0.0, current - self.VOLUME_STEP)
            vol.SetMasterVolumeLevelScalar(new_vol, None)
            log.info(f"Volume down: {current:.0%} -> {new_vol:.0%}")
            return f"Volume decreased to {int(new_vol * 100)} percent."
        return "Sorry, I couldn't control the volume."

    def mute(self) -> str:
        vol = _get_volume_interface()
        if vol:
            vol.SetMute(1, None)
            log.info("System muted.")
            return "System is now muted."
        return "Sorry, I couldn't mute the system."

    def unmute(self) -> str:
        vol = _get_volume_interface()
        if vol:
            vol.SetMute(0, None)
            log.info("System unmuted.")
            return "System is now unmuted."
        return "Sorry, I couldn't unmute the system."

    def get_volume(self) -> str:
        vol = _get_volume_interface()
        if vol:
            current = vol.GetMasterVolumeLevelScalar()
            muted   = vol.GetMute()
            status  = "muted" if muted else f"{int(current * 100)} percent"
            return f"Current volume is {status}."
        return "I couldn't read the volume level."

    # ── Brightness Controls ────────────────────────────────────────────────────

    def brightness_up(self) -> str:
        """Increase screen brightness by BRIGHTNESS_STEP percent."""
        sbc = _get_brightness_module()
        if not sbc:
            return (
                "Brightness control is not available. "
                "Please install screen-brightness-control."
            )
        try:
            current = sbc.get_brightness(display=0)
            # get_brightness may return a list for multiple monitors
            if isinstance(current, list):
                current = current[0]
            new_val = min(100, current + self.BRIGHTNESS_STEP)
            sbc.set_brightness(new_val, display=0)
            log.info(f"Brightness up: {current}% -> {new_val}%")
            return f"Brightness increased to {new_val} percent."
        except Exception as e:
            log.error(f"Brightness up error: {e}")
            return f"Sorry, I couldn't increase the brightness. {e}"

    def brightness_down(self) -> str:
        """Decrease screen brightness by BRIGHTNESS_STEP percent."""
        sbc = _get_brightness_module()
        if not sbc:
            return (
                "Brightness control is not available. "
                "Please install screen-brightness-control."
            )
        try:
            current = sbc.get_brightness(display=0)
            if isinstance(current, list):
                current = current[0]
            new_val = max(10, current - self.BRIGHTNESS_STEP)
            sbc.set_brightness(new_val, display=0)
            log.info(f"Brightness down: {current}% -> {new_val}%")
            return f"Brightness decreased to {new_val} percent."
        except Exception as e:
            log.error(f"Brightness down error: {e}")
            return f"Sorry, I couldn't decrease the brightness. {e}"

    def get_brightness(self) -> str:
        """Return the current brightness level as a spoken string."""
        sbc = _get_brightness_module()
        if not sbc:
            return "Brightness reading is not available."
        try:
            current = sbc.get_brightness(display=0)
            if isinstance(current, list):
                current = current[0]
            return f"Current screen brightness is {current} percent."
        except Exception as e:
            log.error(f"Get brightness error: {e}")
            return "I couldn't read the brightness level."

    # ── Command Router ─────────────────────────────────────────────────────────

    def parse_and_execute(self, text: str, confirm_callback=None) -> str | None:
        """
        Parse system commands. `confirm_callback` is called for
        destructive actions (shutdown/restart) and should return bool.
        Returns spoken response or None if not matched.
        """
        t = normalize(text)

        # ── Volume ─────────────────────────────────────────────────────────────
        if contains_any(t, ["volume up", "increase volume", "turn up", "louder",
                             "raise volume", "turn volume up"]):
            return self.volume_up()
        if contains_any(t, ["volume down", "decrease volume", "turn down", "quieter",
                             "lower volume", "turn volume down"]):
            return self.volume_down()
        if contains_any(t, ["unmute", "sound on", "turn sound on"]):
            return self.unmute()
        if contains_any(t, ["mute", "silent mode", "silence", "no sound"]):
            return self.mute()
        if contains_any(t, ["what is the volume", "current volume", "volume level",
                             "how loud"]):
            return self.get_volume()

        # ── Brightness ─────────────────────────────────────────────────────────
        if contains_any(t, ["brightness up", "increase brightness", "brighter",
                             "more brightness", "turn up brightness",
                             "make it brighter", "increase the brightness"]):
            return self.brightness_up()
        if contains_any(t, ["brightness down", "decrease brightness", "dimmer",
                             "less brightness", "turn down brightness",
                             "make it dimmer", "dim screen", "dim the screen",
                             "decrease the brightness"]):
            return self.brightness_down()
        if contains_any(t, ["what is the brightness", "current brightness",
                             "brightness level"]):
            return self.get_brightness()

        # ── Lock / Sleep (safe – no confirmation needed) ────────────────────
        if contains_any(t, ["lock", "lock computer", "lock my computer",
                             "lock screen", "lock the screen"]):
            return self.lock()
        if contains_any(t, ["sleep", "sleep mode", "hibernate", "go to sleep",
                             "put computer to sleep"]):
            return self.sleep()

        # ── Shutdown / Restart (destructive – require confirmation) ──────────
        if contains_any(t, ["shutdown", "shut down", "turn off", "power off",
                             "switch off"]):
            if confirm_callback:
                confirmed = confirm_callback(
                    "Are you sure you want to shut down? Say yes to confirm."
                )
                if not confirmed:
                    return "Shutdown cancelled."
            return self.shutdown()

        if contains_any(t, ["restart", "reboot", "restart computer",
                             "reboot computer"]):
            if confirm_callback:
                confirmed = confirm_callback(
                    "Are you sure you want to restart? Say yes to confirm."
                )
                if not confirmed:
                    return "Restart cancelled."
            return self.restart()

        if contains_any(t, ["cancel shutdown", "abort shutdown", "stop shutdown"]):
            return self.cancel_shutdown()

        return None


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sc = SystemControl()
    print(sc.get_volume())
    print(sc.volume_up())
    print(sc.volume_down())
    print(sc.get_brightness())
