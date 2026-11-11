"""
ARC-LINK Design Tokens
Shared Theme: "NEON GLASS / CYBER-HUD"
Provides centralized color constants, geometry, typography, and visual tokens.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeColors:
    # Deep space background palette
    BG_SPACE_DEEP: str = "#070A12"
    BG_SPACE_DARK: str = "#0D1224"
    BG_SPACE_CARD: str = "#111827"
    BG_SPACE_GLASS: str = "rgba(13, 18, 36, 0.75)"
    BG_SPACE_GLASS_HEADER: str = "rgba(7, 10, 18, 0.85)"
    BG_SPACE_GLASS_CARD: str = "rgba(17, 24, 39, 0.65)"
    BG_SPACE_HOVER: str = "rgba(0, 229, 255, 0.08)"
    BG_SPACE_ACTIVE: str = "rgba(0, 229, 255, 0.16)"

    # Cyberpunk Accent Colors
    CYAN_PRIMARY: str = "#00E5FF"        # Electric Cyan (Primary Accent)
    CYAN_GLOW: str = "rgba(0, 229, 255, 0.45)"
    CYAN_MUTED: str = "rgba(0, 229, 255, 0.20)"

    MAGENTA_ACCENT: str = "#FF2BD6"      # Magenta (Secondary Accent)
    MAGENTA_GLOW: str = "rgba(255, 43, 214, 0.45)"

    GREEN_CONNECTED: str = "#39FF88"     # Acid Green (Connected)
    GREEN_GLOW: str = "rgba(57, 255, 136, 0.50)"

    AMBER_SEARCHING: str = "#FFB020"     # Amber (Searching/Knocking)
    AMBER_GLOW: str = "rgba(255, 176, 32, 0.50)"

    RED_ERROR: str = "#FF3B5C"           # Red (Error/Disconnected)
    RED_GLOW: str = "rgba(255, 59, 92, 0.50)"

    # Neutral and Glass Borders
    BORDER_GLASS: str = "rgba(255, 255, 255, 0.12)"
    BORDER_GLASS_ACTIVE: str = "rgba(0, 229, 255, 0.45)"
    BORDER_GLASS_SUBTLE: str = "rgba(255, 255, 255, 0.06)"

    # Typography
    TEXT_PRIMARY: str = "#F0F6FC"
    TEXT_SECONDARY: str = "#8B949E"
    TEXT_MUTED: str = "#484F58"
    TEXT_ACCENT: str = "#00E5FF"
    TEXT_INVERT: str = "#070A12"


@dataclass(frozen=True)
class ThemeGeometry:
    RADIUS_LG: int = 20
    RADIUS_MD: int = 14
    RADIUS_SM: int = 8
    RADIUS_PILL: int = 999
    BORDER_WIDTH: int = 1
    BORDER_WIDTH_FOCUSED: int = 2


@dataclass(frozen=True)
class ThemeTypography:
    FONT_FAMILY_TITLE: str = "'Orbitron', 'Inter', -apple-system, 'Segoe UI', sans-serif"
    FONT_FAMILY_BODY: str = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    FONT_FAMILY_MONO: str = "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace"


COLORS = ThemeColors()
GEOMETRY = ThemeGeometry()
TYPOGRAPHY = ThemeTypography()
