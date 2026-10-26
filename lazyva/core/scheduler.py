"""
Smart break and work interval scheduler.
Provides Pomodoro-style cadence to maintain realistic working patterns.
"""

import enum
import time
from typing import Callable, Optional


class SchedulerState(enum.Enum):
    IDLE = "idle"
    WORKING = "working"
    BREAK = "break"


class BreakScheduler:
    """Manages working cycles and break intervals."""

    def __init__(
        self,
        work_minutes: float = 25.0,
        break_minutes: float = 5.0,
        enabled: bool = True,
        on_state_change: Optional[Callable[[SchedulerState], None]] = None,
    ):
        self.work_seconds = work_minutes * 60.0
        self.break_seconds = break_minutes * 60.0
        self.enabled = enabled
        self.on_state_change = on_state_change

        self.state = SchedulerState.IDLE
        self._current_cycle_start: float = 0.0
        self._total_active_seconds: float = 0.0
        self._breaks_count: int = 0
        self._last_tick: float = 0.0

    def start(self) -> None:
        """Starts a new active work cycle."""
        now = time.time()
        self.state = SchedulerState.WORKING
        self._current_cycle_start = now
        self._last_tick = now
        if self.on_state_change:
            self.on_state_change(self.state)

    def stop(self) -> None:
        """Stops the scheduler and records final elapsed work time."""
        now = time.time()
        if self.state == SchedulerState.WORKING:
            self._total_active_seconds += max(0.0, now - self._last_tick)
        self.state = SchedulerState.IDLE
        if self.on_state_change:
            self.on_state_change(self.state)

    def tick(self) -> SchedulerState:
        """
        Updates internal timers and checks for phase transitions.
        Should be called periodically by the engine loop.
        """
        if self.state == SchedulerState.IDLE:
            return self.state

        now = time.time()
        elapsed_in_cycle = now - self._current_cycle_start

        if self.state == SchedulerState.WORKING:
            self._total_active_seconds += max(0.0, now - self._last_tick)
            self._last_tick = now

            if self.enabled and elapsed_in_cycle >= self.work_seconds:
                # Transition from Work to Break
                self.state = SchedulerState.BREAK
                self._current_cycle_start = now
                self._breaks_count += 1
                if self.on_state_change:
                    self.on_state_change(self.state)

        elif self.state == SchedulerState.BREAK:
            self._last_tick = now
            if elapsed_in_cycle >= self.break_seconds:
                # Break completed, resume work
                self.state = SchedulerState.WORKING
                self._current_cycle_start = now
                if self.on_state_change:
                    self.on_state_change(self.state)

        return self.state

    def update_durations(self, work_minutes: float, break_minutes: float, enabled: bool) -> None:
        """Updates interval settings dynamically."""
        self.work_seconds = max(60.0, work_minutes * 60.0)
        self.break_seconds = max(30.0, break_minutes * 60.0)
        self.enabled = enabled

    @property
    def is_in_break(self) -> bool:
        return self.state == SchedulerState.BREAK

    @property
    def total_active_seconds(self) -> float:
        return self._total_active_seconds

    @property
    def breaks_count(self) -> int:
        return self._breaks_count

    def get_cycle_progress(self) -> float:
        """Returns 0.0 to 1.0 progress through the current work or break period."""
        if self.state == SchedulerState.IDLE:
            return 0.0
        now = time.time()
        elapsed = now - self._current_cycle_start
        target = self.break_seconds if self.state == SchedulerState.BREAK else self.work_seconds
        return min(1.0, max(0.0, elapsed / target))
