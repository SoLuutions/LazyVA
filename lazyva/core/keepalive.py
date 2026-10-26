"""
Windows Native Keep-Alive management.
Interacts directly with Windows kernel32.SetThreadExecutionState to prevent
the OS from entering sleep, dimming screens, or triggering idle timeouts.
"""

import ctypes
import sys
from typing import Optional

# Windows Execution State Flags
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_USER_PRESENT = 0x00000004
ES_AWAYMODE_REQUIRED = 0x00000040
ES_CONTINUOUS = 0x80000000


class KeepAliveManager:
    """Manages Windows power management state."""

    def __init__(self):
        self._is_windows = sys.platform == "win32"
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def enable(self, keep_display_on: bool = True) -> bool:
        """
        Signals Windows OS that the current application requires the system and
        optionally display to remain in the working state.
        """
        if not self._is_windows:
            self._active = True
            return True

        try:
            flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
            if keep_display_on:
                flags |= ES_DISPLAY_REQUIRED

            result = ctypes.windll.kernel32.SetThreadExecutionState(flags)
            self._active = result != 0
            return self._active
        except Exception as e:
            print(f"[LazyVA] Error setting execution state: {e}")
            return False

    def disable(self) -> bool:
        """Restores normal Windows power saving behavior."""
        if not self._is_windows:
            self._active = False
            return True

        try:
            result = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            self._active = False
            return result != 0
        except Exception as e:
            print(f"[LazyVA] Error clearing execution state: {e}")
            return False

    def pulse_activity(self) -> bool:
        """
        Sends a single non-continuous activity pulse to the OS to reset the idle timer.
        """
        if not self._is_windows:
            return True

        try:
            result = ctypes.windll.kernel32.SetThreadExecutionState(
                ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            return result != 0
        except Exception as e:
            print(f"[LazyVA] Error pulsing execution state: {e}")
            return False
