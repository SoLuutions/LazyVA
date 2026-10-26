"""
Configuration and persistent state manager for LazyVA.
Stores user settings in a platform-appropriate application data directory.
"""

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict

DEFAULT_SETTINGS: Dict[str, Any] = {
    # Activity Mode: 'natural' (human-like Bezier curve), 'jitter' (micro nudge), 'keepalive_only' (Windows API only)
    "mode": "natural",
    
    # Timing intervals in seconds
    "interval_min": 15,
    "interval_max": 45,
    
    # Movement parameters
    "jitter_radius": 30,
    "glide_speed": 1.0,           # Multiplier for movement speed
    
    # Auto-pause when user physically moves the mouse
    "auto_pause_on_user": True,
    "auto_pause_cooldown": 4.0,   # Seconds to wait after user stops interacting
    
    # Smart Break Scheduler (Pomodoro-style)
    "enable_breaks": True,
    "work_duration_minutes": 25,
    "break_duration_minutes": 5,
    "notify_on_break": True,
    
    # Hotkeys
    "hotkey_start": "f9",
    "hotkey_stop": "f10",
    "hotkey_quit": "f11",
    
    # Application startup & behavior
    "start_minimized": True,      # Starts directly in system tray (hidden from taskbar)
    "launch_on_startup": False,
    "close_to_tray": True,        # Closing settings window hides to system tray
    "check_updates_on_launch": True,

    
    # SaaS Licensing details
    "license_key": "",
    "cached_license_token": "",
    "last_license_check": 0.0,
    "registered_machine_id": "",
}


def get_app_dir() -> Path:
    """Returns the persistent application directory."""
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA")
        base = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
    else:
        base = Path.home() / ".config"

    app_dir = base / "LazyVA"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


class ConfigManager:
    """Thread-safe configuration manager."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.app_dir = get_app_dir()
        self.config_path = self.app_dir / "settings.json"
        self._settings = dict(DEFAULT_SETTINGS)
        self._rw_lock = threading.RLock()
        self.load()

    def load(self) -> None:
        """Loads settings from disk, applying defaults for missing keys."""
        with self._rw_lock:
            if self.config_path.exists():
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            self._settings.update(loaded)
                except Exception as e:
                    print(f"[LazyVA] Error loading config: {e}")
            else:
                self.save()

    def save(self) -> None:
        """Saves current settings to disk atomically."""
        with self._rw_lock:
            try:
                temp_path = self.config_path.with_suffix(".tmp")
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(self._settings, f, indent=2)
                temp_path.replace(self.config_path)
            except Exception as e:
                print(f"[LazyVA] Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Gets a configuration setting."""
        with self._rw_lock:
            return self._settings.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Sets a configuration setting and optionally persists it."""
        with self._rw_lock:
            self._settings[key] = value
            if auto_save:
                self.save()

    def update(self, mapping: Dict[str, Any], auto_save: bool = True) -> None:
        """Batch updates configuration settings."""
        with self._rw_lock:
            self._settings.update(mapping)
            if auto_save:
                self.save()

    def get_all(self) -> Dict[str, Any]:
        """Returns a copy of all current settings."""
        with self._rw_lock:
            return dict(self._settings)

    def set_startup_registry(self, enable: bool) -> bool:
        """Configures Windows registry to launch LazyVA on user login."""
        if sys.platform != "win32":
            return False

        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "LazyVA"
            exe_path = sys.executable

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
            ) as key:
                if enable:
                    # If running as script vs frozen exe
                    if getattr(sys, "frozen", False):
                        cmd = f'"{exe_path}" --minimized'
                    else:
                        main_py = Path(__file__).resolve().parent.parent / "run.py"
                        cmd = f'"{exe_path}" "{main_py}" --minimized'
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
            self.set("launch_on_startup", enable)
            return True
        except Exception as e:
            print(f"[LazyVA] Registry startup update failed: {e}")
            return False
