"""
Path data structures and optimization algorithms for pen plotting.

A Path is a polyline: list of (x, y) points drawn sequentially with pen down.
A Drawing is a list of Paths that need to be plotted.

Optimization pipeline:
  1. Extract paths from image (style-specific)
  2. Order paths by greedy nearest-neighbour (reduces travel distance)
  3. Join paths whose endpoints are close (reduces pen lifts)
  4. Simplify paths with Ramer-Douglas-Peucker (reduces G-code size)
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field


@dataclass
class Path:
    """A polyline to be drawn with pen down."""
    points: list[tuple[float, float]] = field(default_factory=list)

    @property
    def start(self) -> tuple[float, float]:
        return self.points[0] if self.points else (0, 0)

    @property
    def end(self) -> tuple[float, float]:
        return self.points[-1] if self.points else (0, 0)

    @property
    def length(self) -> float:
        total = 0.0
        for i in range(1, len(self.points)):
            dx = self.points[i][0] - self.points[i - 1][0]
            dy = self.points[i][1] - self.points[i - 1][1]
            total += math.hypot(dx, dy)
        return total

    def reversed(self) -> Path:
        return Path(list(reversed(self.points)))

    def is_empty(self) -> bool:
        return len(self.points) < 2


@dataclass
class Drawing:
    """A set of paths to be plotted."""
    paths: list[Path] = field(default_factory=list)

    def total_draw_length(self) -> float:
        return sum(p.length for p in self.paths)

    def total_travel_length(self) -> float:
        if not self.paths:
            return 0.0
        total = math.hypot(self.paths[0].start[0], self.paths[0].start[1])
        for i in range(1, len(self.paths)):
            dx = self.paths[i].start[0] - self.paths[i - 1].end[0]
            dy = self.paths[i].start[1] - self.paths[i - 1].end[1]
            total += math.hypot(dx, dy)
        return total


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


# ─── Greedy Nearest-Neighbour Ordering ──────────────────────────────────────

def order_paths(drawing: Drawing) -> Drawing:
    """Reorder paths using greedy nearest-neighbour to minimise travel.

    For each path, we can draw it forward or reversed — whichever endpoint
    is closer to the current position. This is the standard TSP greedy
    approximation used by all plotter software (vpype, fogleman/axi, etc.)
    """
    if len(drawing.paths) <= 1:
        return drawing

    remaining = list(drawing.paths)
    ordered: list[Path] = []
    pos = (0.0, 0.0)  # start at origin

    while remaining:
        best_idx = 0
        best_dist = float('inf')
        best_reverse = False

        for i, p in enumerate(remaining):
            d_fwd = _dist(pos, p.start)
            d_rev = _dist(pos, p.end)
            if d_fwd < best_dist:
                best_dist = d_fwd
                best_idx = i
                best_reverse = False
            if d_rev < best_dist:
                best_dist = d_rev
                best_idx = i
                best_reverse = True

        p = remaining.pop(best_idx)
        if best_reverse:
            p = p.reversed()
        ordered.append(p)
        pos = p.end

    return Drawing(ordered)


# ─── Path Joining ────────────────────────────────────────────────────────────

def join_paths(drawing: Drawing, tolerance: float = 0.5) -> Drawing:
    """Join consecutive paths whose endpoints are within tolerance.

    If path A ends close to where path B starts, we merge them into one
    path — no pen lift needed. This can reduce pen lifts by 30-50%.
    """
    if not drawing.paths:
        return drawing

    joined: list[Path] = [drawing.paths[0]]

    for p in drawing.paths[1:]:
        prev = joined[-1]
        if _dist(prev.end, p.start) <= tolerance:
            # Merge: extend previous path with new points
            prev.points.extend(p.points)
        elif _dist(prev.end, p.end) <= tolerance:
            # Merge reversed
            prev.points.extend(reversed(p.points))
        else:
            joined.append(p)

    return Drawing(joined)


# ─── Ramer-Douglas-Peucker Simplification ────────────────────────────────────

def simplify_path(path: Path, epsilon: float = 0.1) -> Path:
    """Simplify a polyline using the Ramer-Douglas-Peucker algorithm.

    Removes points that don't contribute significantly to the shape.
    Epsilon is the maximum deviation allowed (in mm).
    """
    if len(path.points) <= 2:
        return path

    pts = path.points

    # Find the point with maximum distance from line(start, end)
    start, end = pts[0], pts[-1]
    max_dist = 0.0
    max_idx = 0

    for i in range(1, len(pts) - 1):
        d = _point_line_distance(pts[i], start, end)
        if d > max_dist:
            max_dist = d
            max_idx = i

    if max_dist > epsilon:
        # Recurse on both halves
        left = simplify_path(Path(pts[:max_idx + 1]), epsilon)
        right = simplify_path(Path(pts[max_idx:]), epsilon)
        return Path(left.points[:-1] + right.points)
    else:
        return Path([start, end])


def simplify_drawing(drawing: Drawing, epsilon: float = 0.1) -> Drawing:
    return Drawing([simplify_path(p, epsilon) for p in drawing.paths])


def _point_line_distance(p: tuple[float, float],
                         a: tuple[float, float],
                         b: tuple[float, float]) -> float:
    """Perpendicular distance from point p to line segment a-b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    len_sq = dx * dx + dy * dy
    if len_sq == 0:
        return _dist(p, a)
    t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len_sq))
    proj = (a[0] + t * dx, a[1] + t * dy)
    return _dist(p, proj)


# ─── Full Optimization Pipeline ─────────────────────────────────────────────

def optimize(drawing: Drawing, join_tolerance: float = 0.5,
             simplify_epsilon: float = 0.1) -> Drawing:
    """Apply the full optimization pipeline: order → join → simplify."""
    d = order_paths(drawing)
    d = join_paths(d, tolerance=join_tolerance)
    d = simplify_drawing(d, epsilon=simplify_epsilon)
    return d
