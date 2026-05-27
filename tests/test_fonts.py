"""Tests for cross-platform font resolution."""

from __future__ import annotations

from PIL import ImageFont

from core.fonts import (
    DIMENSION_PX,
    LABEL_PX,
    LEGEND_PX,
    TITLE_PX,
    resolve_font,
    resolve_bold_font,
)


def _is_font(obj: object) -> bool:
    """Check whether obj is any kind of PIL font."""
    return hasattr(obj, "getsize") or hasattr(obj, "getlength")


class TestResolveFont:
    def test_returns_image_font(self) -> None:
        """resolve_font should always return a PIL font."""
        font = resolve_font(DIMENSION_PX)
        assert _is_font(font)

    def test_different_sizes(self) -> None:
        """Different sizes should return fonts."""
        for size in (LABEL_PX, DIMENSION_PX, LEGEND_PX, TITLE_PX):
            font = resolve_font(size)
            assert _is_font(font)

    def test_caching(self) -> None:
        """Same size should return cached instance."""
        f1 = resolve_font(DIMENSION_PX)
        f2 = resolve_font(DIMENSION_PX)
        assert f1 is f2

    def test_bold_font_returns_font(self) -> None:
        """Bold font resolver should return a font."""
        font = resolve_bold_font(DIMENSION_PX)
        assert _is_font(font)
