"""
Core activity simulation engine for LazyVA.
Coordinates mouse movements, Windows keep-alive signals, user detection, and break schedules.
"""

import ctypes
import ctypes.wintypes
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


def _is_chrome_foreground() -> bool:
    """Returns whether the active window belongs to Google Chrome."""
    if sys.platform != "win32":
        return False

    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [
        ctypes.wintypes.HWND,
        ctypes.POINTER(ctypes.wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD
    process_id = ctypes.wintypes.DWORD()
    window = user32.GetForegroundWindow()
    if not window or not user32.GetWindowThreadProcessId(window, ctypes.byref(process_id)):
        return False

    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.argtypes = [
        ctypes.wintypes.DWORD,
        ctypes.wintypes.BOOL,
        ctypes.wintypes.DWORD,
    ]
    kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.DWORD,
        ctypes.wintypes.LPWSTR,
        ctypes.POINTER(ctypes.wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = ctypes.wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
    process = kernel32.OpenProcess(0x1000, False, process_id.value)
    if not process:
        return False

    try:
        image_path = ctypes.create_unicode_buffer(32768)
        path_size = ctypes.wintypes.DWORD(len(image_path))
        if not kernel32.QueryFullProcessImageNameW(
            process, 0, image_path, ctypes.byref(path_size)
        ):
            return False
        return image_path.value.lower().endswith("\\chrome.exe")
    finally:
        kernel32.CloseHandle(process)


def _send_input_event(event: str) -> Tuple[bool, str]:
    """Performs one configured pointer event through PyAutoGUI."""
    if not HAS_PYAUTOGUI:
        return False, f"{event} skipped: PyAutoGUI is unavailable."

    try:
        if event == "click":
            pyautogui.click(button="right")
            return True, "Performed a right-click."
        if event == "scroll":
            amount = random.choice([-3, -2, -1, 1, 2, 3])
            pyautogui.scroll(amount)
            direction = "up" if amount > 0 else "down"
            return True, f"Scrolled {direction} ({abs(amount)} steps)."
    except Exception as error:
        return False, f"{event} failed: {error}"

    return False, f"Unknown activity event: {event}"


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
        self._activity_count = 0

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
        self._activity_count = 0

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
        self._stop_event.wait(1.0)
        last_action_time = time.time()
        next_interval = self._next_action_interval()

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
                self._perform_scheduled_activity()
                last_action_time = time.time()
                next_interval = self._next_action_interval()

            # Responsive sleep in small slices so stopping is instantaneous
            self._stop_event.wait(0.5)

    def _next_action_interval(self) -> float:
        return min(
            300.0,
            max(5.0, float(self.config.get("activity_interval_seconds", 60))),
        )

    def _perform_scheduled_activity(self) -> None:
        """Runs one scheduled action or prompts the user for a manual action."""
        self._activity_count += 1
        if (
            self.config.get("chrome_tab_switch_enabled", False)
            and _is_chrome_foreground()
        ):
            self._perform_chrome_tab_switch()
            return

        event_mode = self.config.get("activity_event_mode", "move")
        event_cycle = {
            "move": ("move",),
            "click": ("click",),
            "scroll": ("scroll",),
            "mixed": ("move", "click", "scroll"),
        }.get(event_mode, ("move",))
        event = event_cycle[(self._activity_count - 1) % len(event_cycle)]

        if event == "move":
            self._perform_activity()
            return

        success, message = _send_input_event(event)
        if success:
            self._total_actions_performed += 1
            self.keepalive.pulse_activity()
        else:
            print(f"[LazyVA] {message}")
        if self.on_activity_pulse:
            self.on_activity_pulse(message)

    def _perform_chrome_tab_switch(self) -> None:
        """Switches one tab in Chrome without performing another activity."""
        if not HAS_PYAUTOGUI:
            message = "Chrome tab switch skipped: PyAutoGUI is unavailable."
            print(f"[LazyVA] {message}")
            if self.on_activity_pulse:
                self.on_activity_pulse(message)
            return

        try:
            pyautogui.hotkey("ctrl", "tab")
        except Exception as error:
            message = f"Chrome tab switch failed: {error}"
            print(f"[LazyVA] {message}")
            if self.on_activity_pulse:
                self.on_activity_pulse(message)
            return

        self._total_actions_performed += 1
        self.keepalive.pulse_activity()
        if self.on_activity_pulse:
            self.on_activity_pulse("Switched to the next Chrome tab (Ctrl+Tab).")

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
