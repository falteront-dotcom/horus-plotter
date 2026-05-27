"""Tests for new converter styles: scribble, contour, waves, hexagon."""

from __future__ import annotations

import pytest

from core.converters import (
    contour,
    hexagon,
    scribble,
    waves,
)
from core.paths import Drawing


def _make_grid(width: int = 20, height: int = 15, pattern: str = "gradient") -> list[list[float]]:
    """Create a test brightness grid."""
    if pattern == "gradient":
        return [[x / width for x in range(width)] for _ in range(height)]
    if pattern == "black":
        return [[0.0] * width for _ in range(height)]
    if pattern == "white":
        return [[1.0] * width for _ in range(height)]
    return [[0.5] * width for _ in range(height)]


class TestScribble:
    def test_produces_paths(self) -> None:
        grid = _make_grid(pattern="black")
        d = scribble(grid, spacing=3)
        assert isinstance(d, Drawing)
        assert len(d.paths) > 0

    def test_deterministic_with_seed(self) -> None:
        grid = _make_grid(pattern="gradient")
        d1 = scribble(grid, spacing=3, seed=42)
        d2 = scribble(grid, spacing=3, seed=42)
        assert len(d1.paths) == len(d2.paths)

    def test_white_image_no_paths(self) -> None:
        grid = _make_grid(pattern="white")
        d = scribble(grid, spacing=3, threshold=0.9)
        assert len(d.paths) == 0


class TestContour:
    def test_produces_paths(self) -> None:
        grid = _make_grid(pattern="gradient")
        d = contour(grid, spacing=3)
        assert isinstance(d, Drawing)
        assert len(d.paths) > 0

    def test_more_levels_more_paths(self) -> None:
        grid = _make_grid(pattern="gradient")
        d1 = contour(grid, spacing=3, levels=2)
        d2 = contour(grid, spacing=3, levels=5)
        assert len(d2.paths) >= len(d1.paths)

    def test_white_image_no_paths(self) -> None:
        grid = _make_grid(pattern="white")
        d = contour(grid, spacing=3, threshold=0.9)
        assert len(d.paths) == 0


class TestWaves:
    def test_produces_paths(self) -> None:
        grid = _make_grid(pattern="black")
        d = waves(grid, spacing=3, width_mm=60, height_mm=45)
        assert isinstance(d, Drawing)
        assert len(d.paths) > 0

    def test_waves_are_wavy(self) -> None:
        """Waves should have Y variation, not perfectly straight."""
        grid = _make_grid(pattern="black")
        d = waves(grid, spacing=3, width_mm=60, height_mm=45)
        # Collect all Y coords across all paths
        all_ys = [pt[1] for p in d.paths for pt in p.points]
        if len(all_ys) >= 3:
            assert max(all_ys) - min(all_ys) > 0.1

    def test_white_image_no_paths(self) -> None:
        grid = _make_grid(pattern="white")
        d = waves(grid, spacing=3, width_mm=60, height_mm=45, threshold=0.9)
        assert len(d.paths) == 0


class TestHexagon:
    def test_produces_paths(self) -> None:
        grid = _make_grid(pattern="black")
        d = hexagon(grid, spacing=3)
        assert isinstance(d, Drawing)
        assert len(d.paths) > 0

    def test_hexagons_are_closed(self) -> None:
        """Each hexagon path should be closed (start == end)."""
        grid = _make_grid(pattern="black")
        d = hexagon(grid, spacing=3)
        for p in d.paths:
            assert p.start == p.end

    def test_white_image_no_paths(self) -> None:
        grid = _make_grid(pattern="white")
        d = hexagon(grid, spacing=3, threshold=0.9)
        assert len(d.paths) == 0
