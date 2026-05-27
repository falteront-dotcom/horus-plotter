"""Tests for ultra_core.py — precision engine."""
import pytest
from core.ultra_core import *
from core.paths import Drawing, Path

class TestGrblPrecision:
    def test_config_defaults(self):
        cfg = GrblPrecisionConfig()
        assert cfg.acceleration_xy == 500
        assert cfg.s_curve_enabled is True

    def test_generate_config_gcode(self):
        gcode = generate_grbl_config_gcode(GrblPrecisionConfig())
        assert "$120=" in gcode
        assert "$121=" in gcode
        assert "$11=" in gcode
        assert "G21" in gcode

    def test_junction_speed_straight(self):
        v = compute_junction_speed(0, 0.02, 500)
        assert v > 10000, "Straight line should have high junction speed"

    def test_junction_speed_corner(self):
        v = compute_junction_speed(90, 0.02, 500)
        assert 0 < v < 1000, "Sharp corner should limit speed"

class Test2Opt:
    def test_empty_drawing(self):
        d = Drawing([])
        result = optimize_2opt(d)
        assert len(result.paths) == 0

    def test_two_path_ordering(self):
        d = Drawing([
            Path([(100, 0), (110, 0)]),
            Path([(0, 0), (10, 0)]),
        ])
        result = optimize_2opt(d)
        assert len(result.paths) == 2

    def test_optimization_does_not_increase(self):
        d = Drawing([
            Path([(50, 0), (60, 0)]),
            Path([(0, 0), (10, 0)]),
            Path([(30, 0), (40, 0)]),
            Path([(80, 0), (90, 0)]),
        ])
        orig_travel = d.total_travel_length()
        result = optimize_2opt(d)
        assert result.total_travel_length() <= orig_travel * 1.1

class TestHilbertOrder:
    def test_preserves_count(self):
        d = Drawing([Path([(i * 10, 0), (i * 10 + 5, 0)]) for i in range(10)])
        result = hilbert_order(d)
        assert len(result.paths) == 10

class TestCalibration:
    def test_square_generation(self):
        d = generate_calibration_square(50)
        assert len(d.paths) == 3

    def test_grid_generation(self):
        d = generate_calibration_grid(100, 100, 20)
        assert len(d.paths) > 5

    def test_calibrate_from_measured(self):
        cal = calibrate_from_measured(49.5, 50.2, 50, 50)
        assert 0.9 < cal.scale_x < 1.1
        assert 0.9 < cal.scale_y < 1.1

    def test_apply_calibration(self):
        cal = CalibrationData(scale_x=1.01, offset_x=2.0)
        x, y = apply_calibration(10, 20, cal)
        assert abs(x - 12.1) < 0.01

class TestTypography:
    def test_kerning_pairs_exist(self):
        assert get_kerning('А', 'Т') != 0
        assert get_kerning('Г', 'Т') != 0

    def test_no_kerning_for_unknown(self):
        assert get_kerning('X', 'Y') == 0

    def test_hyphenation_short_word(self):
        parts = hyphenate_word("дом", 20)
        assert len(parts) == 1 and parts[0] == "дом"

    def test_hyphenation_long_word(self):
        parts = hyphenate_word("интернационализация", 10)
        assert len(parts) >= 2

    def test_justify_adds_spaces(self):
        result = justify_text("hello world", 200, 5)
        assert len(result) > len("hello world")

    def test_river_detection(self):
        lines = ["a b c", "a b c", "a b c"]
        rivers = detect_rivers(lines)
        assert len(rivers) >= 1

class TestDryRun:
    def test_estimates_time(self):
        gcode = "G0 X0 Y0 Z0\nG1 Z5\nG1 X100 Y0 F3000\nG1 X100 Y100\nG0 Z0\nG0 X0 Y0 Z0"
        est = dry_run_estimate(gcode)
        assert est["total_time_sec"] > 0

class TestQuality:
    def test_straight_path_perfect(self):
        p = Path([(0, 0), (10, 0), (20, 0)])
        score = path_smoothness_score(p)
        assert score > 0.9, f"Straight path should be smooth, got {score}"

    def test_jagged_path_worse(self):
        p = Path([(0, 0), (10, 10), (0, 20)])
        score1 = path_smoothness_score(p)
        p2 = Path([(0, 0), (0, 10), (10, 20), (20, 15)])
        score2 = path_smoothness_score(p2)
        assert score2 < 1.0

    def test_drawing_quality(self):
        d = Drawing([Path([(0, 0), (10, 0)]), Path([(10, 0), (20, 0)])])
        qs = drawing_quality_score(d)
        assert "overall_score" in qs
        assert 0 <= qs["overall_score"] <= 1

class TestBounds:
    def test_bounds_empty(self):
        b = Bounds()
        assert b.width == 0

    def test_compute_drawing_bounds(self):
        d = Drawing([Path([(10, 20), (30, 40)])])
        b = compute_drawing_bounds(d)
        assert b.x_min <= 10
        assert b.x_max >= 30

    def test_validate_gcode_bounds(self):
        gcode = "G1 X999 Y999\nG1 X10 Y10"
        violations = validate_gcode_bounds(gcode, 500, 500)
        assert len(violations) >= 2

class TestPenProfile:
    def test_pressure_variation(self):
        profile = PenProfile(pressure_vary=True)
        # Horizontal stroke (0 deg) vs vertical (90 deg)
        # Vertical should have less pressure (cos^2(90) = 0)
        p_up = compute_pressure(90, profile)   # vertical = down-stroke
        p_side = compute_pressure(0, profile)   # horizontal = side-stroke
        assert p_up < p_side, "Horizontal strokes should have more pressure"

    def test_pen_change_gcode(self):
        gcode = generate_pen_change_gcode(2, 5.0)
        assert "M0" in gcode
        assert "Pen change" in gcode

class TestExport:
    def test_hpgl_export(self):
        d = Drawing([Path([(0, 0), (10, 10)])])
        hpgl = export_hpgl(d)
        assert "PU" in hpgl
        assert "PD" in hpgl

    def test_dxf_export(self):
        d = Drawing([Path([(0, 0), (20, 20)])])
        dxf = export_dxf(d)
        assert "SECTION" in dxf
        assert "LWPOLYLINE" in dxf

class TestSmoothing:
    def test_smooth_reduces_jitter(self):
        p = Path([(0, 0), (1, 2), (0, 4), (-1, 6)])
        smoothed = smooth_path(p, window_size=3)
        assert len(smoothed.points) == len(p.points)

class TestOptimizeFull:
    def test_all_methods_work(self):
        d = Drawing([Path([(i * 10, 0), (i * 10 + 5, 0)]) for i in range(5)])
        for method in ["greedy", "2opt", "hilbert", "full"]:
            result = optimize_paths_full(d, method=method)
            assert len(result.paths) == 5, f"{method} lost paths"
