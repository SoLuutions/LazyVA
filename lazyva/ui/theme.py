"""
Modern Dark SaaS Theme and Color Palette for LazyVA.
Engineered for a high-end, premium aesthetic (similar to Raycast, Linear, Discord).
"""

from typing import Dict

THEME: Dict[str, str] = {
    # Backgrounds & Surfaces
    "bg_dark": "#0B0D14",            # Deepest obsidian base
    "surface": "#131722",            # Card and panel surface
    "surface_elevated": "#1A1F2E",   # Hovered or elevated container
    "surface_border": "#262D42",     # Subtle crisp border outline
    "surface_border_focus": "#3B82F6",
    
    # Brand & Accents
    "primary": "#3B82F6",            # Vibrant electric blue
    "primary_hover": "#2563EB",
    "accent_cyan": "#06B6D4",        # Neon cyan pulse
    "accent_cyan_glow": "#0891B2",
    "accent_green": "#10B981",       # Active running green
    "accent_green_hover": "#059669",
    "accent_amber": "#F59E0B",       # Scheduled break amber
    "accent_red": "#EF4444",         # Stop / Danger red
    "accent_red_hover": "#DC2626",
    
    # Typography
    "text_primary": "#F8FAFC",       # High-contrast crisp white
    "text_secondary": "#94A3B8",     # Muted slate secondary
    "text_muted": "#64748B",         # Dim subtle label
    "text_inverse": "#0B0D14",
    
    # Status badges
    "badge_active_bg": "#064E3B",
    "badge_active_text": "#34D399",
    "badge_break_bg": "#78350F",
    "badge_break_text": "#FBBF24",
    "badge_idle_bg": "#1E293B",
    "badge_idle_text": "#94A3B8",
}

def sys_is_windows() -> bool:
    import sys
    return sys.platform == "win32"


FONT_FAMILY = "Segoe UI" if sys_is_windows() else "sans-serif"

