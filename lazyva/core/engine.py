"""
Core activity simulation engine for LazyVA.
Coordinates mouse movements, Windows keep-alive signals, user detection, and break schedules.
"""

import ctypes
import math
import random
import sys
import threading
import time
from typing import Callable, Optional, Tuple

from lazyva.config import ConfigManager
from .curves import generate_bezier_trajectory
from .keepalive import KeepAliveManager
from .scheduler import BreakScheduler, SchedulerState

try:
    import pyautogui
    # Configure pyautogui safety
    pyautogui.FAILSAFE = False
    HAS_PYAUTOGUI = True
except Exception:
    HAS_PYAUTOGUI = False



def _get_screen_size() -> Tuple[int, int]:
    """Returns the primary screen width and height safely."""
    if sys.platform == "win32":
        try:
            # SM_CXSCREEN = 0, SM_CYSCREEN = 1
            w = ctypes.windll.user32.GetSystemMetrics(0)
            h = ctypes.windll.user32.GetSystemMetrics(1)
            if w > 0 and h > 0:
                return (w, h)
        except Exception:
            pass

    if HAS_PYAUTOGUI:
        try:
            return pyautogui.size()
        except Exception:
            pass

    return (1920, 1080)


def _get_cursor_pos() -> Tuple[int, int]:
    """Returns current cursor position (x, y)."""
    if sys.platform == "win32":
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        try:
            pt = POINT()
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                return (pt.x, pt.y)
        except Exception:
            pass

    if HAS_PYAUTOGUI:
        try:
            return pyautogui.position()
        except Exception:
            pass

    return (500, 500)


def _set_cursor_pos(x: int, y: int) -> None:
    """Sets cursor position directly via Windows API or fallback."""
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
            return
        except Exception:
            pass

    if HAS_PYAUTOGUI:
        try:
            pyautogui.moveTo(x, y)
        except Exception:
            pass


class ActivityEngine:
    """
    Main background simulation engine.
    Runs a worker thread that triggers periodic keep-awake pulses and natural mouse movements.
    """

    def __init__(self, config: Optional[ConfigManager] = None):
        self.config = config or ConfigManager()
        self.keepalive = KeepAliveManager()
        self.scheduler = BreakScheduler(
            work_minutes=self.config.get("work_duration_minutes", 25),
            break_minutes=self.config.get("break_duration_minutes", 5),
            enabled=self.config.get("enable_breaks", True),
            on_state_change=self._on_scheduler_state_change,
        )

        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Tracking state
        self._last_user_activity = 0.0
        self._last_engine_action_pos = (0, 0)
        self._total_actions_performed = 0

        # UI Callbacks
        self.on_state_change: Optional[Callable[[bool, SchedulerState], None]] = None
        self.on_activity_pulse: Optional[Callable[[str], None]] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        """Starts the background activity engine."""
        if self._running:
            return True

        self._running = True
        self._stop_event.clear()

        # Update scheduler parameters from current config
        self.scheduler.update_durations(
            work_minutes=self.config.get("work_duration_minutes", 25),
            break_minutes=self.config.get("break_duration_minutes", 5),
            enabled=self.config.get("enable_breaks", True),
        )
        self.scheduler.start()

        # Enable Windows keepalive
        self.keepalive.enable(keep_display_on=True)

        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="LazyVA-Worker")
        self._thread.start()

        if self.on_state_change:
            self.on_state_change(True, self.scheduler.state)

        print("[LazyVA] Activity engine started.")
        return True

    def stop(self) -> None:
        """Stops the background activity engine."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        self.scheduler.stop()
        self.keepalive.disable()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None

        if self.on_state_change:
            self.on_state_change(False, SchedulerState.IDLE)

        print("[LazyVA] Activity engine stopped.")

    def _on_scheduler_state_change(self, state: SchedulerState) -> None:
        if self.on_state_change:
            self.on_state_change(self._running, state)

    def _worker_loop(self) -> None:
        """Main periodic action loop."""
        # Initial cooldown
        time.sleep(1.0)
        last_action_time = time.time()

        while self._running and not self._stop_event.is_set():
            # Advance scheduler tick
            current_sched_state = self.scheduler.tick()

            # If user is in a scheduled break, do not simulate work activity!
            if current_sched_state == SchedulerState.BREAK:
                # Still pulse Windows keepalive so monitor doesn't shut down during break
                self.keepalive.pulse_activity()
                time.sleep(1.0)
                continue

            now = time.time()
            interval_min = float(self.config.get("interval_min", 15))
            interval_max = float(self.config.get("interval_max", 45))
            next_interval = random.uniform(interval_min, interval_max)

            # Check if auto-pause on user interaction is enabled
            if self.config.get("auto_pause_on_user", True):
                cur_x, cur_y = _get_cursor_pos()
                last_x, last_y = self._last_engine_action_pos
                dx = abs(cur_x - last_x)
                dy = abs(cur_y - last_y)

                # If mouse moved more than 15px since LazyVA last moved it, user touched it!
                if (dx > 15 or dy > 15) and last_x != 0 and last_y != 0:
                    self._last_user_activity = now

                cooldown = float(self.config.get("auto_pause_cooldown", 4.0))
                if (now - self._last_user_activity) < cooldown:
                    # User was recently active, delay next action
                    time.sleep(0.5)
                    continue

            # Time to trigger activity
            if (now - last_action_time) >= next_interval:
                self._perform_activity()
                last_action_time = time.time()

            # Responsive sleep in small slices so stopping is instantaneous
            self._stop_event.wait(0.5)

    def _perform_activity(self) -> None:
        """Executes one simulation action based on chosen mode."""
        mode = self.config.get("mode", "natural")
        self.keepalive.pulse_activity()

        screen_w, screen_h = _get_screen_size()
        curr_x, curr_y = _get_cursor_pos()

        # Keep margin from screen edges
        margin = 100
        min_x, max_x = margin, max(screen_w - margin, margin + 50)
        min_y, max_y = margin, max(screen_h - margin, margin + 50)

        if mode == "keepalive_only":
            self._last_engine_action_pos = (curr_x, curr_y)
            self._total_actions_performed += 1
            if self.on_activity_pulse:
                self.on_activity_pulse("Keep-Alive OS Signal pulsed")
            return

        elif mode == "jitter":
            # Micro-nudge: 1-4 pixels, then gentle return
            radius = int(self.config.get("jitter_radius", 15))
            offset_x = random.choice([-1, 1]) * random.randint(2, max(4, radius))
            offset_y = random.choice([-1, 1]) * random.randint(2, max(4, radius))

            target_x = max(min_x, min(max_x, curr_x + offset_x))
            target_y = max(min_y, min(max_y, curr_y + offset_y))

            _set_cursor_pos(target_x, target_y)
            time.sleep(random.uniform(0.1, 0.25))
            _set_cursor_pos(curr_x, curr_y)

            self._last_engine_action_pos = (curr_x, curr_y)
            self._total_actions_performed += 1
            if self.on_activity_pulse:
                self.on_activity_pulse(f"Micro-jitter pulse ({offset_x}px, {offset_y}px)")

        else:  # 'natural'
            # Human-like Bezier curve gliding
            travel_dist = random.randint(80, 300)
            angle = random.uniform(0, 2 * math.pi)
            target_x = int(curr_x + travel_dist * math.cos(angle))
            target_y = int(curr_y + travel_dist * math.sin(angle))

            # Clamp inside screen boundaries
            target_x = max(min_x, min(max_x, target_x))
            target_y = max(min_y, min(max_y, target_y))

            duration = random.uniform(0.4, 0.9)
            speed_mult = float(self.config.get("glide_speed", 1.0))
            if speed_mult > 0:
                duration /= speed_mult

            steps = random.randint(35, 60)
            trajectory = generate_bezier_trajectory(
                (curr_x, curr_y), (target_x, target_y), duration=duration, steps=steps
            )

            for step_x, step_y, delay in trajectory:
                if self._stop_event.is_set():
                    break
                _set_cursor_pos(step_x, step_y)
                time.sleep(delay)

            self._last_engine_action_pos = (target_x, target_y)
            self._total_actions_performed += 1
            if self.on_activity_pulse:
                self.on_activity_pulse(f"Natural glide to ({target_x}, {target_y})")
