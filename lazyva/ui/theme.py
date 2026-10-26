"""Soft Meadow and Twilight Meadow color tokens for the LazyVA interface."""

import sys
from typing import Dict, Tuple

ColorPair = Tuple[str, str]

THEME: Dict[str, ColorPair] = {
    "bg_dark": ("#FBF7F0", "#5B5878"),
    "surface": ("#FFFDF8", "#6A6788"),
    "surface_elevated": ("#F3EEE3", "#777495"),
    "surface_border": ("#E4DCCB", "#8582A3"),
    "surface_border_focus": ("#6FA586", "#8FC4A4"),
    "primary": ("#A7D3B8", "#B5DDC4"),
    "primary_hover": ("#6FA586", "#8FC4A4"),
    "accent_cyan": ("#BFD8EA", "#C4DDF0"),
    "accent_cyan_glow": ("#BFD8EA", "#C4DDF0"),
    "accent_green": ("#A7D3B8", "#B5DDC4"),
    "accent_green_hover": ("#6FA586", "#8FC4A4"),
    "accent_amber": ("#F6C99B", "#F8D4A8"),
    "accent_red": ("#E9AFAE", "#F2BDC0"),
    "accent_red_hover": ("#D99494", "#E5A5AA"),
    "text_primary": ("#3D3A35", "#F7F2EA"),
    "text_secondary": ("#6F6A60", "#F0ECF5"),
    "text_muted": ("#706B61", "#DED9E8"),
    "text_inverse": ("#2F3B33", "#2E2B40"),
    "badge_active_bg": ("#A7D3B8", "#B5DDC4"),
    "badge_active_text": ("#2F3B33", "#2E2B40"),
    "badge_break_bg": ("#F6C99B", "#F8D4A8"),
    "badge_break_text": ("#2F3B33", "#2E2B40"),
    "badge_idle_bg": ("#D8D1C2", "#CFCADB"),
    "badge_idle_text": ("#3D3A35", "#2E2B40"),
    "accent_sage": ("#A7D3B8", "#B5DDC4"),
    "accent_sage_deep": ("#6FA586", "#8FC4A4"),
    "accent_sage_text": ("#4B725A", "#E2F3E7"),
    "accent_apricot": ("#F6C99B", "#F8D4A8"),
    "accent_apricot_text": ("#855C35", "#FFF0D7"),
    "accent_oat": ("#D8D1C2", "#CFCADB"),
    "accent_lavender": ("#CBBFE6", "#D3C8F0"),
    "accent_sky": ("#BFD8EA", "#C4DDF0"),
    "accent_rose": ("#E9AFAE", "#F2BDC0"),
    "accent_rose_text": ("#9B4F4D", "#FFE9EA"),
    "on_accent": ("#2F3B33", "#2E2B40"),
}

RADIUS = {"card": 20, "input": 14, "pill": 999}
SPACE = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32}
FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "sans-serif"
DISPLAY_FONT_FAMILY = "Georgia"


def sys_is_windows() -> bool:
    return sys.platform == "win32"


def resolve_color(color: ColorPair, appearance: str) -> str:
    return color[1] if appearance.lower() == "dark" else color[0]
