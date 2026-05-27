"""Tests for core.paths — ordering, joining, simplification, statistics."""

import math
import pytest
from core.paths import Path, Drawing, order_paths, join_paths, simplify_path, simplify_drawing, optimize


class TestPath:
    def test_start_end(self):
        p = Path([(0, 0), (10, 5), (20, 0)])
        assert p.start == (0, 0)
        assert p.end == (20, 0)

    def test_length(self):
        p = Path([(0, 0), (3, 4)])
        assert abs(p.length - 5.0) < 0.01

    def test_length_multi_segment(self):
        p = Path([(0, 0), (10, 0), (10, 10)])
        assert abs(p.length - 20.0) < 0.01

    def test_reversed(self):
        p = Path([(0, 0), (10, 5), (20, 0)])
        r = p.reversed()
        assert r.start == (20, 0)
        assert r.end == (0, 0)
        assert len(r.points) == 3

    def test_is_empty_single_point(self):
        assert Path([(0, 0)]).is_empty()
        assert not Path([(0, 0), (1, 1)]).is_empty()

    def test_is_empty_no_points(self):
        assert Path([]).is_empty()


class TestDrawing:
    def test_total_draw_length(self):
        d = Drawing([Path([(0, 0), (10, 0)]), Path([(0, 0), (0, 10)])])
        assert abs(d.total_draw_length() - 20.0) < 0.01

    def test_total_travel_length(self):
        d = Drawing([Path([(0, 0), (10, 0)]), Path([(20, 0), (30, 0)])])
        # travel: 0→(0,0) = 0, (10,0)→(20,0) = 10
        assert abs(d.total_travel_length() - 10.0) < 0.01

    def test_total_travel_length_empty(self):
        assert Drawing().total_travel_length() == 0.0


class TestOrderPaths:
    def test_single_path_unchanged(self):
        d = Drawing([Path([(0, 0), (10, 0)])])
        result = order_paths(d)
        assert len(result.paths) == 1
        assert result.paths[0].start == (0, 0)

    def test_reorders_to_reduce_travel(self):
        # Paths in bad order: far apart
        d = Drawing([
            Path([(0, 0), (10, 0)]),
            Path([(100, 0), (110, 0)]),
            Path([(10, 0), (20, 0)]),
        ])
        result = order_paths(d)
        # After ordering, path near (10,0) should come before (100,0)
        assert result.paths[0].start == (0, 0)
        assert result.paths[1].start[0] < 50  # should be the nearby one

    def test_reverses_path_if_closer(self):
        # If end of prev is closer to end of next, reverse next
        d = Drawing([
            Path([(0, 0), (10, 0)]),   # ends at (10, 0)
            Path([(20, 0), (10, 0)]),  # start=(20,0), end=(10,0) — end is closer
        ])
        result = order_paths(d)
        # Second path should be reversed so it starts at (10,0)
        assert result.paths[1].start == (10, 0)

    def test_starts_at_origin(self):
        d = Drawing([Path([(50, 50), (60, 50)])])
        result = order_paths(d)
        assert result.paths[0].start == (50, 50)

    def test_travel_decreases_after_ordering(self):
        import random
        rng = random.Random(42)
        paths = [Path([(rng.uniform(0, 200), rng.uniform(0, 200)),
                       (rng.uniform(0, 200), rng.uniform(0, 200))])
                 for _ in range(50)]
        d = Drawing(paths)
        before = d.total_travel_length()
        after = order_paths(d).total_travel_length()
        assert after <= before


class TestJoinPaths:
    def test_no_join_when_far(self):
        d = Drawing([Path([(0, 0), (10, 0)]), Path([(100, 0), (110, 0)])])
        result = join_paths(d, tolerance=0.5)
        assert len(result.paths) == 2

    def test_join_when_close(self):
        d = Drawing([Path([(0, 0), (10, 0)]), Path([(10.3, 0), (20, 0)])])
        result = join_paths(d, tolerance=0.5)
        assert len(result.paths) == 1
        assert result.paths[0].start == (0, 0)
        assert result.paths[0].end == (20, 0)

    def test_join_reversed(self):
        d = Drawing([Path([(0, 0), (10, 0)]), Path([(20, 0), (10.3, 0)])])
        result = join_paths(d, tolerance=0.5)
        assert len(result.paths) == 1

    def test_pen_lifts_decrease(self):
        d = Drawing([
            Path([(0, 0), (10, 0)]),
            Path([(10.1, 0), (20, 0)]),
            Path([(100, 0), (110, 0)]),
        ])
        result = join_paths(d, tolerance=0.5)
        assert len(result.paths) == 2  # first two merged


class TestSimplifyPath:
    def test_straight_line_unchanged(self):
        p = Path([(0, 0), (10, 0), (20, 0), (30, 0)])
        result = simplify_path(p, epsilon=0.1)
        assert len(result.points) == 2  # collapsed to start+end

    def test_curve_preserved(self):
        # Quarter circle
        pts = [(math.cos(a) * 10, math.sin(a) * 10)
               for a in [i * math.pi / 20 for i in range(11)]]
        p = Path(pts)
        result = simplify_path(p, epsilon=0.5)
        assert len(result.points) >= 3  # curve needs more points

    def test_short_path_unchanged(self):
        p = Path([(0, 0), (10, 10)])
        result = simplify_path(p, epsilon=0.1)
        assert len(result.points) == 2


class TestOptimize:
    def test_full_pipeline(self):
        d = Drawing([
            Path([(0, 0), (10, 0)]),
            Path([(10.1, 0), (20, 0)]),
            Path([(100, 0), (110, 0)]),
        ])
        result = optimize(d, join_tolerance=0.5, simplify_epsilon=0.1)
        assert len(result.paths) >= 1
        # First two should be joined
        assert any(p.start == (0, 0) for p in result.paths)
