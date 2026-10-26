"""Calm, pastel desktop interface for LazyVA."""

import threading
import time
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk
import tkinter as tk
from PIL import Image

from lazyva import __app_name__, __version__
from lazyva.config import ConfigManager
from lazyva.core.engine import ActivityEngine

from lazyva.core.scheduler import SchedulerState
from lazyva.licensing.manager import LicenseManager, LicenseTier
from .theme import (
    DISPLAY_FONT_FAMILY,
    FONT_FAMILY,
    RADIUS,
    SPACE,
    THEME,
    resolve_color,
)





# Configure CustomTkinter defaults
ctk.set_default_color_theme("blue")

EVENT_MODE_LABELS = {
    "move": "Movement only",
    "click": "Right-click only",
    "scroll": "Scroll only",
    "mixed": "Mix movement, right-click, and scroll",
}


class MainWindow(ctk.CTk):
    """Primary application window for LazyVA."""

    def __init__(
        self,
        engine: ActivityEngine,
        licensing: LicenseManager,
        config: ConfigManager,
        on_request_hide: Optional[Callable[[], None]] = None,
        on_request_quit: Optional[Callable[[], None]] = None,
        on_theme_change: Optional[Callable[[], None]] = None,
    ):
        super().__init__()

        self.engine = engine
        self.licensing = licensing
        self.config = config
        self.on_request_hide = on_request_hide
        self.on_request_quit = on_request_quit
        self.on_theme_change = on_theme_change

        appearance = self.config.get("theme", "system")
        if appearance not in {"system", "day", "night"}:
            appearance = "system"
        self.config.set("theme", appearance, auto_save=False)
        ctk.set_appearance_mode(
            {"system": "system", "day": "light", "night": "dark"}[appearance]
        )

        self.title(f"{__app_name__} — a little room to breathe")
        self.geometry("720x560")
        self.minsize(640, 520)
        self.configure(fg_color=THEME["bg_dark"])

        # Set Icon
        self._set_app_icon()

        # Handle window close button (X)
        self.protocol("WM_DELETE_WINDOW", self._on_close_event)

        # Wire callbacks
        self.engine.on_state_change = self._on_engine_state_change
        self.engine.on_activity_pulse = self._on_activity_pulse
        self.licensing.on_license_updated = self._on_license_status_updated

        # UI State variables
        self._active_tab = "dashboard"
        self._recent_logs = []

        # Build UI Structure
        self._build_sidebar()
        self._build_content_area()

        # Start periodic UI refresh timer (updates live counters every second)
        self._start_ui_loop()

    def _set_app_icon(self) -> None:
        """Sets window and taskbar icon."""
        try:
            icon_name = "icon_night.png" if self.current_theme() == "night" else "icon.png"
            icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / icon_name
            if icon_path.exists():
                icon_img = Image.open(icon_path)
                # Tkinter photo image
                import tkinter as tk
                from PIL import ImageTk
                self._icon_photo = ImageTk.PhotoImage(icon_img)
                self.iconphoto(False, self._icon_photo)
        except Exception as e:
            print(f"[LazyVA] Error setting window icon: {e}")

    def _build_sidebar(self) -> None:
        """Builds the compact header and pill-shaped view navigation."""
        header = ctk.CTkFrame(self, fg_color="transparent", height=56)
        header.pack(fill="x", padx=SPACE["lg"], pady=(SPACE["sm"], 0))
        header.pack_propagate(False)

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side="left", fill="y")
        ctk.CTkLabel(
            brand,
            text=__app_name__,
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w", pady=(5, 0))
        ctk.CTkLabel(
            brand,
            text=f"Rest, rhythm, and a little breathing room · v{__version__}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=THEME["text_secondary"],
        ).pack(anchor="w")

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.pack(side="right", fill="y")
        self.theme_toggle_btn = ctk.CTkButton(
            actions,
            text="",
            width=150,
            height=34,
            corner_radius=RADIUS["pill"],
            border_width=1,
            border_color=THEME["surface_border"],
            fg_color=THEME["surface"],
            hover_color=THEME["surface_elevated"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self.toggle_theme,
        )
        self.theme_toggle_btn.pack(side="right", padx=(SPACE["sm"], 0), pady=10)

        self.header_status = ctk.CTkLabel(
            actions,
            text="○ Resting",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=THEME["text_secondary"],
        )
        self.header_status.pack(side="right", pady=10)
        self._update_theme_button()

        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.pack(fill="x", padx=SPACE["lg"], pady=(SPACE["sm"], 0))
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Today"),
            ("engine", "Movement"),
            ("scheduler", "Rhythm"),
            ("hotkeys", "Preferences"),
            ("license", "License"),
        ]

        for tab_id, text in nav_items:
            btn = ctk.CTkButton(
                nav_frame,
                text=text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                height=34,
                corner_radius=RADIUS["pill"],
                fg_color="transparent",
                text_color=THEME["text_secondary"],
                hover_color=THEME["surface_elevated"],
                command=lambda tid=tab_id: self._select_tab(tid),
            )
            btn.pack(side="left", padx=(0, SPACE["xs"]))
            self.nav_buttons[tab_id] = btn

    def _build_content_area(self) -> None:
        """Constructs the active view below the header and navigation."""
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(
            fill="both",
            expand=True,
            padx=SPACE["lg"],
            pady=(SPACE["sm"], SPACE["md"]),
        )

        # Tab Views Dictionary
        self.tabs = {}
        self.tabs["dashboard"] = self._create_dashboard_view()
        self.tabs["engine"] = self._create_engine_view()
        self.tabs["scheduler"] = self._create_scheduler_view()
        self.tabs["hotkeys"] = self._create_hotkeys_view()
        self.tabs["license"] = self._create_license_view()

        # Display initial tab
        self._select_tab("dashboard")

    def _select_tab(self, tab_id: str) -> None:
        """Switches the active view and updates navigation styling."""
        self._active_tab = tab_id
        for tid, frame in self.tabs.items():
            if tid == tab_id:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                btn.configure(
                    fg_color=THEME["accent_sage"],
                    text_color=THEME["on_accent"],
                    hover_color=THEME["accent_sage_deep"],
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=THEME["text_secondary"],
                    hover_color=THEME["surface_elevated"],
                )

    def toggle_theme(self) -> None:
        next_theme = "day" if ctk.get_appearance_mode().lower() == "dark" else "night"
        self.config.set("theme", next_theme)
        ctk.set_appearance_mode("dark" if next_theme == "night" else "light")
        self._refresh_pomodoro_ring(self.engine.scheduler.get_cycle_progress())
        self._update_theme_button()
        self._set_app_icon()
        if self.on_theme_change:
            self.on_theme_change()

    def current_theme(self) -> str:
        return "night" if ctk.get_appearance_mode().lower() == "dark" else "day"

    def _update_theme_button(self) -> None:
        mode = self.current_theme()
        label = "Twilight" if mode == "day" else "Soft Meadow"
        self.theme_toggle_btn.configure(
            text=f"☾ Switch to {label}" if mode == "day" else f"☼ Switch to {label}"
        )

    # ── View 1: Today ──────────────────────────────────────────────────────────────
    def _create_dashboard_view(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.content_container, fg_color="transparent")
        hour = time.localtime().tm_hour
        greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        ctk.CTkLabel(
            view,
            text=greeting,
            font=ctk.CTkFont(family=FONT_FAMILY, size=23, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            view,
            text="A little room to breathe, whenever you need it.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=THEME["text_secondary"],
        ).pack(anchor="w", pady=(0, SPACE["sm"]))

        hero = ctk.CTkFrame(
            view,
            fg_color=THEME["surface"],
            corner_radius=RADIUS["card"],
            border_width=1,
            border_color=THEME["surface_border"],
        )
        hero.pack(fill="x", pady=(0, SPACE["md"]), padx=1)

        hero_top = ctk.CTkFrame(hero, fg_color="transparent")
        hero_top.pack(fill="x", padx=SPACE["md"], pady=(SPACE["md"], SPACE["xs"]))

        self.hero_status_badge = ctk.CTkLabel(
            hero_top,
            text="○ Resting",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=THEME["badge_idle_text"],
            fg_color=THEME["badge_idle_bg"],
            corner_radius=RADIUS["pill"],
            padx=12,
            pady=6,
        )
        self.hero_status_badge.pack(side="left")

        self.plan_indicator = ctk.CTkLabel(
            hero_top,
            text="Licensed" if self.licensing.is_pro else f"{self.licensing.days_remaining} days left in your free trial",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=THEME["on_accent"],
            fg_color=THEME["accent_sky"],
            corner_radius=RADIUS["pill"],
            padx=10,
            pady=6,
        )

        hero_body = ctk.CTkFrame(hero, fg_color="transparent")
        hero_body.pack(fill="x", padx=SPACE["md"], pady=(SPACE["xs"], SPACE["md"]))

        hero_copy = ctk.CTkFrame(hero_body, fg_color="transparent")
        hero_copy.pack(side="left", fill="both", expand=True)

        self.live_timer_lbl = ctk.CTkLabel(
            hero_copy,
            text=f"{int(self.config.get('work_duration_minutes', 25)):02d}:00",
            font=ctk.CTkFont(family=DISPLAY_FONT_FAMILY, size=38, weight="bold"),
            text_color=THEME["text_primary"],
        )
        self.live_timer_lbl.pack(anchor="w", pady=(0, 0))

        self.timer_phase_lbl = ctk.CTkLabel(
            hero_copy,
            text="Focus, at your own pace",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=THEME["text_secondary"],
        )
        self.timer_phase_lbl.pack(anchor="w")

        action_buttons = ctk.CTkFrame(hero_body, fg_color="transparent")
        action_buttons.pack(side="right", padx=(SPACE["sm"], 0))
        self.hero_action_btn = ctk.CTkButton(
            action_buttons,
            text="Start",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            width=82,
            height=42,
            corner_radius=RADIUS["pill"],
            fg_color=THEME["accent_sage"],
            hover_color=THEME["accent_sage_deep"],
            text_color=THEME["on_accent"],
            command=self.engine.start,
        )
        self.hero_action_btn.pack(side="left", padx=(0, SPACE["xs"]))
        self.hero_stop_btn = ctk.CTkButton(
            action_buttons,
            text="Stop",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            width=82,
            height=42,
            corner_radius=RADIUS["pill"],
            border_width=1,
            border_color=THEME["accent_sage_deep"],
            fg_color="transparent",
            hover_color=THEME["surface_elevated"],
            text_color=THEME["text_secondary"],
            state="disabled",
            command=self.engine.stop,
        )
        self.hero_stop_btn.pack(side="left")

        cards_row = ctk.CTkFrame(view, fg_color="transparent")
        cards_row.pack(fill="x", pady=(0, SPACE["md"]))
        cards_row.grid_columnconfigure((0, 1), weight=1, uniform="dashboard")

        mode_column = ctk.CTkFrame(cards_row, fg_color="transparent")
        mode_column.grid(row=0, column=0, sticky="nsew", padx=(0, SPACE["sm"]))
        mode_card = self._create_card(mode_column, "Movement mode")
        self.mode_var = ctk.StringVar(value=self.config.get("mode", "natural"))
        mode_value = {
            "natural": "Glide",
            "jitter": "Nudge",
            "keepalive_only": "Native",
        }.get(self.mode_var.get(), "Glide")
        mode_controls = ctk.CTkFrame(mode_card, fg_color="transparent")
        mode_controls.pack(fill="x", padx=SPACE["md"], pady=(SPACE["sm"], SPACE["md"]))
        self.dashboard_mode_buttons = {}
        for label in ("Glide", "Nudge", "Native"):
            button = ctk.CTkButton(
                mode_controls,
                text=label,
                width=76,
                height=34,
                corner_radius=RADIUS["pill"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                command=lambda selected=label: self._on_dashboard_mode_change(selected),
            )
            button.pack(side="left", fill="x", expand=True, padx=2)
            self.dashboard_mode_buttons[label] = button
        self._update_mode_buttons(mode_value)

        focus_column = ctk.CTkFrame(cards_row, fg_color="transparent")
        focus_column.grid(row=0, column=1, sticky="nsew", padx=(SPACE["sm"], 0))
        focus_card = self._create_card(focus_column, "Focus rhythm")
        self.pomodoro_ring = tk.Canvas(
            focus_card,
            width=108,
            height=108,
            highlightthickness=0,
            bd=0,
            bg=resolve_color(THEME["surface"], ctk.get_appearance_mode()),
        )
        self.pomodoro_ring.pack(side="right", padx=SPACE["sm"], pady=SPACE["xs"])
        self.pomodoro_track = self.pomodoro_ring.create_arc(
            12, 12, 96, 96, start=0, extent=359, style=tk.ARC, width=8
        )
        self.pomodoro_arc = self.pomodoro_ring.create_arc(
            12, 12, 96, 96, start=90, extent=0, style=tk.ARC, width=8
        )
        self.pomodoro_time_item = self.pomodoro_ring.create_text(
            54,
            49,
            text=f"{int(self.config.get('work_duration_minutes', 25)):02d}:00",
            font=(DISPLAY_FONT_FAMILY, 17, "bold"),
        )
        self.pomodoro_phase_item = self.pomodoro_ring.create_text(
            54, 69, text="Focus", font=(FONT_FAMILY, 9)
        )
        self._refresh_pomodoro_ring(0.0)
        ctk.CTkLabel(
            focus_card,
            text="A gentle pause is part of the rhythm.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=THEME["text_secondary"],
            wraplength=130,
            justify="left",
        ).pack(side="left", fill="x", expand=True, padx=(SPACE["md"], 0), pady=SPACE["sm"])

        footer = ctk.CTkFrame(view, fg_color="transparent")
        footer.pack(fill="x", pady=(0, SPACE["xs"]))
        self._create_hotkey_chip(footer, "F9", "Start").pack(side="left", padx=(0, SPACE["xs"]))
        self._create_hotkey_chip(footer, "F10", "Stop").pack(side="left", padx=(0, SPACE["xs"]))
        self._create_hotkey_chip(footer, "F11", "Exit").pack(side="left")
        self.plan_indicator.pack(side="right")

        return view

    def _create_hotkey_chip(self, parent, key: str, label: str) -> ctk.CTkFrame:
        chip = ctk.CTkFrame(
            parent,
            fg_color=THEME["surface_elevated"],
            corner_radius=RADIUS["pill"],
        )
        ctk.CTkLabel(
            chip,
            text=key,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(side="left", padx=(SPACE["sm"], SPACE["xs"]), pady=SPACE["xs"])
        ctk.CTkLabel(
            chip,
            text=label,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=THEME["text_secondary"],
        ).pack(side="left", padx=(0, SPACE["sm"]), pady=SPACE["xs"])
        return chip

    def _on_dashboard_mode_change(self, value: str) -> None:
        self.mode_var.set({"Glide": "natural", "Nudge": "jitter", "Native": "keepalive_only"}[value])
        self._on_settings_change()

    def _update_mode_buttons(self, selected: str) -> None:
        for label, button in self.dashboard_mode_buttons.items():
            is_selected = label == selected
            button.configure(
                fg_color=THEME["accent_sage"] if is_selected else THEME["surface_elevated"],
                hover_color=THEME["accent_sage_deep"] if is_selected else THEME["surface_border"],
                text_color=THEME["on_accent"] if is_selected else THEME["text_secondary"],
            )

    def _refresh_pomodoro_ring(self, progress: float) -> None:
        appearance = ctk.get_appearance_mode()
        self.pomodoro_ring.configure(bg=resolve_color(THEME["surface"], appearance))
        self.pomodoro_ring.itemconfigure(
            self.pomodoro_track,
            outline=resolve_color(THEME["surface_elevated"], appearance),
        )
        self.pomodoro_ring.itemconfigure(
            self.pomodoro_arc,
            outline=resolve_color(THEME["accent_lavender"], appearance),
            extent=-360 * max(0.0, min(1.0, progress)),
        )
        for item in (self.pomodoro_time_item, self.pomodoro_phase_item):
            self.pomodoro_ring.itemconfigure(
                item,
                fill=resolve_color(THEME["text_primary"], appearance),
            )

    # ── View 2: Movement Engine Settings ──────────────────────────────────────────
    def _create_engine_view(self) -> ctk.CTkScrollableFrame:
        view = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
            scrollbar_button_color=THEME["surface_elevated"],
        )

        title = ctk.CTkLabel(
            view,
            text="Movement",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=THEME["text_primary"],
        )
        title.pack(anchor="w", pady=(0, SPACE["sm"]))

        mode_card = self._create_card(view, "Choose a gentle way to keep things awake")
        self.mode_var.set(self.config.get("mode", "natural"))

        modes = [
            ("natural", "Glide", "A soft, natural cursor movement."),
            ("jitter", "Nudge", "A small movement, then back again."),
            ("keepalive_only", "Native", "Keep the screen awake without moving the cursor."),
        ]

        for val, name, desc in modes:
            r_frame = ctk.CTkFrame(mode_card, fg_color="transparent")
            r_frame.pack(fill="x", padx=16, pady=6)
            rb = ctk.CTkRadioButton(
                r_frame,
                text=name,
                variable=self.mode_var,
                value=val,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                fg_color=THEME["accent_sage_deep"],
                hover_color=THEME["accent_sage"],
                border_color=THEME["surface_border"],
                command=self._on_settings_change,
            )
            rb.pack(anchor="w")
            d_lbl = ctk.CTkLabel(
                r_frame,
                text=desc,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=THEME["text_secondary"],
            )
            d_lbl.pack(anchor="w", padx=(28, 0))

        interval_card = self._create_card(view, "Event frequency")

        interval = int(self.config.get("activity_interval_seconds", 60))
        self.activity_interval_val_lbl = ctk.CTkLabel(
            interval_card,
            text=self._format_activity_interval(interval),
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=THEME["text_primary"],
        )
        self.activity_interval_val_lbl.pack(anchor="w", padx=16, pady=(8, 0))

        self.activity_interval_slider = ctk.CTkSlider(
            interval_card,
            from_=5,
            to=300,
            number_of_steps=59,
            command=self._update_activity_interval,
            progress_color=THEME["accent_sage_deep"],
            button_color=THEME["accent_sage"],
            button_hover_color=THEME["accent_sage_deep"],
            fg_color=THEME["surface_elevated"],
        )
        self.activity_interval_slider.set(interval)
        self.activity_interval_slider.pack(fill="x", padx=16, pady=(4, 16))

        event_card = self._create_card(view, "Scheduled event")
        current_event_mode = self.config.get("activity_event_mode", "move")
        self.event_mode_var = ctk.StringVar(
            value=EVENT_MODE_LABELS.get(current_event_mode, "Movement only")
        )
        self.event_mode_menu = ctk.CTkOptionMenu(
            event_card,
            values=list(EVENT_MODE_LABELS.values()),
            variable=self.event_mode_var,
            command=lambda _: self._on_settings_change(),
            fg_color=THEME["accent_sage"],
            button_color=THEME["accent_sage_deep"],
            button_hover_color=THEME["primary_hover"],
            text_color=THEME["on_accent"],
            dropdown_fg_color=THEME["surface"],
            dropdown_text_color=THEME["text_primary"],
            dropdown_hover_color=THEME["surface_elevated"],
        )
        self.event_mode_menu.pack(anchor="w", padx=16, pady=(12, 8))
        ctk.CTkLabel(
            event_card,
            text="Click events send a right-click; scroll events scroll the active window.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=THEME["text_secondary"],
        ).pack(anchor="w", padx=16, pady=(0, 12))

        pause_card = self._create_card(view, "When you move the mouse")

        self.auto_pause_switch = ctk.CTkSwitch(
            pause_card,
            text="Step aside while you are using the mouse",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=THEME["accent_sage"],
            button_color=THEME["surface"],
            button_hover_color=THEME["surface_elevated"],
            fg_color=THEME["surface_elevated"],
            command=self._on_settings_change,
        )
        if self.config.get("auto_pause_on_user", True):
            self.auto_pause_switch.select()
        self.auto_pause_switch.pack(anchor="w", padx=16, pady=(12, 8))

        self.cooldown_val_lbl = ctk.CTkLabel(
            pause_card,
            text=f"Wait before resuming: {self.config.get('auto_pause_cooldown')} sec",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=THEME["text_secondary"],
        )
        self.cooldown_val_lbl.pack(anchor="w", padx=16, pady=(4, 0))

        self.cooldown_slider = ctk.CTkSlider(
            pause_card,
            from_=1.0,
            to=15.0,
            number_of_steps=28,
            command=self._update_cooldown,
            progress_color=THEME["accent_sage_deep"],
            button_color=THEME["accent_sage"],
            button_hover_color=THEME["accent_sage_deep"],
            fg_color=THEME["surface_elevated"],
        )
        self.cooldown_slider.set(self.config.get("auto_pause_cooldown", 4.0))
        self.cooldown_slider.pack(fill="x", padx=16, pady=(4, 16))

        window_events_card = self._create_card(view, "Optional Chrome tab event")
        self.chrome_tab_switch = ctk.CTkSwitch(
            window_events_card,
            text="Allow Ctrl+Tab when Google Chrome is active",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=THEME["accent_sage"],
            button_color=THEME["surface"],
            button_hover_color=THEME["surface_elevated"],
            fg_color=THEME["surface_elevated"],
            command=self._on_settings_change,
        )
        if self.config.get("chrome_tab_switch_enabled", False):
            self.chrome_tab_switch.select()
        self.chrome_tab_switch.pack(anchor="w", padx=16, pady=(4, 8))
        ctk.CTkLabel(
            window_events_card,
            text="When enabled, this replaces the scheduled action only while Chrome is active.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=THEME["text_secondary"],
        ).pack(anchor="w", padx=16, pady=(0, 12))

        return view

    # ── View 3: Smart Breaks (Scheduler) ──────────────────────────────────────────
    def _create_scheduler_view(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.content_container, fg_color="transparent")

        title = ctk.CTkLabel(
            view,
            text="A gentler rhythm",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=THEME["text_primary"],
        )
        title.pack(anchor="w", pady=(0, SPACE["sm"]))

        sched_card = self._create_card(view, "Time for focus, then time to rest")

        self.enable_breaks_switch = ctk.CTkSwitch(
            sched_card,
            text="Make room for regular breaks",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            progress_color=THEME["accent_sage"],
            button_color=THEME["surface"],
            button_hover_color=THEME["surface_elevated"],
            fg_color=THEME["surface_elevated"],
            command=self._on_settings_change,
        )
        if self.config.get("enable_breaks", True):
            self.enable_breaks_switch.select()
        self.enable_breaks_switch.pack(anchor="w", padx=16, pady=(12, 10))

        # Work Duration
        self.work_dur_lbl = ctk.CTkLabel(
            sched_card,
            text=f"Focus time: {self.config.get('work_duration_minutes')} minutes",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=THEME["text_primary"],
        )
        self.work_dur_lbl.pack(anchor="w", padx=16, pady=(6, 0))

        self.work_dur_slider = ctk.CTkSlider(
            sched_card,
            from_=10,
            to=90,
            number_of_steps=16,
            command=lambda val: self._update_scheduler_durations(),
            progress_color=THEME["accent_sage_deep"],
            button_color=THEME["accent_sage"],
            button_hover_color=THEME["accent_sage_deep"],
            fg_color=THEME["surface_elevated"],
        )
        self.work_dur_slider.set(self.config.get("work_duration_minutes", 25))
        self.work_dur_slider.pack(fill="x", padx=16, pady=(4, 14))

        # Break Duration
        self.break_dur_lbl = ctk.CTkLabel(
            sched_card,
            text=f"Rest time: {self.config.get('break_duration_minutes')} minutes",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=THEME["text_primary"],
        )
        self.break_dur_lbl.pack(anchor="w", padx=16, pady=(4, 0))

        self.break_dur_slider = ctk.CTkSlider(
            sched_card,
            from_=1,
            to=20,
            number_of_steps=19,
            command=lambda val: self._update_scheduler_durations(),
            progress_color=THEME["accent_lavender"],
            button_color=THEME["accent_lavender"],
            button_hover_color=THEME["accent_sage_deep"],
            fg_color=THEME["surface_elevated"],
        )
        self.break_dur_slider.set(self.config.get("break_duration_minutes", 5))
        self.break_dur_slider.pack(fill="x", padx=16, pady=(4, 16))

        # Notification toggle
        self.notify_break_switch = ctk.CTkSwitch(
            sched_card,
            text="Let me know when it is time to rest",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=THEME["accent_sage"],
            button_color=THEME["surface"],
            button_hover_color=THEME["surface_elevated"],
            fg_color=THEME["surface_elevated"],
            command=self._on_settings_change,
        )
        if self.config.get("notify_on_break", True):
            self.notify_break_switch.select()
        self.notify_break_switch.pack(anchor="w", padx=16, pady=(0, 16))

        return view

    # ── View 4: Hotkeys & System ──────────────────────────────────────────────────
    def _create_hotkeys_view(self) -> ctk.CTkFrame:
        view = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
            scrollbar_button_color=THEME["surface_elevated"],
        )

        title = ctk.CTkLabel(
            view,
            text="Preferences",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=THEME["text_primary"],
        )
        title.pack(anchor="w", pady=(0, SPACE["sm"]))

        hk_card = self._create_card(view, "A few handy shortcuts")

        hk_grid = ctk.CTkFrame(hk_card, fg_color="transparent")
        hk_grid.pack(fill="x", padx=SPACE["md"], pady=SPACE["sm"])

        ctk.CTkLabel(hk_grid, text="Start", font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=THEME["text_primary"]).grid(row=0, column=0, sticky="w", pady=6)
        ctk.CTkLabel(hk_grid, text="F9", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=THEME["accent_sage_text"]).grid(
            row=0, column=1, sticky="w", padx=16, pady=6
        )

        ctk.CTkLabel(hk_grid, text="Stop", font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=THEME["text_primary"]).grid(row=1, column=0, sticky="w", pady=6)
        ctk.CTkLabel(hk_grid, text="F10", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=THEME["accent_apricot_text"]).grid(
            row=1, column=1, sticky="w", padx=16, pady=6
        )

        ctk.CTkLabel(hk_grid, text="Quit LazyVA", font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=THEME["text_primary"]).grid(row=2, column=0, sticky="w", pady=6)
        ctk.CTkLabel(hk_grid, text="F11", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=THEME["accent_rose_text"]).grid(
            row=2, column=1, sticky="w", padx=16, pady=6
        )

        win_card = self._create_card(view, "When LazyVA starts or closes")

        self.startup_switch = ctk.CTkSwitch(
            win_card,
            text="Open LazyVA when I sign in to Windows",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=THEME["accent_sage"],
            button_color=THEME["surface"],
            button_hover_color=THEME["surface_elevated"],
            fg_color=THEME["surface_elevated"],
            command=self._on_toggle_startup,
        )
        if self.config.get("launch_on_startup", False):
            self.startup_switch.select()
        self.startup_switch.pack(anchor="w", padx=16, pady=(12, 8))

        self.minimized_switch = ctk.CTkSwitch(
            win_card,
            text="Start quietly in the system tray",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=THEME["accent_sage"],
            button_color=THEME["surface"],
            button_hover_color=THEME["surface_elevated"],
            fg_color=THEME["surface_elevated"],
            command=self._on_settings_change,
        )
        if self.config.get("start_minimized", False):
            self.minimized_switch.select()
        self.minimized_switch.pack(anchor="w", padx=16, pady=(4, 8))

        self.close_to_tray_switch = ctk.CTkSwitch(
            win_card,
            text="Keep LazyVA in the tray when I close this window",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            progress_color=THEME["accent_sage"],
            button_color=THEME["surface"],
            button_hover_color=THEME["surface_elevated"],
            fg_color=THEME["surface_elevated"],
            command=self._on_settings_change,
        )
        if self.config.get("close_to_tray", True):
            self.close_to_tray_switch.select()
        self.close_to_tray_switch.pack(anchor="w", padx=16, pady=(4, 16))

        log_card = self._create_card(view, "A quiet little activity log")
        self.log_textbox = ctk.CTkTextbox(
            log_card,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=THEME["surface_elevated"],
            text_color=THEME["text_secondary"],
            corner_radius=RADIUS["input"],
            border_width=1,
            border_color=THEME["surface_border"],
        )
        self.log_textbox.pack(fill="both", expand=True, padx=SPACE["md"], pady=(SPACE["xs"], SPACE["md"]))
        self.log_textbox.insert("end", f"{time.strftime('%H:%M')}  LazyVA is ready.\n")
        self.log_textbox.configure(state="disabled")

        return view

    # ── View 5: License ───────────────────────────────────────────────────────────
    def _create_license_view(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.content_container, fg_color="transparent")

        title = ctk.CTkLabel(
            view,
            text="Your LazyVA plan",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=THEME["text_primary"],
        )
        title.pack(anchor="w", pady=(0, SPACE["sm"]))

        plan_card = self._create_card(view, "Your plan")
        plan_box = ctk.CTkFrame(plan_card, fg_color="transparent")
        plan_box.pack(fill="x", padx=16, pady=12)

        self.license_tier_badge = ctk.CTkLabel(
            plan_box,
            text="Licensed" if self.licensing.is_pro else f"{self.licensing.days_remaining} days left in your free trial",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=THEME["badge_active_text"] if self.licensing.is_pro else THEME["badge_break_text"],
            fg_color=THEME["badge_active_bg"] if self.licensing.is_pro else THEME["badge_break_bg"],
            corner_radius=RADIUS["pill"],
            padx=12,
            pady=8,
        )
        self.license_tier_badge.pack(side="left")

        hwid_card = self._create_card(view, "This device")
        hwid_box = ctk.CTkFrame(hwid_card, fg_color="transparent")
        hwid_box.pack(fill="x", padx=16, pady=12)

        hwid_lbl = ctk.CTkLabel(
            hwid_box,
            text=self.licensing.machine_id,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=THEME["text_primary"],
        )
        hwid_lbl.pack(side="left")

        copy_btn = ctk.CTkButton(
            hwid_box,
            text="Copy ID",
            width=90,
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            fg_color=THEME["surface_elevated"],
            hover_color=THEME["surface_border"],
            text_color=THEME["text_primary"],
            corner_radius=RADIUS["pill"],
            command=self._copy_hwid,
        )
        copy_btn.pack(side="right")

        act_card = self._create_card(view, "Add a license")
        act_box = ctk.CTkFrame(act_card, fg_color="transparent")
        act_box.pack(fill="x", padx=16, pady=(12, 8))

        self.license_entry = ctk.CTkEntry(
            act_box,
            placeholder_text="Enter your license key",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            height=40,
            corner_radius=RADIUS["input"],
            fg_color=THEME["surface_elevated"],
            border_color=THEME["surface_border"],
            text_color=THEME["text_primary"],
            placeholder_text_color=THEME["text_muted"],
        )
        self.license_entry.pack(side="left", fill="x", expand=True, padx=(0, 12))
        stored_key = self.config.get("license_key", "")
        if stored_key:
            self.license_entry.insert(0, stored_key)

        self.activate_btn = ctk.CTkButton(
            act_box,
            text="Activate",
            width=110,
            height=40,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=THEME["accent_sage"],
            hover_color=THEME["accent_sage_deep"],
            text_color=THEME["on_accent"],
            corner_radius=RADIUS["pill"],
            command=self._on_activate_license,
        )
        self.activate_btn.pack(side="right")

        self.license_feedback_lbl = ctk.CTkLabel(
            act_card,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=THEME["accent_sage_text"],
        )
        self.license_feedback_lbl.pack(anchor="w", padx=16, pady=(0, 14))

        return view

    # ── Helper Builders ────────────────────────────────────────────────────────────
    def _create_card(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=THEME["surface"],
            corner_radius=RADIUS["card"],
            border_width=1,
            border_color=THEME["surface_border"],
        )
        card.pack(fill="both", expand=True, pady=SPACE["xs"], padx=1)

        lbl = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=THEME["text_primary"],
        )
        lbl.pack(anchor="w", padx=SPACE["md"], pady=(SPACE["md"], SPACE["xs"]))
        return card

    # ── Action Handlers ────────────────────────────────────────────────────────────
    def _toggle_engine(self) -> None:
        if self.engine.is_running:
            self.engine.stop()
        else:
            self.engine.start()

    def _on_engine_state_change(self, is_running: bool, state: SchedulerState) -> None:
        """Callback invoked from engine thread when running state changes."""
        self.after(0, lambda: self._update_ui_state(is_running, state))

    def _update_ui_state(self, is_running: bool, state: SchedulerState) -> None:
        """Applies state changes to UI widgets."""
        if is_running:
            if state == SchedulerState.BREAK:
                self.hero_status_badge.configure(
                    text="◒ Rest time",
                    fg_color=THEME["badge_break_bg"],
                    text_color=THEME["badge_break_text"],
                )
                status_text = "◒ Rest time"
                status_color = THEME["text_primary"]
            else:
                self.hero_status_badge.configure(
                    text="● Awake and steady",
                    fg_color=THEME["badge_active_bg"],
                    text_color=THEME["badge_active_text"],
                )
                status_text = "● Awake and steady"
                status_color = THEME["accent_sage_text"]
            self.hero_action_btn.configure(
                state="disabled",
            )
            self.hero_stop_btn.configure(state="normal")
        else:
            self.hero_status_badge.configure(
                text="○ Resting",
                fg_color=THEME["badge_idle_bg"],
                text_color=THEME["badge_idle_text"],
            )
            status_text = "○ Resting"
            status_color = THEME["text_secondary"]
            self.hero_action_btn.configure(
                state="normal",
            )
            self.hero_stop_btn.configure(state="disabled")
        self.header_status.configure(text=status_text, text_color=status_color)

    def _on_activity_pulse(self, description: str) -> None:
        """Appends activity message to live log feed."""
        msg = f"[{time.strftime('%H:%M:%S')}] {description}\n"
        self.after(0, lambda: self._append_log(msg))

    def _append_log(self, text: str) -> None:
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", text)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _start_ui_loop(self) -> None:
        """Refreshes the focus ring and countdown once per second."""
        def _tick():
            scheduler = self.engine.scheduler
            in_break = scheduler.state == SchedulerState.BREAK
            duration = scheduler.break_seconds if in_break else scheduler.work_seconds
            progress = scheduler.get_cycle_progress() if self.engine.is_running else 0.0
            remaining = int(max(0.0, duration * (1.0 - progress)))
            minutes, seconds = divmod(remaining, 60)
            self.live_timer_lbl.configure(text=f"{minutes:02d}:{seconds:02d}")
            phase = "Rest" if in_break else "Focus"
            self.timer_phase_lbl.configure(
                text="Time for a little rest." if in_break else "Focus, at your own pace"
            )
            self.pomodoro_ring.itemconfigure(
                self.pomodoro_time_item,
                text=f"{minutes:02d}:{seconds:02d}",
            )
            self.pomodoro_ring.itemconfigure(self.pomodoro_phase_item, text=phase)
            self._refresh_pomodoro_ring(progress)

            self.after(1000, _tick)

        self.after(1000, _tick)

    @staticmethod
    def _format_activity_interval(seconds: int) -> str:
        if seconds % 60 == 0:
            minutes = seconds // 60
            unit = "minute" if minutes == 1 else "minutes"
            return f"One event every {minutes} {unit}"
        return f"One event every {seconds} seconds"

    def _update_activity_interval(self, val: float) -> None:
        interval = int(round(val / 5) * 5)
        self.activity_interval_slider.set(interval)
        self.activity_interval_val_lbl.configure(
            text=self._format_activity_interval(interval)
        )
        self._on_settings_change()

    def _update_cooldown(self, val: float) -> None:
        self.cooldown_val_lbl.configure(text=f"Wait before resuming: {val:.1f} sec")
        self._on_settings_change()

    def _update_scheduler_durations(self) -> None:
        w = int(self.work_dur_slider.get())
        b = int(self.break_dur_slider.get())
        self.work_dur_lbl.configure(text=f"Focus time: {w} minutes")
        self.break_dur_lbl.configure(text=f"Rest time: {b} minutes")
        self._on_settings_change()

    def _on_settings_change(self) -> None:
        """Saves current widget values to ConfigManager."""
        self.config.set("mode", self.mode_var.get())
        interval = int(self.activity_interval_slider.get())
        self.config.set("activity_interval_seconds", interval)
        self.config.set("interval_min", interval)
        self.config.set("interval_max", interval)
        self.config.set(
            "activity_event_mode",
            next(
                (
                    event_mode
                    for event_mode, label in EVENT_MODE_LABELS.items()
                    if label == self.event_mode_var.get()
                ),
                "move",
            ),
        )
        self.config.set("auto_pause_on_user", bool(self.auto_pause_switch.get()))
        self.config.set("auto_pause_cooldown", round(self.cooldown_slider.get(), 1))
        self.config.set(
            "chrome_tab_switch_enabled", bool(self.chrome_tab_switch.get())
        )

        self.config.set("enable_breaks", bool(self.enable_breaks_switch.get()))
        self.config.set("work_duration_minutes", int(self.work_dur_slider.get()))
        self.config.set("break_duration_minutes", int(self.break_dur_slider.get()))
        self.config.set("notify_on_break", bool(self.notify_break_switch.get()))

        self.config.set("start_minimized", bool(self.minimized_switch.get()))
        self.config.set("close_to_tray", bool(self.close_to_tray_switch.get()))

        selected_mode = {
            "natural": "Glide",
            "jitter": "Nudge",
            "keepalive_only": "Native",
        }.get(self.mode_var.get(), "Glide")
        self._update_mode_buttons(selected_mode)

        # Update active scheduler
        self.engine.scheduler.update_durations(
            work_minutes=int(self.work_dur_slider.get()),
            break_minutes=int(self.break_dur_slider.get()),
            enabled=bool(self.enable_breaks_switch.get()),
        )

    def _on_toggle_startup(self) -> None:
        enable = bool(self.startup_switch.get())
        self.config.set_startup_registry(enable)

    def _copy_hwid(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.licensing.machine_id)
        self._append_log(f"[{time.strftime('%H:%M:%S')}] Device ID copied.\n")

    def _on_activate_license(self) -> None:
        key = self.license_entry.get().strip()
        if not key:
            self.license_feedback_lbl.configure(
                text="Please enter a license key.",
                text_color=THEME["accent_rose_text"],
            )
            return

        self.activate_btn.configure(text="Activating...", state="disabled")

        def _do_activate():
            success, msg = self.licensing.activate(key)
            self.after(0, lambda: self._handle_activation_result(success, msg))

        threading.Thread(target=_do_activate, daemon=True).start()

    def _handle_activation_result(self, success: bool, msg: str) -> None:
        self.activate_btn.configure(text="Activate", state="normal")
        color = THEME["accent_sage_text"] if success else THEME["accent_rose_text"]
        self.license_feedback_lbl.configure(text=msg, text_color=color)

    def _on_license_status_updated(self, tier: LicenseTier, msg: str) -> None:
        plan_text = (
            "Licensed"
            if self.licensing.is_pro
            else f"{self.licensing.days_remaining} days left in your free trial"
        )
        self.plan_indicator.configure(
            text=plan_text
        )
        self.license_tier_badge.configure(
            text=plan_text,
            fg_color=THEME["badge_active_bg"] if self.licensing.is_pro else THEME["badge_break_bg"],
            text_color=THEME["badge_active_text"] if self.licensing.is_pro else THEME["badge_break_text"],
        )

    def _on_close_event(self) -> None:
        """Handles user clicking the window close button."""
        if self.config.get("close_to_tray", True) and self.on_request_hide:
            self.on_request_hide()
        else:
            if self.on_request_quit:
                self.on_request_quit()
            else:
                self.destroy()
