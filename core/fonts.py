"""Cross-platform font resolution with fallback chain and caching.

Follows visual-design-foundations principles:
  - Modular type scale (9/10/12/16 px)
  - System font stack with graceful degradation
  - Cache fonts to avoid repeated I/O
"""

from __future__ import annotations

import functools
from typing import Final

from PIL import ImageFont

# ─── Font stacks by platform ────────────────────────────────────────────────

_WINDOWS_FONTS: Final = ["arial.ttf", "segoeui.ttf", "calibri.ttf"]
_LINUX_FONTS: Final = [
    "DejaVuSans.ttf",
    "LiberationSans-Regular.ttf",
    "FreeSans.ttf",
]
_MACOS_FONTS: Final = [
    "Helvetica.ttc",
    "Arial.ttf",
    ".SFNSText-Regular.ttf",
]

# Ordered fallback chain — most common first
_FONT_CHAIN: Final = _WINDOWS_FONTS + _LINUX_FONTS + _MACOS_FONTS

# ─── Type scale (visual-design-foundations) ─────────────────────────────────

LABEL_PX: Final = 9
DIMENSION_PX: Final = 10
LEGEND_PX: Final = 11
TITLE_PX: Final = 14


@functools.lru_cache(maxsize=16)
def resolve_font(size_px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return a usable TrueType font at the requested pixel size.

    Tries system fonts in order, falling back to PIL's built-in bitmap font
    if nothing else is available.

    Args:
        size_px: Font size in pixels.

    Returns:
        A PIL ImageFont instance.
    """
    for font_name in _FONT_CHAIN:
        try:
            return ImageFont.truetype(font_name, size_px)
        except OSError:
            continue

    return ImageFont.load_default()


def resolve_bold_font(size_px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return a bold font variant if available, otherwise regular."""
    bold_variants = [
        "arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf", "FreeSansBold.ttf",
        "Helvetica-Bold.ttc", "Arial-Bold.ttf",
    ]
    for font_name in bold_variants:
        try:
            return ImageFont.truetype(font_name, size_px)
        except OSError:
            continue
    return resolve_font(size_px)
