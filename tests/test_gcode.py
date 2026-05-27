"""Tests for core.gcode — G-code generation, preview, statistics."""

import pytest
from core.paths import Path, Drawing
from core.gcode import PlotConfig, drawing_to_gcode, drawing_to_preview


def _simple_drawing():
    return Drawing([
        Path([(0, 0), (10, 0), (10, 10)]),
        Path([(20, 0), (30, 0)]),
    ])


class TestDrawingToGcode:
    def test_contains_header(self):
        cfg = PlotConfig()
        gcode = drawing_to_gcode(_simple_drawing(), cfg)
        assert "G21" in gcode
        assert "G90" in gcode

    def test_contains_footer(self):
        cfg = PlotConfig()
        gcode = drawing_to_gcode(_simple_drawing(), cfg)
        assert "M2" in gcode
        assert "G0 X0 Y0" in gcode

    def test_pen_up_down(self):
        cfg = PlotConfig(pen_up_z=0, pen_down_z=5)
        gcode = drawing_to_gcode(_simple_drawing(), cfg)
        assert f"G0 Z{cfg.pen_up_z}" in gcode
        assert f"G1 Z{cfg.pen_down_z}" in gcode

    def test_speed_in_feed(self):
        cfg = PlotConfig(speed=3000)
        gcode = drawing_to_gcode(_simple_drawing(), cfg)
        assert "F3000" in gcode

    def test_travel_moves_use_g0(self):
        cfg = PlotConfig()
        gcode = drawing_to_gcode(_simple_drawing(), cfg)
        # Travel to start of second path should be G0
        lines = gcode.split("\n")
        g0_moves = [l for l in lines if l.startswith("G0 X")]
        assert len(g0_moves) >= 2  # at least 2 travel moves

    def test_empty_drawing(self):
        cfg = PlotConfig()
        gcode = drawing_to_gcode(Drawing(), cfg)
        # Should still have header + footer
        assert "G21" in gcode
        assert "M2" in gcode


class TestDrawingToPreview:
    def test_returns_base64(self):
        preview = drawing_to_preview(_simple_drawing())
        assert isinstance(preview, str)
        assert len(preview) > 0

    def test_empty_drawing_returns_empty(self):
        preview = drawing_to_preview(Drawing())
        assert preview == ""

    def test_valid_png(self):
        import base64
        from PIL import Image
        import io
        preview = drawing_to_preview(_simple_drawing())
        data = base64.b64decode(preview)
        img = Image.open(io.BytesIO(data))
        assert img.size == (400, 400)


class TestPlotConfig:
    def test_defaults(self):
        cfg = PlotConfig()
        assert cfg.style == "hatching"
        assert cfg.threshold == 0.15
        assert cfg.join_tolerance == 0.5
        assert cfg.simplify_epsilon == 0.1

    def test_custom(self):
        cfg = PlotConfig(style="stipple", threshold=0.3, speed=5000)
        assert cfg.style == "stipple"
        assert cfg.threshold == 0.3
