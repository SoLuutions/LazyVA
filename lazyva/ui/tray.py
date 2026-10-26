from __future__ import annotations

"""
System Tray Integration for LazyVA using pystray and Pillow.
Provides persistent background presence, dynamic status indicators, and quick context actions.
"""


import sys
import threading
from typing import Callable, Optional

from PIL import Image, ImageDraw

from lazyva.ui.theme import THEME, resolve_color

try:
    import pystray
    HAS_PYSTRAY = True
except Exception:
    HAS_PYSTRAY = False


from lazyva import __app_name__, __version__


def create_tray_icon_image(status: str = "idle", theme: str = "day") -> Image.Image:
    """Renders a meadow-colored leaf icon with a distinct status marker."""
    appearance = "dark" if theme == "night" else "light"
    color = lambda token: resolve_color(THEME[token], appearance)
    background = color("bg_dark")
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (4, 4, 60, 60),
        radius=17,
        fill=background,
        outline=color("surface_border"),
        width=2,
    )
    draw.ellipse((15, 11, 46, 46), fill=color("accent_sage"))
    draw.polygon(((19, 39), (42, 17), (38, 43)), fill=color("accent_sage_deep"))
    draw.line((21, 41, 41, 20), fill=color("on_accent"), width=2)

    status_color = {
        "active": color("accent_sage"),
        "break": color("accent_apricot"),
        "idle": color("accent_oat"),
    }.get(status, color("accent_oat"))
    draw.ellipse((42, 42, 58, 58), fill=status_color, outline=background, width=2)
    if status == "idle":
        draw.ellipse((46, 46, 54, 54), outline=color("on_accent"), width=1)

    return img


class TrayIconManager:
    """Manages the Windows taskbar notification tray icon."""

    def __init__(
        self,
        on_toggle_start_stop: Callable[[], None],
        on_show_window: Callable[[], None],
        on_quit_app: Callable[[], None],
        on_toggle_theme: Callable[[], None],
        get_theme: Callable[[], str],
    ):
        self.on_toggle_start_stop = on_toggle_start_stop
        self.on_show_window = on_show_window
        self.on_quit_app = on_quit_app
        self.on_toggle_theme = on_toggle_theme
        self.get_theme = get_theme

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
                self._tray_icon.icon = create_tray_icon_image(
                    self._current_status, self.get_theme()
                )
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
            "Awake and steady"
            if self._is_engine_active and self._current_status == "active"
            else "Rest time"
            if self._current_status == "break"
            else "Resting"
        )

        toggle_label = "Stop" if self._is_engine_active else "Start"
        theme_label = "Switch to day" if self.get_theme() == "night" else "Switch to night"

        return pystray.Menu(
            pystray.MenuItem(status_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(toggle_label, lambda icon, item: self.on_toggle_start_stop(), default=True),
            pystray.MenuItem("Open LazyVA", lambda icon, item: self.on_show_window()),
            pystray.MenuItem(theme_label, lambda icon, item: self.on_toggle_theme()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda icon, item: self.on_quit_app()),
        )


    def _run_tray_loop(self) -> None:
        """Background thread target that runs the pystray loop."""
        try:
            self._tray_icon = pystray.Icon(
                __app_name__,
                create_tray_icon_image(self._current_status, self.get_theme()),
                f"{__app_name__} - Activity Assistant",
                menu=self._build_menu(),
            )
            self._tray_icon.run()
        except Exception as e:
            print(f"[LazyVA] Tray icon runner failed: {e}")
