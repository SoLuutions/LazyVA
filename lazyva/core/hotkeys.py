"""
Global Hotkey Manager for LazyVA.
Handles system-wide keyboard shortcuts (F9 Start, F10 Stop, F11 Quit).
"""

import sys
import threading
from typing import Callable, Dict, Optional

try:
    from pynput import keyboard as pynput_keyboard
    HAS_PYNPUT = True
except Exception:
    HAS_PYNPUT = False



class HotkeyManager:
    """Manages global keyboard shortcuts."""

    def __init__(self):
        self._callbacks: Dict[str, Callable[[], None]] = {}
        self._listener: Optional[pynput_keyboard.GlobalHotKeys] = None
        self._lock = threading.Lock()
        self._running = False

    def register(self, key_combo: str, callback: Callable[[], None]) -> None:
        """Registers or replaces a hotkey callback."""
        with self._lock:
            # Standardize key naming for pynput (e.g. 'f9' -> '<f9>')
            formatted = self._format_combo(key_combo)
            self._callbacks[formatted] = callback
            if self._running:
                self._restart_listener()

    def unregister(self, key_combo: str) -> None:
        """Removes a hotkey binding."""
        with self._lock:
            formatted = self._format_combo(key_combo)
            if formatted in self._callbacks:
                del self._callbacks[formatted]
                if self._running:
                    self._restart_listener()

    def start(self) -> bool:
        """Starts the global hotkey background listener."""
        if not HAS_PYNPUT:
            print("[LazyVA] pynput not installed. Global hotkeys disabled.")
            return False

        with self._lock:
            if self._running:
                return True
            self._running = True
            self._start_listener_internal()
            return True

    def stop(self) -> None:
        """Stops the global hotkey background listener."""
        with self._lock:
            self._running = False
            if self._listener is not None:
                try:
                    self._listener.stop()
                except Exception:
                    pass
                self._listener = None

    def _format_combo(self, key: str) -> str:
        """Formats hotkey strings like 'f9' into pynput '<f9>' format."""
        k = key.strip().lower()
        if k.startswith("<") and k.endswith(">"):
            return k
        if k in ("f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"):
            return f"<{k}>"
        return k

    def _start_listener_internal(self) -> None:
        if not self._callbacks:
            return
        try:
            self._listener = pynput_keyboard.GlobalHotKeys(self._callbacks)
            self._listener.daemon = True
            self._listener.start()
        except Exception as e:
            print(f"[LazyVA] Error starting hotkey listener: {e}")

    def _restart_listener(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        if self._running:
            self._start_listener_internal()
