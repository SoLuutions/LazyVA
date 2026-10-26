"""Soft Meadow and Twilight Meadow color tokens for the LazyVA interface."""

import sys
from typing import Dict, Tuple

ColorPair = Tuple[str, str]

THEME: Dict[str, ColorPair] = {
    "bg_dark": ("#FFF2B4", "#15370D"),
    "surface": ("#FFF8D6", "#25451F"),
    "surface_elevated": ("#F2E6AB", "#365630"),
    "surface_border": ("#D8C77F", "#728E6D"),
    "surface_border_focus": ("#728E6D", "#A9BD9F"),
    "primary": ("#728E6D", "#A9BD9F"),
    "primary_hover": ("#15370D", "#C4D1B7"),
    "accent_cyan": ("#728E6D", "#A9BD9F"),
    "accent_cyan_glow": ("#728E6D", "#A9BD9F"),
    "accent_green": ("#728E6D", "#A9BD9F"),
    "accent_green_hover": ("#5A7555", "#C4D1B7"),
    "accent_amber": ("#E5CD82", "#E5CD82"),
    "accent_red": ("#A75B43", "#E5A68B"),
    "accent_red_hover": ("#884833", "#F1BEA5"),
    "text_primary": ("#15370D", "#FFF2B4"),
    "text_secondary": ("#354D30", "#E5CD82"),
    "text_muted": ("#4A6044", "#D8D0A7"),
    "text_inverse": ("#15370D", "#15370D"),
    "badge_active_bg": ("#4E6848", "#A9BD9F"),
    "badge_active_text": ("#FFF2B4", "#15370D"),
    "badge_break_bg": ("#E5CD82", "#E5CD82"),
    "badge_break_text": ("#15370D", "#15370D"),
    "badge_idle_bg": ("#E5CD82", "#728E6D"),
    "badge_idle_text": ("#15370D", "#FFF2B4"),
    "accent_sage": ("#4E6848", "#A9BD9F"),
    "accent_sage_deep": ("#15370D", "#C4D1B7"),
    "accent_sage_text": ("#354D30", "#DCE7D1"),
    "accent_apricot": ("#E5CD82", "#E5CD82"),
    "accent_apricot_text": ("#15370D", "#15370D"),
    "accent_oat": ("#E5CD82", "#728E6D"),
    "accent_lavender": ("#728E6D", "#A9BD9F"),
    "accent_sky": ("#E5CD82", "#E5CD82"),
    "accent_rose": ("#A75B43", "#E5A68B"),
    "accent_rose_text": ("#884833", "#F1BEA5"),
    "on_accent": ("#FFF2B4", "#15370D"),
}

RADIUS = {"card": 20, "input": 14, "pill": 999}
SPACE = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32}
FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "sans-serif"
DISPLAY_FONT_FAMILY = "Georgia"


def sys_is_windows() -> bool:
    return sys.platform == "win32"


def resolve_color(color: ColorPair, appearance: str) -> str:
    return color[1] if appearance.lower() == "dark" else color[0]
