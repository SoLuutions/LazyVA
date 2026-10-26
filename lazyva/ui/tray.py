from __future__ import annotations

"""
System Tray Integration for LazyVA using pystray and Pillow.
Provides persistent background presence, dynamic status indicators, and quick context actions.
"""


import sys
import threading
from typing import Callable, Optional

from PIL import Image, ImageDraw

try:
    import pystray
    HAS_PYSTRAY = True
except Exception:
    HAS_PYSTRAY = False


from lazyva import __app_name__, __version__


def create_tray_icon_image(status: str = "idle") -> Image.Image:
    """
    Renders dynamic 64x64 status icons for the Windows notification area.
    status options: 'active', 'break', 'idle'
    """
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Base circular background
    draw.ellipse((4, 4, 60, 60), fill=(18, 22, 33, 240), outline=(43, 49, 69, 255), width=2)

    if status == "active":
        # Glowing active green dot
        draw.ellipse((16, 16, 48, 48), fill=(16, 185, 129, 255))
        draw.ellipse((24, 24, 40, 40), fill=(255, 255, 255, 220))
    elif status == "break":
        # Scheduled break amber dot
        draw.ellipse((16, 16, 48, 48), fill=(245, 158, 11, 255))
        draw.ellipse((24, 24, 40, 40), fill=(255, 255, 255, 220))
    else:  # 'idle'
        # Sleek idle cyan ring
        draw.ellipse((18, 18, 46, 46), outline=(6, 182, 212, 230), width=4)
        draw.ellipse((27, 27, 37, 37), fill=(148, 163, 184, 200))

    return img


class TrayIconManager:
    """Manages the Windows taskbar notification tray icon."""

    def __init__(
        self,
        on_toggle_start_stop: Callable[[], None],
        on_show_window: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_check_updates: Callable[[], None],
        on_quit_app: Callable[[], None],
    ):
        self.on_toggle_start_stop = on_toggle_start_stop
        self.on_show_window = on_show_window
        self.on_open_settings = on_open_settings
        self.on_check_updates = on_check_updates
        self.on_quit_app = on_quit_app

        self._tray_icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        self._current_status = "idle"
        self._is_engine_active = False

    def start(self) -> bool:
        """Starts the tray icon in a dedicated daemon thread."""
        if not HAS_PYSTRAY:
            print("[LazyVA] pystray not installed. Running without system tray.")
            return False

        if self._is_running:
            return True

        self._is_running = True
        self._thread = threading.Thread(target=self._run_tray_loop, daemon=True, name="LazyVA-Tray")
        self._thread.start()
        return True

    def stop(self) -> None:
        """Stops and cleans up the tray icon."""
        self._is_running = False
        if self._tray_icon is not None:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None

    def update_status(self, is_active: bool, in_break: bool = False) -> None:
        """Updates the tray icon graphic and dynamic menu labels."""
        self._is_engine_active = is_active
        if not is_active:
            self._current_status = "idle"
        elif in_break:
            self._current_status = "break"
        else:
            self._current_status = "active"

        if self._tray_icon is not None:
            try:
                self._tray_icon.icon = create_tray_icon_image(self._current_status)
                self._tray_icon.menu = self._build_menu()
                self._tray_icon.title = (
                    f"LazyVA - {'Active' if is_active else 'Idle'}"
                    if not in_break
                    else "LazyVA - On Break"
                )
                self._tray_icon.update_menu()
            except Exception as e:
                print(f"[LazyVA] Error updating tray icon: {e}")

    def _build_menu(self) -> pystray.Menu:
        """Builds context menu entries for tray icon."""
        status_text = (
            "Status: Active (Working)"
            if self._is_engine_active and self._current_status == "active"
            else "Status: On Break (Paused)"
            if self._current_status == "break"
            else "Status: Stopped (Idle)"
        )

        toggle_label = "Stop (F10)" if self._is_engine_active else "Start (F9)"

        return pystray.Menu(
            pystray.MenuItem(status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(toggle_label, lambda icon, item: self.on_toggle_start_stop(), default=True),
            pystray.MenuItem("Settings…", lambda icon, item: self.on_open_settings()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit (F11)", lambda icon, item: self.on_quit_app()),
        )


    def _run_tray_loop(self) -> None:
        """Background thread target that runs the pystray loop."""
        try:
            self._tray_icon = pystray.Icon(
                __app_name__,
                create_tray_icon_image(self._current_status),
                f"{__app_name__} - Activity Assistant",
                menu=self._build_menu(),
            )
            self._tray_icon.run()
        except Exception as e:
            print(f"[LazyVA] Tray icon runner failed: {e}")
