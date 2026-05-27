"""Tests for core.converters — all 7 styles + preprocessing."""

import pytest
from PIL import Image
import numpy as np

from core.converters import (
    hatching, cross_hatching, halftone, stipple, spiral,
    flow_field, meandering, edge_detect,
    dots, concentric, woodcut, zigzag, tiles,
    CONVERTERS,
)
from core.exceptions import ConverterError
from core.paths import Drawing


def _make_grid(width=20, height=15, pattern="gradient"):
    """Create a test brightness grid."""
    grid = []
    for y in range(height):
        row = []
        for x in range(width):
            if pattern == "gradient":
                row.append(x / width)  # left=black, right=white
            elif pattern == "circle":
                cx, cy = width / 2, height / 2
                dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                max_dist = (cx ** 2 + cy ** 2) ** 0.5
                row.append(min(1.0, dist / max_dist))
            elif pattern == "white":
                row.append(1.0)
            elif pattern == "black":
                row.append(0.0)
            else:
                row.append(0.5)
        grid.append(row)
    return grid


class TestHatching:
    def test_produces_paths(self):
        grid = _make_grid(pattern="gradient")
        d = hatching(grid, spacing=3, threshold=0.15)
        assert isinstance(d, Drawing)
        assert len(d.paths) > 0

    def test_white_image_no_paths(self):
        grid = _make_grid(pattern="white")
        d = hatching(grid, spacing=3, threshold=0.15)
        assert len(d.paths) == 0

    def test_black_image_many_paths(self):
        grid = _make_grid(pattern="black")
        d = hatching(grid, spacing=3, threshold=0.15)
        assert len(d.paths) > 5

    def test_threshold_affects_output(self):
        grid = _make_grid(pattern="gradient")
        d_low = hatching(grid, spacing=3, threshold=0.05)
        d_high = hatching(grid, spacing=3, threshold=0.45)
        assert len(d_low.paths) > len(d_high.paths)

    def test_cross_hatch_adds_paths(self):
        grid = _make_grid(pattern="black")
        d_no_cross = hatching(grid, spacing=3, cross_hatch=False)
        d_cross = hatching(grid, spacing=3, cross_hatch=True)
        assert len(d_cross.paths) > len(d_no_cross.paths)


class TestCrossHatching:
    def test_produces_paths(self):
        grid = _make_grid(pattern="gradient")
        d = cross_hatching(grid, spacing=3, threshold=0.15, angles=[0, 45])
        assert len(d.paths) > 0

    def test_more_angles_more_paths(self):
        grid = _make_grid(pattern="black")
        d1 = cross_hatching(grid, spacing=3, angles=[0])
        d2 = cross_hatching(grid, spacing=3, angles=[0, 45])
        d3 = cross_hatching(grid, spacing=3, angles=[0, 45, 90])
        assert len(d1.paths) < len(d2.paths) < len(d3.paths)


class TestHalftone:
    def test_produces_paths(self):
        grid = _make_grid(pattern="gradient")
        d = halftone(grid, spacing=3)
        assert len(d.paths) > 0

    def test_white_image_no_paths(self):
        grid = _make_grid(pattern="white")
        d = halftone(grid, spacing=3, threshold=0.1)
        assert len(d.paths) == 0

    def test_circles_are_closed(self):
        grid = _make_grid(pattern="black")
        d = halftone(grid, spacing=3, segments=8)
        for p in d.paths:
            assert p.start == p.end  # circle is closed


class TestStipple:
    def test_produces_paths(self):
        grid = _make_grid(pattern="gradient")
        d = stipple(grid, spacing=3)
        assert len(d.paths) > 0

    def test_deterministic_with_seed(self):
        grid = _make_grid(pattern="gradient")
        d1 = stipple(grid, spacing=3, seed=42)
        d2 = stipple(grid, spacing=3, seed=42)
        assert len(d1.paths) == len(d2.paths)


class TestSpiral:
    def test_produces_paths(self):
        grid = _make_grid(pattern="gradient")
        d = spiral(grid, spacing=3, width_mm=60, height_mm=45)
        assert len(d.paths) > 0


class TestFlowField:
    def test_produces_paths(self):
        grid = _make_grid(pattern="circle")
        d = flow_field(grid, spacing=3, width_mm=60, height_mm=45)
        assert len(d.paths) > 0

    def test_white_image_no_paths(self):
        grid = _make_grid(pattern="white")
        d = flow_field(grid, spacing=3, width_mm=60, height_mm=45, threshold=0.15)
        assert len(d.paths) == 0


class TestMeandering:
    def test_produces_paths(self):
        grid = _make_grid(pattern="gradient")
        d = meandering(grid, spacing=3, width_mm=60, height_mm=45)
        assert len(d.paths) > 0

    def test_wavy_not_straight(self):
        grid = _make_grid(pattern="black")
        d = meandering(grid, spacing=3, width_mm=60, height_mm=45, wave_amplitude=2.0)
        # Paths should have Y variation (not perfectly horizontal)
        for p in d.paths:
            if len(p.points) >= 3:
                ys = [pt[1] for pt in p.points]
                assert max(ys) - min(ys) > 0.1  # some wave


class TestConverterRegistry:
    @pytest.mark.parametrize("style_name", list(CONVERTERS.keys()))
    def test_each_style_is_callable(self, style_name: str) -> None:
        """Every registered style should be a callable function."""
        assert callable(CONVERTERS[style_name])

    def test_all_styles_registered(self) -> None:
        expected = {"hatching", "cross-hatching", "halftone", "stipple",
                    "spiral", "flow-field", "meandering", "edge-detect",
                    "dots", "concentric", "woodcut", "zigzag", "tiles",
                    "scribble", "contour", "waves", "hexagon"}
        assert set(CONVERTERS.keys()) == expected


class TestEdgeDetect:
    def test_produces_paths(self):
        # Need a grid with a sharp edge — gradient is too smooth
        grid = []
        for y in range(20):
            row = []
            for x in range(20):
                row.append(0.0 if x < 10 else 1.0)
            grid.append(row)
        d = edge_detect(grid, spacing=3)
        assert isinstance(d, Drawing)
        assert len(d.paths) > 0

    def test_uniform_image_no_edges(self):
        grid = _make_grid(pattern="white")
        d = edge_detect(grid, spacing=3)
        assert len(d.paths) == 0


class TestDots:
    def test_produces_paths(self):
        grid = _make_grid(pattern="black")
        d = dots(grid, spacing=3)
        assert len(d.paths) > 0

    def test_white_image_no_paths(self):
        grid = _make_grid(pattern="white")
        d = dots(grid, spacing=3, threshold=0.1)
        assert len(d.paths) == 0


_SIZE_STYLES = ("spiral", "flow-field", "meandering", "concentric", "waves")


class TestAllConverters:
    """Parametrized tests that run against every converter."""

    @pytest.mark.parametrize("style_name,converter", CONVERTERS.items())
    def test_converter_returns_drawing(self, style_name: str, converter) -> None:
        """Every converter must return a Drawing instance."""
        grid = _make_grid(pattern="black")
        if style_name in _SIZE_STYLES:
            d = converter(grid, spacing=3, width_mm=60, height_mm=45)
        elif style_name == "cross-hatching":
            d = converter(grid, spacing=3, angles=[0])
        else:
            d = converter(grid, spacing=3)
        assert isinstance(d, Drawing)

    @pytest.mark.parametrize("style_name,converter", CONVERTERS.items())
    def test_white_grid_produces_no_paths(self, style_name: str, converter) -> None:
        """Every converter should produce no paths on a fully white grid."""
        grid = _make_grid(pattern="white")
        if style_name in _SIZE_STYLES:
            d = converter(grid, spacing=3, width_mm=60, height_mm=45, threshold=0.9)
        elif style_name == "cross-hatching":
            d = converter(grid, spacing=3, angles=[0], threshold=0.9)
        else:
            d = converter(grid, spacing=3, threshold=0.9)
        assert len(d.paths) == 0

    @pytest.mark.parametrize(
        "style_name,converter",
        [(n, c) for n, c in CONVERTERS.items() if n != "edge-detect"],
    )
    def test_black_grid_produces_paths(self, style_name: str, converter) -> None:
        """Most converters should produce at least one path on a fully black grid.

        Edge-detect is excluded because it requires brightness gradients.
        """
        grid = _make_grid(pattern="black")
        if style_name in _SIZE_STYLES:
            d = converter(grid, spacing=3, width_mm=60, height_mm=45)
        elif style_name == "cross-hatching":
            d = converter(grid, spacing=3, angles=[0])
        else:
            d = converter(grid, spacing=3)
        assert len(d.paths) > 0

    def test_edge_detect_needs_gradient(self) -> None:
        """Edge-detect requires a gradient to produce paths."""
        from core.converters import edge_detect
        # Uniform black grid → no edges
        black = _make_grid(pattern="black")
        assert len(edge_detect(black, spacing=3).paths) == 0
        # Grid with sharp edge → edges found
        edge_grid = []
        for y in range(20):
            row = []
            for x in range(20):
                row.append(0.0 if x < 10 else 1.0)
            edge_grid.append(row)
        assert len(edge_detect(edge_grid, spacing=3).paths) > 0


class TestConcentric:
    def test_produces_paths(self):
        grid = _make_grid(pattern="gradient")
        d = concentric(grid, spacing=3, width_mm=60, height_mm=45)
        assert len(d.paths) > 0


class TestWoodcut:
    def test_produces_paths(self):
        grid = _make_grid(pattern="black")
        d = woodcut(grid, spacing=3)
        assert len(d.paths) > 0


class TestZigzag:
    def test_produces_paths(self):
        grid = _make_grid(pattern="black")
        d = zigzag(grid, spacing=3)
        assert len(d.paths) > 0


class TestTiles:
    def test_produces_paths(self):
        grid = _make_grid(pattern="black")
        d = tiles(grid, spacing=3)
        assert len(d.paths) > 0
