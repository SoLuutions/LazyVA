"""
Application entry point and coordinator for LazyVA.
Connects the activity engine, licensing manager, global hotkeys, system tray, and GUI.
"""

import argparse
import sys
import threading
import time
from typing import Optional

from lazyva import __app_name__, __version__
from lazyva.config import ConfigManager
from lazyva.core.engine import ActivityEngine
from lazyva.core.hotkeys import HotkeyManager
from lazyva.core.scheduler import SchedulerState
from lazyva.licensing.manager import LicenseManager
from lazyva.ui.main_window import MainWindow
from lazyva.ui.tray import TrayIconManager
from lazyva.updater.auto_updater import AutoUpdater


class LazyVAApplication:
    """Master application controller."""

    def __init__(self, start_minimized: bool = False):
        self.config = ConfigManager()
        self.start_minimized = start_minimized or self.config.get("start_minimized", False)

        # 1. Initialize Subsystems
        self.licensing = LicenseManager(self.config)
        self.engine = ActivityEngine(self.config)
        self.hotkeys = HotkeyManager()
        self.updater = AutoUpdater()

        # 2. Window and Tray
        self.window: Optional[MainWindow] = None
        self.tray = TrayIconManager(
            on_toggle_start_stop=self.toggle_start_stop,
            on_show_window=self.show_window,
            on_open_settings=self.open_settings,
            on_check_updates=self.check_updates,
            on_quit_app=self.quit_app,
        )

        # 3. Setup Hotkeys
        self._setup_hotkeys()

        # 4. Sync engine state with tray
        self.engine.on_state_change = self._on_engine_state_change

    def _setup_hotkeys(self) -> None:
        """Binds global keyboard shortcuts."""
        hk_start = self.config.get("hotkey_start", "f9")
        hk_stop = self.config.get("hotkey_stop", "f10")
        hk_quit = self.config.get("hotkey_quit", "f11")

        self.hotkeys.register(hk_start, self.start_engine)
        self.hotkeys.register(hk_stop, self.stop_engine)
        self.hotkeys.register(hk_quit, self.quit_app)
        self.hotkeys.start()

    def run(self) -> None:
        """Starts background workers and GUI event loop."""
        print(f"[LazyVA] Starting {__app_name__} v{__version__}...")

        # Start system tray icon
        self.tray.start()

        # Create GUI Window
        self.window = MainWindow(
            engine=self.engine,
            licensing=self.licensing,
            config=self.config,
            on_request_hide=self.hide_window,
            on_request_quit=self.quit_app,
        )

        # Background update check if enabled
        if self.config.get("check_updates_on_launch", True):
            self.updater.check_for_updates(callback=self._on_update_check_result)

        if self.start_minimized:
            self.window.withdraw()
        else:
            self.window.deiconify()

        # Run main GUI loop (blocking)
        try:
            self.window.mainloop()
        except KeyboardInterrupt:
            self.quit_app()

    def start_engine(self) -> None:
        """Starts activity simulation."""
        self.engine.start()
        self.tray.update_status(is_active=True, in_break=False)

    def stop_engine(self) -> None:
        """Stops activity simulation."""
        self.engine.stop()
        self.tray.update_status(is_active=False, in_break=False)

    def toggle_start_stop(self) -> None:
        if self.engine.is_running:
            self.stop_engine()
        else:
            self.start_engine()

    def _on_engine_state_change(self, is_running: bool, state: SchedulerState) -> None:
        in_break = state == SchedulerState.BREAK
        self.tray.update_status(is_active=is_running, in_break=in_break)

    def show_window(self) -> None:
        """Restores and focuses the main window."""
        if self.window is not None:
            self.window.after(0, self._restore_window_internal)

    def _restore_window_internal(self) -> None:
        if self.window is not None:
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()

    def hide_window(self) -> None:
        """Minimizes window to tray."""
        if self.window is not None:
            self.window.withdraw()

    def open_settings(self) -> None:
        """Restores window and navigates to settings."""
        self.show_window()
        if self.window is not None:
            self.window.after(50, lambda: self.window._select_tab("engine"))

    def check_updates(self) -> None:
        """Triggers manual update check."""
        self.updater.check_for_updates(callback=self._on_update_check_result)

    def _on_update_check_result(self, is_newer: bool, data: Optional[dict], msg: str) -> None:
        print(f"[LazyVA] Update check: {msg}")
        if is_newer and self.window:
            self.window.after(
                0,
                lambda: self.window._append_log(
                    f"[{time.strftime('%H:%M:%S')}] Update available: {data.get('version')}!\n"
                ),
            )

    def quit_app(self) -> None:
        """Performs clean shutdown of all subsystems."""
        print("[LazyVA] Shutting down...")
        self.hotkeys.stop()
        self.engine.stop()
        self.tray.stop()
        if self.window is not None:
            try:
                self.window.quit()
                self.window.destroy()
            except Exception:
                pass
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description=f"{__app_name__} Workspace Assistant")
    parser.add_argument("--minimized", action="store_true", help="Start directly in system tray")
    parser.add_argument("--gui", action="store_true", help="Force show the main dashboard window on launch")
    parser.add_argument("--version", action="version", version=f"{__app_name__} {__version__}")
    args = parser.parse_args()

    start_minimized = None
    if args.gui:
        start_minimized = False
    elif args.minimized:
        start_minimized = True

    app = LazyVAApplication(start_minimized=start_minimized)
    app.run()



if __name__ == "__main__":
    main()
