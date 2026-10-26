"""
Modern Dark SaaS Dashboard GUI for LazyVA.
Built with CustomTkinter for high-DPI scaling, smooth dark mode, and sleek aesthetics.
"""

import os
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image

from lazyva import __app_name__, __version__
from lazyva.config import ConfigManager
from lazyva.core.engine import ActivityEngine

from lazyva.core.scheduler import SchedulerState
from lazyva.licensing.manager import LicenseManager, LicenseTier
from .theme import THEME, sys_is_windows





# Configure CustomTkinter defaults
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    """Primary application window for LazyVA."""

    def __init__(
        self,
        engine: ActivityEngine,
        licensing: LicenseManager,
        config: ConfigManager,
        on_request_hide: Optional[Callable[[], None]] = None,
        on_request_quit: Optional[Callable[[], None]] = None,
    ):
        super().__init__()

        self.engine = engine
        self.licensing = licensing
        self.config = config
        self.on_request_hide = on_request_hide
        self.on_request_quit = on_request_quit

        # Window Setup
        self.title(f"{__app_name__} — Modern Workspace Assistant v{__version__}")
        self.geometry("960x640")
        self.minsize(900, 600)
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
            icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "icon.png"
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
        """Constructs the left-hand navigation sidebar."""
        self.sidebar_frame = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0,
            fg_color=THEME["surface"],
            border_width=1,
            border_color=THEME["surface_border"],
        )
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        # App Brand Header
        header_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=18, pady=(22, 16))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text=__app_name__,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=THEME["text_primary"],
        )
        title_lbl.pack(anchor="w")

        version_badge = ctk.CTkLabel(
            header_frame,
            text=f"v{__version__} • Windows SaaS",
            font=ctk.CTkFont(size=11),
            text_color=THEME["accent_cyan"],
        )
        version_badge.pack(anchor="w")

        # Separator line
        sep = ctk.CTkFrame(self.sidebar_frame, height=1, fg_color=THEME["surface_border"])
        sep.pack(fill="x", padx=18, pady=(0, 16))

        # Nav Buttons
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "⚡ Dashboard"),
            ("engine", "⚙️ Movement Engine"),
            ("scheduler", "⏱️ Smart Breaks"),
            ("hotkeys", "⌨️ Hotkeys & System"),
            ("license", "🔑 SaaS License"),
        ]

        for tab_id, text in nav_items:
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=text,
                anchor="w",
                font=ctk.CTkFont(size=13),
                height=38,
                corner_radius=8,

                fg_color="transparent",
                text_color=THEME["text_secondary"],
                hover_color=THEME["surface_elevated"],
                command=lambda tid=tab_id: self._select_tab(tid),
            )
            btn.pack(fill="x", padx=12, pady=4)
            self.nav_buttons[tab_id] = btn

        # Bottom Sidebar Status
        spacer = ctk.CTkLabel(self.sidebar_frame, text="")
        spacer.pack(fill="both", expand=True)

        status_box = ctk.CTkFrame(
            self.sidebar_frame,
            fg_color=THEME["surface_elevated"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["surface_border"],
        )
        status_box.pack(fill="x", padx=12, pady=(0, 16))

        self.sidebar_status_dot = ctk.CTkLabel(
            status_box,
            text="●",
            font=ctk.CTkFont(size=14),
            text_color=THEME["accent_green"] if self.engine.is_running else THEME["text_muted"],
        )
        self.sidebar_status_dot.pack(side="left", padx=(10, 4), pady=8)

        self.sidebar_status_txt = ctk.CTkLabel(
            status_box,
            text="Running" if self.engine.is_running else "Idle",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["text_primary"],
        )
        self.sidebar_status_txt.pack(side="left", padx=(0, 10), pady=8)

    def _build_content_area(self) -> None:
        """Constructs right-hand dynamic view area."""
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(side="right", fill="both", expand=True, padx=24, pady=20)

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
        """Switches active view and updates sidebar styling."""
        self._active_tab = tab_id
        for tid, frame in self.tabs.items():
            if tid == tab_id:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                btn.configure(
                    fg_color=THEME["primary"],
                    text_color=THEME["text_primary"],
                    hover_color=THEME["primary_hover"],
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=THEME["text_secondary"],
                    hover_color=THEME["surface_elevated"],
                )

    # ── View 1: Dashboard ──────────────────────────────────────────────────────────
    def _create_dashboard_view(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.content_container, fg_color="transparent")

        # Hero Card: Status & Big Action Button
        hero = ctk.CTkFrame(
            view,
            fg_color=THEME["surface"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["surface_border"],
        )
        hero.pack(fill="x", pady=(0, 16), padx=2)

        hero_top = ctk.CTkFrame(hero, fg_color="transparent")
        hero_top.pack(fill="x", padx=20, pady=(18, 10))

        self.hero_status_badge = ctk.CTkLabel(
            hero_top,
            text="⚪ IDLE & READY",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["badge_idle_text"],
            fg_color=THEME["badge_idle_bg"],
            corner_radius=6,
            padx=10,
            pady=4,
        )
        self.hero_status_badge.pack(side="left")

        self.plan_indicator = ctk.CTkLabel(
            hero_top,
            text="PRO LIFETIME" if self.licensing.is_pro else f"FREE TRIAL ({self.licensing.days_remaining}d)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["accent_cyan"],
        )
        self.plan_indicator.pack(side="right")

        # Big Timer
        timer_box = ctk.CTkFrame(hero, fg_color="transparent")
        timer_box.pack(fill="x", padx=20, pady=(0, 12))

        self.live_timer_lbl = ctk.CTkLabel(
            timer_box,
            text="00:00:00",
            font=ctk.CTkFont(family="Consolas" if sys_is_windows() else "monospace", size=46, weight="bold"),
            text_color=THEME["text_primary"],
        )
        self.live_timer_lbl.pack(anchor="w")

        timer_sub = ctk.CTkLabel(
            timer_box,
            text="Total session active working time today",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_muted"],
        )
        timer_sub.pack(anchor="w")

        # Start / Stop Toggle Button
        self.hero_action_btn = ctk.CTkButton(
            hero,
            text="START ASSISTANT (F9)",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=46,
            corner_radius=10,
            fg_color=THEME["accent_green"],
            hover_color=THEME["accent_green_hover"],
            command=self._toggle_engine,
        )
        self.hero_action_btn.pack(fill="x", padx=20, pady=(4, 18))

        # Metrics Row (4 Cards)
        metrics_row = ctk.CTkFrame(view, fg_color="transparent")
        metrics_row.pack(fill="x", pady=(0, 16))
        metrics_row.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="metric")

        self.metric_mode_val = self._create_metric_card(metrics_row, 0, "Simulation Mode", "Natural Bezier")
        self.metric_interval_val = self._create_metric_card(
            metrics_row, 1, "Interval Delay", f"{self.config.get('interval_min')}s - {self.config.get('interval_max')}s"
        )
        self.metric_breaks_val = self._create_metric_card(metrics_row, 2, "Breaks Completed", "0")
        self.metric_pause_val = self._create_metric_card(
            metrics_row, 3, "Auto-Pause", "Active" if self.config.get("auto_pause_on_user") else "Off"
        )

        # Activity Log Card
        log_card = ctk.CTkFrame(
            view,
            fg_color=THEME["surface"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["surface_border"],
        )
        log_card.pack(fill="both", expand=True, padx=2)

        log_header = ctk.CTkFrame(log_card, fg_color="transparent")
        log_header.pack(fill="x", padx=16, pady=(12, 6))

        log_title = ctk.CTkLabel(
            log_header,
            text="Live Activity Feed",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME["text_primary"],
        )
        log_title.pack(side="left")

        self.log_textbox = ctk.CTkTextbox(
            log_card,
            font=ctk.CTkFont(family="Consolas" if sys_is_windows() else "monospace", size=11),
            fg_color=THEME["bg_dark"],
            text_color=THEME["text_secondary"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["surface_border"],
        )
        self.log_textbox.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.log_textbox.insert("end", f"[{time.strftime('%H:%M:%S')}] LazyVA initialized and ready.\n")
        self.log_textbox.configure(state="disabled")

        return view

    def _create_metric_card(self, parent, col: int, title: str, initial_val: str) -> ctk.CTkLabel:
        card = ctk.CTkFrame(
            parent,
            fg_color=THEME["surface"],
            corner_radius=10,
            border_width=1,
            border_color=THEME["surface_border"],
        )
        card.grid(row=0, column=col, padx=4, sticky="nsew")

        lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11), text_color=THEME["text_muted"])
        lbl_title.pack(anchor="w", padx=12, pady=(10, 2))

        lbl_val = ctk.CTkLabel(
            card, text=initial_val, font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["text_primary"]
        )
        lbl_val.pack(anchor="w", padx=12, pady=(0, 10))
        return lbl_val

    # ── View 2: Movement Engine Settings ──────────────────────────────────────────
    def _create_engine_view(self) -> ctk.CTkScrollableFrame:
        view = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="transparent",
            scrollbar_button_color=THEME["surface_elevated"],
        )

        title = ctk.CTkLabel(view, text="Movement & Keep-Awake Settings", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", pady=(0, 12))

        # Mode Selection Card
        mode_card = self._create_card(view, "Simulation Mode")
        self.mode_var = ctk.StringVar(value=self.config.get("mode", "natural"))

        modes = [
            ("natural", "Natural Bezier Glide", "Simulates organic human hand movement with easing and micro-curves."),
            ("jitter", "Micro-Jitter Nudge", "Moves 1-4 pixels then returns instantly. Barely perceptible."),
            ("keepalive_only", "Keep-Awake API Only", "Native Windows OS sleep prevention. No cursor movement whatsoever."),
        ]

        for val, name, desc in modes:
            r_frame = ctk.CTkFrame(mode_card, fg_color="transparent")
            r_frame.pack(fill="x", padx=16, pady=6)
            rb = ctk.CTkRadioButton(
                r_frame,
                text=name,
                variable=self.mode_var,
                value=val,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=self._on_settings_change,
            )
            rb.pack(anchor="w")
            d_lbl = ctk.CTkLabel(r_frame, text=desc, font=ctk.CTkFont(size=11), text_color=THEME["text_muted"])
            d_lbl.pack(anchor="w", padx=(28, 0))

        # Intervals Card
        interval_card = self._create_card(view, "Interval Timing")

        self.min_interval_val_lbl = ctk.CTkLabel(
            interval_card,
            text=f"Min Delay: {self.config.get('interval_min')}s",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.min_interval_val_lbl.pack(anchor="w", padx=16, pady=(8, 0))

        self.min_slider = ctk.CTkSlider(
            interval_card,
            from_=5,
            to=60,
            number_of_steps=55,
            command=self._update_min_interval,
        )
        self.min_slider.set(self.config.get("interval_min", 15))
        self.min_slider.pack(fill="x", padx=16, pady=(4, 12))

        self.max_interval_val_lbl = ctk.CTkLabel(
            interval_card,
            text=f"Max Delay: {self.config.get('interval_max')}s",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.max_interval_val_lbl.pack(anchor="w", padx=16, pady=(4, 0))

        self.max_slider = ctk.CTkSlider(
            interval_card,
            from_=15,
            to=180,
            number_of_steps=165,
            command=self._update_max_interval,
        )
        self.max_slider.set(self.config.get("interval_max", 45))
        self.max_slider.pack(fill="x", padx=16, pady=(4, 16))

        # Auto-Pause Card
        pause_card = self._create_card(view, "Human Interaction Detection")

        self.auto_pause_switch = ctk.CTkSwitch(
            pause_card,
            text="Auto-pause when physical mouse movement is detected",
            font=ctk.CTkFont(size=13),
            command=self._on_settings_change,
        )
        if self.config.get("auto_pause_on_user", True):
            self.auto_pause_switch.select()
        self.auto_pause_switch.pack(anchor="w", padx=16, pady=(12, 8))

        self.cooldown_val_lbl = ctk.CTkLabel(
            pause_card,
            text=f"Inactivity Cooldown: {self.config.get('auto_pause_cooldown')}s",
            font=ctk.CTkFont(size=12),
        )
        self.cooldown_val_lbl.pack(anchor="w", padx=16, pady=(4, 0))

        self.cooldown_slider = ctk.CTkSlider(
            pause_card,
            from_=1.0,
            to=15.0,
            number_of_steps=28,
            command=self._update_cooldown,
        )
        self.cooldown_slider.set(self.config.get("auto_pause_cooldown", 4.0))
        self.cooldown_slider.pack(fill="x", padx=16, pady=(4, 16))

        return view

    # ── View 3: Smart Breaks (Scheduler) ──────────────────────────────────────────
    def _create_scheduler_view(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.content_container, fg_color="transparent")

        title = ctk.CTkLabel(view, text="Smart Pomodoro & Break Scheduler", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", pady=(0, 12))

        sched_card = self._create_card(view, "Automated Work/Break Cycles")

        self.enable_breaks_switch = ctk.CTkSwitch(
            sched_card,
            text="Enable Smart Breaks",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_settings_change,
        )
        if self.config.get("enable_breaks", True):
            self.enable_breaks_switch.select()
        self.enable_breaks_switch.pack(anchor="w", padx=16, pady=(12, 10))

        # Work Duration
        self.work_dur_lbl = ctk.CTkLabel(
            sched_card,
            text=f"Work Duration: {self.config.get('work_duration_minutes')} minutes",
            font=ctk.CTkFont(size=12),
        )
        self.work_dur_lbl.pack(anchor="w", padx=16, pady=(6, 0))

        self.work_dur_slider = ctk.CTkSlider(
            sched_card,
            from_=10,
            to=90,
            number_of_steps=16,
            command=lambda val: self._update_scheduler_durations(),
        )
        self.work_dur_slider.set(self.config.get("work_duration_minutes", 25))
        self.work_dur_slider.pack(fill="x", padx=16, pady=(4, 14))

        # Break Duration
        self.break_dur_lbl = ctk.CTkLabel(
            sched_card,
            text=f"Break Duration: {self.config.get('break_duration_minutes')} minutes",
            font=ctk.CTkFont(size=12),
        )
        self.break_dur_lbl.pack(anchor="w", padx=16, pady=(4, 0))

        self.break_dur_slider = ctk.CTkSlider(
            sched_card,
            from_=1,
            to=20,
            number_of_steps=19,
            command=lambda val: self._update_scheduler_durations(),
        )
        self.break_dur_slider.set(self.config.get("break_duration_minutes", 5))
        self.break_dur_slider.pack(fill="x", padx=16, pady=(4, 16))

        # Notification toggle
        self.notify_break_switch = ctk.CTkSwitch(
            sched_card,
            text="Notify with desktop alert when break starts",
            font=ctk.CTkFont(size=13),
            command=self._on_settings_change,
        )
        if self.config.get("notify_on_break", True):
            self.notify_break_switch.select()
        self.notify_break_switch.pack(anchor="w", padx=16, pady=(0, 16))

        return view

    # ── View 4: Hotkeys & System ──────────────────────────────────────────────────
    def _create_hotkeys_view(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.content_container, fg_color="transparent")

        title = ctk.CTkLabel(view, text="Hotkeys & Windows Integration", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", pady=(0, 12))

        # Hotkeys
        hk_card = self._create_card(view, "Global Keyboard Shortcuts")

        hk_grid = ctk.CTkFrame(hk_card, fg_color="transparent")
        hk_grid.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(hk_grid, text="Start Assistant:", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", pady=6)
        ctk.CTkLabel(hk_grid, text="F9", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["accent_cyan"]).grid(
            row=0, column=1, sticky="w", padx=16, pady=6
        )

        ctk.CTkLabel(hk_grid, text="Stop / Pause Assistant:", font=ctk.CTkFont(size=13)).grid(row=1, column=0, sticky="w", pady=6)
        ctk.CTkLabel(hk_grid, text="F10", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["accent_amber"]).grid(
            row=1, column=1, sticky="w", padx=16, pady=6
        )

        ctk.CTkLabel(hk_grid, text="Exit LazyVA Completely:", font=ctk.CTkFont(size=13)).grid(row=2, column=0, sticky="w", pady=6)
        ctk.CTkLabel(hk_grid, text="F11", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["accent_red"]).grid(
            row=2, column=1, sticky="w", padx=16, pady=6
        )

        # Windows Integration Card
        win_card = self._create_card(view, "Windows System Behavior")

        self.startup_switch = ctk.CTkSwitch(
            win_card,
            text="Launch LazyVA automatically on Windows startup",
            font=ctk.CTkFont(size=13),
            command=self._on_toggle_startup,
        )
        if self.config.get("launch_on_startup", False):
            self.startup_switch.select()
        self.startup_switch.pack(anchor="w", padx=16, pady=(12, 8))

        self.minimized_switch = ctk.CTkSwitch(
            win_card,
            text="Start minimized directly to the System Tray",
            font=ctk.CTkFont(size=13),
            command=self._on_settings_change,
        )
        if self.config.get("start_minimized", False):
            self.minimized_switch.select()
        self.minimized_switch.pack(anchor="w", padx=16, pady=(4, 8))

        self.close_to_tray_switch = ctk.CTkSwitch(
            win_card,
            text="Minimize to System Tray when closing the window",
            font=ctk.CTkFont(size=13),
            command=self._on_settings_change,
        )
        if self.config.get("close_to_tray", True):
            self.close_to_tray_switch.select()
        self.close_to_tray_switch.pack(anchor="w", padx=16, pady=(4, 16))

        return view

    # ── View 5: License & SaaS Activation ─────────────────────────────────────────
    def _create_license_view(self) -> ctk.CTkFrame:
        view = ctk.CTkFrame(self.content_container, fg_color="transparent")

        title = ctk.CTkLabel(view, text="SaaS Licensing & Device Activation", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(anchor="w", pady=(0, 12))

        # Current Plan Card
        plan_card = self._create_card(view, "Current Subscription / Plan")
        plan_box = ctk.CTkFrame(plan_card, fg_color="transparent")
        plan_box.pack(fill="x", padx=16, pady=12)

        self.license_tier_badge = ctk.CTkLabel(
            plan_box,
            text="PRO LIFETIME" if self.licensing.is_pro else f"FREE TRIAL ({self.licensing.days_remaining} Days Remaining)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["badge_active_text"] if self.licensing.is_pro else THEME["badge_break_text"],
            fg_color=THEME["badge_active_bg"] if self.licensing.is_pro else THEME["badge_break_bg"],
            corner_radius=6,
            padx=12,
            pady=6,
        )
        self.license_tier_badge.pack(side="left")

        # Hardware ID Card
        hwid_card = self._create_card(view, "Registered Device Hardware Fingerprint (HWID)")
        hwid_box = ctk.CTkFrame(hwid_card, fg_color="transparent")
        hwid_box.pack(fill="x", padx=16, pady=12)

        hwid_lbl = ctk.CTkLabel(
            hwid_box,
            text=self.licensing.machine_id,
            font=ctk.CTkFont(family="Consolas" if sys_is_windows() else "monospace", size=13, weight="bold"),
            text_color=THEME["text_primary"],
        )
        hwid_lbl.pack(side="left")

        copy_btn = ctk.CTkButton(
            hwid_box,
            text="Copy HWID",
            width=90,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=THEME["surface_elevated"],
            hover_color=THEME["surface_border"],
            command=self._copy_hwid,
        )
        copy_btn.pack(side="right")

        # License Key Activation Card
        act_card = self._create_card(view, "Activate License Key")
        act_box = ctk.CTkFrame(act_card, fg_color="transparent")
        act_box.pack(fill="x", padx=16, pady=(12, 8))

        self.license_entry = ctk.CTkEntry(
            act_box,
            placeholder_text="Enter license key (e.g. LVA-PRO-XXXXX-XXXXX-XXXXX)",
            font=ctk.CTkFont(family="Consolas" if sys_is_windows() else "monospace", size=12),
            height=40,
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
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=THEME["primary"],
            hover_color=THEME["primary_hover"],
            command=self._on_activate_license,
        )
        self.activate_btn.pack(side="right")

        self.license_feedback_lbl = ctk.CTkLabel(
            act_card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=THEME["accent_green"],
        )
        self.license_feedback_lbl.pack(anchor="w", padx=16, pady=(0, 14))

        return view

    # ── Helper Builders ────────────────────────────────────────────────────────────
    def _create_card(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=THEME["surface"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["surface_border"],
        )
        card.pack(fill="x", pady=6, padx=2)

        lbl = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_primary"])
        lbl.pack(anchor="w", padx=16, pady=(12, 4))
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
                    text="🟡 IN SMART BREAK",
                    fg_color=THEME["badge_break_bg"],
                    text_color=THEME["badge_break_text"],
                )
            else:
                self.hero_status_badge.configure(
                    text="🟢 ACTIVE & WORKING",
                    fg_color=THEME["badge_active_bg"],
                    text_color=THEME["badge_active_text"],
                )
            self.hero_action_btn.configure(
                text="STOP ASSISTANT (F10)",
                fg_color=THEME["accent_red"],
                hover_color=THEME["accent_red_hover"],
            )
            self.sidebar_status_dot.configure(text_color=THEME["accent_green"])
            self.sidebar_status_txt.configure(text="Running")
        else:
            self.hero_status_badge.configure(
                text="⚪ IDLE & READY",
                fg_color=THEME["badge_idle_bg"],
                text_color=THEME["badge_idle_text"],
            )
            self.hero_action_btn.configure(
                text="START ASSISTANT (F9)",
                fg_color=THEME["accent_green"],
                hover_color=THEME["accent_green_hover"],
            )
            self.sidebar_status_dot.configure(text_color=THEME["text_muted"])
            self.sidebar_status_txt.configure(text="Idle")

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
        """Updates live timer and metrics every second."""
        def _tick():
            if self.engine.is_running:
                total_sec = int(self.engine.scheduler.total_active_seconds)
                hrs = total_sec // 3600
                mins = (total_sec % 3600) // 60
                secs = total_sec % 60
                self.live_timer_lbl.configure(text=f"{hrs:02d}:{mins:02d}:{secs:02d}")
                self.metric_breaks_val.configure(text=str(self.engine.scheduler.breaks_count))

            self.after(1000, _tick)

        self.after(1000, _tick)

    def _update_min_interval(self, val: float) -> None:
        v = int(val)
        self.min_interval_val_lbl.configure(text=f"Min Delay: {v}s")
        # Ensure max >= min
        if self.max_slider.get() < v:
            self.max_slider.set(v + 5)
            self.max_interval_val_lbl.configure(text=f"Max Delay: {v + 5}s")
        self._on_settings_change()

    def _update_max_interval(self, val: float) -> None:
        v = int(val)
        # Ensure max >= min
        if v < self.min_slider.get():
            v = int(self.min_slider.get()) + 5
            self.max_slider.set(v)
        self.max_interval_val_lbl.configure(text=f"Max Delay: {v}s")
        self._on_settings_change()

    def _update_cooldown(self, val: float) -> None:
        self.cooldown_val_lbl.configure(text=f"Inactivity Cooldown: {val:.1f}s")
        self._on_settings_change()

    def _update_scheduler_durations(self) -> None:
        w = int(self.work_dur_slider.get())
        b = int(self.break_dur_slider.get())
        self.work_dur_lbl.configure(text=f"Work Duration: {w} minutes")
        self.break_dur_lbl.configure(text=f"Break Duration: {b} minutes")
        self._on_settings_change()

    def _on_settings_change(self) -> None:
        """Saves current widget values to ConfigManager."""
        self.config.set("mode", self.mode_var.get())
        self.config.set("interval_min", int(self.min_slider.get()))
        self.config.set("interval_max", int(self.max_slider.get()))
        self.config.set("auto_pause_on_user", bool(self.auto_pause_switch.get()))
        self.config.set("auto_pause_cooldown", round(self.cooldown_slider.get(), 1))

        self.config.set("enable_breaks", bool(self.enable_breaks_switch.get()))
        self.config.set("work_duration_minutes", int(self.work_dur_slider.get()))
        self.config.set("break_duration_minutes", int(self.break_dur_slider.get()))
        self.config.set("notify_on_break", bool(self.notify_break_switch.get()))

        self.config.set("start_minimized", bool(self.minimized_switch.get()))
        self.config.set("close_to_tray", bool(self.close_to_tray_switch.get()))

        # Update dashboard metrics
        self.metric_mode_val.configure(
            text="Natural Bezier"
            if self.mode_var.get() == "natural"
            else "Micro-Jitter"
            if self.mode_var.get() == "jitter"
            else "Keep-Alive Only"
        )
        self.metric_interval_val.configure(
            text=f"{int(self.min_slider.get())}s - {int(self.max_slider.get())}s"
        )
        self.metric_pause_val.configure(text="Active" if self.auto_pause_switch.get() else "Off")

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
        self._append_log(f"[{time.strftime('%H:%M:%S')}] Copied Machine HWID to clipboard.\n")

    def _on_activate_license(self) -> None:
        key = self.license_entry.get().strip()
        if not key:
            self.license_feedback_lbl.configure(text="Please enter a license key.", text_color=THEME["accent_red"])
            return

        self.activate_btn.configure(text="Activating...", state="disabled")

        def _do_activate():
            success, msg = self.licensing.activate(key)
            self.after(0, lambda: self._handle_activation_result(success, msg))

        threading.Thread(target=_do_activate, daemon=True).start()

    def _handle_activation_result(self, success: bool, msg: str) -> None:
        self.activate_btn.configure(text="Activate", state="normal")
        color = THEME["accent_green"] if success else THEME["accent_red"]
        self.license_feedback_lbl.configure(text=msg, text_color=color)

    def _on_license_status_updated(self, tier: LicenseTier, msg: str) -> None:
        self.plan_indicator.configure(
            text="PRO LIFETIME" if self.licensing.is_pro else f"FREE TRIAL ({self.licensing.days_remaining}d)"
        )
        self.license_tier_badge.configure(
            text="PRO LIFETIME" if self.licensing.is_pro else f"FREE TRIAL ({self.licensing.days_remaining} Days Remaining)",
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
