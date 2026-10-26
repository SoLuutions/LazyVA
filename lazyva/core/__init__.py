"""Core engine and automation components for LazyVA."""
from .curves import generate_bezier_trajectory
from .keepalive import KeepAliveManager
from .scheduler import BreakScheduler
from .engine import ActivityEngine

__all__ = ["generate_bezier_trajectory", "KeepAliveManager", "BreakScheduler", "ActivityEngine"]
