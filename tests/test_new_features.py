"""Tests for new features: preprocessing, pen delay, travel speed, edge detection, invert, stats."""

import pytest
from PIL import Image
import io

from core.paths import Path, Drawing
from core.gcode import PlotConfig, drawing_to_gcode, drawing_to_preview


# ─── Image Preprocessing ────────────────────────────────────────────────────

class TestImagePreprocessing:
    def test_invert_brightness(self):
        """Invert should swap dark/light regions."""
        from core.preprocessing import preprocess_image
        img = Image.new("L", (10, 10), 0)  # black image
        result = preprocess_image(img, invert=True)
        # After invert, all pixels should be 255 (white)
        pixels = list(result.get_flattened_data())
        assert all(p == 255 for p in pixels)

    def test_brightness_adjustment(self):
        """Brightness slider should shift pixel values."""
        from core.preprocessing import preprocess_image
        img = Image.new("L", (10, 10), 128)
        result = preprocess_image(img, brightness=1.5)
        pixels = list(result.get_flattened_data())
        assert all(p > 128 for p in pixels)

    def test_contrast_adjustment(self):
        """Contrast should increase difference from midpoint."""
        from core.preprocessing import preprocess_image
        img = Image.new("L", (10, 10), 128)
        result = preprocess_image(img, contrast=2.0)
        pixels = list(result.get_flattened_data())
        # High contrast on mid-gray pushes toward 255
        assert all(p >= 128 for p in pixels)

    def test_blur(self):
        """Blur should smooth the image."""
        from core.preprocessing import preprocess_image
        # Image with sharp edge
        img = Image.new("L", (100, 100), 255)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 49, 99], fill=0)
        result = preprocess_image(img, blur=2)
        # After blur, edge should be softer
        pixels = list(result.get_flattened_data())
        # Middle column should have intermediate values
        mid_col = [pixels[x + 50 * 100] for x in range(100)]
        non_extreme = [p for p in mid_col if 10 < p < 245]
        assert len(non_extreme) > 0


# ─── Pen Delay ──────────────────────────────────────────────────────────────

class TestPenDelay:
    def test_pen_down_has_delay(self):
        """G-code should include G4 pause after pen down."""
        cfg = PlotConfig(pen_down_delay=0.1)
        d = Drawing([Path([(0, 0), (10, 0)])])
        gcode = drawing_to_gcode(d, cfg)
        assert "G4 P0.1" in gcode

    def test_pen_up_has_delay(self):
        """G-code should include G4 pause after pen up."""
        cfg = PlotConfig(pen_up_delay=0.05)
        d = Drawing([Path([(0, 0), (10, 0)])])
        gcode = drawing_to_gcode(d, cfg)
        assert "G4 P0.05" in gcode

    def test_no_delay_when_zero(self):
        """No G4 commands when delays are 0."""
        cfg = PlotConfig(pen_down_delay=0, pen_up_delay=0)
        d = Drawing([Path([(0, 0), (10, 0)])])
        gcode = drawing_to_gcode(d, cfg)
        assert "G4" not in gcode


# ─── Travel Speed ───────────────────────────────────────────────────────────

class TestTravelSpeed:
    def test_travel_moves_use_travel_speed(self):
        """G0 moves should use travel speed, G1 moves use draw speed."""
        cfg = PlotConfig(speed=3000, travel_speed=8000)
        d = Drawing([Path([(0, 0), (10, 0)]), Path([(30, 0), (40, 0)])])
        gcode = drawing_to_gcode(d, cfg)
        # G0 travel should have F8000
        assert "F8000" in gcode
        # G1 draw should have F3000
        assert "F3000" in gcode


# ─── Edge Detection Style ───────────────────────────────────────────────────

class TestEdgeDetection:
    def test_produces_paths(self):
        """Edge detection converter should produce paths."""
        from core.converters import edge_detect
        grid = []
        for y in range(20):
            row = []
            for x in range(20):
                # Sharp vertical edge at x=10
                row.append(0.0 if x < 10 else 1.0)
            grid.append(row)
        d = edge_detect(grid, spacing=3)
        assert isinstance(d, Drawing)
        assert len(d.paths) > 0

    def test_uniform_image_no_edges(self):
        """Uniform image should produce no edges."""
        from core.converters import edge_detect
        grid = [[0.5] * 20 for _ in range(20)]
        d = edge_detect(grid, spacing=3)
        assert len(d.paths) == 0


# ─── Invert Option ──────────────────────────────────────────────────────────

class TestInvertOption:
    def test_invert_in_config(self):
        """PlotConfig should support invert flag."""
        cfg = PlotConfig(invert=True)
        assert cfg.invert is True

    def test_invert_produces_different_output(self):
        """Inverted image should produce different G-code."""
        from core.pipeline import image_to_gcode
        # Create a test image with variation (half black, half white)
        img = Image.new("L", (100, 100), 255)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 49, 99], fill=0)
        img.save("C:/Users/Semyon/horus-plotter/tests/test_invert.png")
        cfg_normal = PlotConfig(style="hatching", invert=False, auto_invert=False)
        cfg_inverted = PlotConfig(style="hatching", invert=True, auto_invert=False)
        g1, _ = image_to_gcode("C:/Users/Semyon/horus-plotter/tests/test_invert.png", cfg_normal)
        g2, _ = image_to_gcode("C:/Users/Semyon/horus-plotter/tests/test_invert.png", cfg_inverted)
        assert g1 != g2


# ─── G-code Statistics ──────────────────────────────────────────────────────

class TestGcodeStats:
    def test_stats_structure(self):
        """gcode_stats should return dict with expected keys."""
        from core.gcode import gcode_stats
        d = Drawing([Path([(0, 0), (10, 0)]), Path([(20, 0), (30, 0)])])
        cfg = PlotConfig()
        stats = gcode_stats(d, cfg)
        assert "pen_lifts" in stats
        assert "total_draw_mm" in stats
        assert "total_travel_mm" in stats
        assert "estimated_time_sec" in stats
        assert "num_paths" in stats

    def test_pen_lifts_count(self):
        """Should count pen lifts correctly."""
        from core.gcode import gcode_stats
        d = Drawing([Path([(0, 0), (10, 0)]), Path([(20, 0), (30, 0)])])
        cfg = PlotConfig()
        stats = gcode_stats(d, cfg)
        assert stats["pen_lifts"] == 2
        assert stats["num_paths"] == 2

    def test_draw_distance(self):
        """Should calculate total draw distance."""
        from core.gcode import gcode_stats
        d = Drawing([Path([(0, 0), (10, 0)])])
        cfg = PlotConfig()
        stats = gcode_stats(d, cfg)
        assert abs(stats["total_draw_mm"] - 10.0) < 0.1


# ─── Work Area Boundary ────────────────────────────────────────────────────

class TestWorkAreaBoundary:
    def test_tall_image_fits_in_work_area(self):
        """Tall image should be scaled down to fit within work_area_y."""
        from core.pipeline import image_to_gcode
        # Create a tall image (portrait)
        img = Image.new("L", (100, 400), 255)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 50, 90, 350], fill=0)
        img.save("C:/Users/Semyon/horus-plotter/tests/test_tall_boundary.png")

        cfg = PlotConfig(style="hatching", width_mm=200, spacing_mm=3,
                         work_area_x=300, work_area_y=300)
        gcode, _ = image_to_gcode("C:/Users/Semyon/horus-plotter/tests/test_tall_boundary.png", cfg)

        # Check no draw coordinate exceeds work area
        for line in gcode.split("\n"):
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            # Only check G1 (draw) moves — G0 travel/home are not constrained
            if line.startswith("G1"):
                for part in line.split():
                    if part.startswith("X"):
                        x = float(part[1:])
                        assert 0 <= x <= 300, f"X={x} exceeds work area"
                    if part.startswith("Y"):
                        y = float(part[1:])
                        assert 0 <= y <= 300, f"Y={y} exceeds work area"

    def test_drawing_is_centered(self):
        """Drawing should be centered within the work area."""
        from core.pipeline import image_to_gcode
        img = Image.new("L", (200, 100), 255)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 25, 150, 75], fill=0)
        img.save("C:/Users/Semyon/horus-plotter/tests/test_center.png")

        cfg = PlotConfig(style="hatching", width_mm=100, spacing_mm=3,
                         work_area_x=300, work_area_y=300)
        gcode, _ = image_to_gcode("C:/Users/Semyon/horus-plotter/tests/test_center.png", cfg)

        # Parse only G1 (draw) moves — G0 travel/home moves are not part of drawing
        xs, ys = [], []
        for line in gcode.split("\n"):
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            if line.startswith("G1"):
                for part in line.split():
                    if part.startswith("X"):
                        xs.append(float(part[1:]))
                    if part.startswith("Y"):
                        ys.append(float(part[1:]))

        if xs and ys:
            # Center of drawn paths should be near center of work area (150, 150)
            center_x = (min(xs) + max(xs)) / 2
            center_y = (min(ys) + max(ys)) / 2
            assert abs(center_x - 150) < 15, f"X center={center_x}, expected ~150"
            assert abs(center_y - 150) < 15, f"Y center={center_y}, expected ~150"


# ─── Auto-Invert ────────────────────────────────────────────────────────────

class TestAutoInvert:
    def test_dark_image_auto_inverted(self):
        """Dark-background image should be auto-inverted."""
        from core.pipeline import _should_auto_invert
        # Mostly dark image
        img = Image.new("L", (100, 100), 30)
        assert _should_auto_invert(img) is True

    def test_light_image_not_inverted(self):
        """Light-background image should NOT be auto-inverted."""
        from core.pipeline import _should_auto_invert
        # Mostly light image
        img = Image.new("L", (100, 100), 230)
        assert _should_auto_invert(img) is False

    def test_auto_invert_produces_fewer_commands(self):
        """Auto-invert on dark image should produce fewer G-code commands."""
        from core.pipeline import image_to_gcode
        # Dark background with light content
        img = Image.new("L", (100, 100), 30)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.rectangle([30, 30, 70, 70], fill=230)
        img.save("C:/Users/Semyon/horus-plotter/tests/test_auto_inv.png")

        cfg_auto = PlotConfig(style="hatching", width_mm=100, spacing_mm=3,
                              auto_invert=True, invert=False)
        cfg_no_auto = PlotConfig(style="hatching", width_mm=100, spacing_mm=3,
                                 auto_invert=False, invert=False)

        g_auto, _ = image_to_gcode("C:/Users/Semyon/horus-plotter/tests/test_auto_inv.png", cfg_auto)
        g_no_auto, _ = image_to_gcode("C:/Users/Semyon/horus-plotter/tests/test_auto_inv.png", cfg_no_auto)

        cmds_auto = len([l for l in g_auto.split("\n") if l.strip() and not l.strip().startswith(";")])
        cmds_no_auto = len([l for l in g_no_auto.split("\n") if l.strip() and not l.strip().startswith(";")])
        # Auto-inverted should have fewer commands (only the light square, not the dark bg)
        assert cmds_auto < cmds_no_auto


# ─── Error Paths ────────────────────────────────────────────────────────────

class TestErrorPaths:
    def test_unsupported_format_raises(self) -> None:
        """Loading an unsupported file should raise ImageLoadError."""
        from core.pipeline import _load_as_image
        from core.exceptions import ImageLoadError
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            f.write(b"test")
            tmp_path = f.name

        try:
            with pytest.raises(ImageLoadError):
                _load_as_image(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_empty_drawing_stats(self) -> None:
        """Stats on empty drawing should return zeros."""
        from core.gcode import gcode_stats
        d = Drawing()
        cfg = PlotConfig()
        stats = gcode_stats(d, cfg)
        assert stats["num_paths"] == 0
        assert stats["pen_lifts"] == 0
        assert stats["total_draw_mm"] == 0.0
        assert stats["total_travel_mm"] == 0.0
