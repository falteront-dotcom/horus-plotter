"""Image → Drawing converters (path extraction).

Each converter takes a brightness grid and config, returns a Drawing
containing paths that the plotter should draw.
"""

from __future__ import annotations

import math
import random

from .paths import Drawing, Path


# ─── Grid helpers (DRY) ─────────────────────────────────────────────────────

def _grid_dims(grid: list[list[float]]) -> tuple[int, int]:
    """Return (rows, cols) for a brightness grid."""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    return rows, cols


def _cell_to_mm(
    row: int, col: int, rows: int, spacing: float
) -> tuple[float, float]:
    """Convert grid cell coordinates to millimetres.

    Y axis is flipped so row 0 is at the top of the image.
    """
    x = col * spacing
    y = (rows - 1 - row) * spacing
    return x, y


def _cell_darkness(grid: list[list[float]], row: int, col: int) -> float:
    """Return darkness (0=white, 1=black) for a grid cell."""
    return 1.0 - grid[row][col]


def _is_dark(
    grid: list[list[float]], row: int, col: int, threshold: float
) -> bool:
    """Check whether a cell is dark enough to draw."""
    return _cell_darkness(grid, row, col) > threshold


# ─── Hatching ───────────────────────────────────────────────────────────────

def hatching(grid: list[list[float]], spacing: float,
             threshold: float = 0.15, angle: float = 0,
             cross_hatch: bool = True) -> Drawing:
    """Horizontal line hatching with optional cross-hatch for dark areas.

    Args:
        grid: brightness grid (0=black, 1=white)
        spacing: mm between lines
        threshold: darkness threshold to start drawing (0-1)
        angle: hatch angle in degrees (0 = horizontal)
        cross_hatch: add diagonal lines for dark areas (darkness > 0.5)
    """
    rows, cols = _grid_dims(grid)
    paths = []

    # Main hatching passes (horizontal)
    for r in range(rows):
        y = (rows - 1 - r) * spacing
        seg_start = None

        for c in range(cols + 1):
            dark = _cell_darkness(grid, r, c) if c < cols else 0.0
            should = dark > threshold

            if should and seg_start is None:
                seg_start = (c * spacing, y)
            elif not should and seg_start is not None:
                paths.append(Path([seg_start, (c * spacing, y)]))
                seg_start = None

        if seg_start is not None:
            paths.append(Path([seg_start, (cols * spacing, y)]))

    # Cross-hatch for dark areas
    if cross_hatch:
        cross_threshold = max(threshold, 0.3)
        for r in range(rows):
            for c in range(cols):
                dark = _cell_darkness(grid, r, c)
                if dark < cross_threshold:
                    continue
                x, y = _cell_to_mm(r, c, rows, spacing)
                half = spacing * 0.35
                paths.append(Path([(x - half, y - half), (x + half, y + half)]))

    return Drawing(paths)


# ─── Cross-Hatching at Angle ────────────────────────────────────────────────

def cross_hatching(grid: list[list[float]], spacing: float,
                   threshold: float = 0.15, angles: list[float] = None) -> Drawing:
    """Multi-angle cross-hatching. Each angle adds a layer of lines.

    Args:
        angles: list of angles in degrees (default: [0, 45])
    """
    if angles is None:
        angles = [0, 45]

    rows, cols = _grid_dims(grid)
    paths = []

    w = cols * spacing
    h = rows * spacing

    for angle_deg in angles:
        angle = math.radians(angle_deg)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Perpendicular direction for spacing
        perp_x = -sin_a
        perp_y = cos_a

        # How many lines we need
        diag = math.hypot(w, h)
        n_lines = int(diag / spacing) + 1

        for i in range(-n_lines, n_lines + 1):
            offset = i * spacing
            # Line through the image at this offset
            # Origin point on the perpendicular axis
            ox = w / 2 + perp_x * offset
            oy = h / 2 + perp_y * offset

            # Sample points along this line
            seg_start = None
            steps = int(diag / (spacing * 0.5)) + 1

            for s in range(-steps, steps + 1):
                px = ox + cos_a * s * spacing * 0.5
                py = oy + sin_a * s * spacing * 0.5

                # Check if point is in image bounds
                col = int(px / spacing)
                row = rows - 1 - int(py / spacing)

                if 0 <= row < rows and 0 <= col < cols:
                    should = _is_dark(grid, row, col, threshold)
                else:
                    should = False

                if should and seg_start is None:
                    seg_start = (px, py)
                elif not should and seg_start is not None:
                    paths.append(Path([seg_start, (px, py)]))
                    seg_start = None

            if seg_start is not None:
                paths.append(Path([seg_start, (ox + cos_a * steps * spacing * 0.5,
                                                oy + sin_a * steps * spacing * 0.5)]))

    return Drawing(paths)


# ─── Halftone ───────────────────────────────────────────────────────────────

def halftone(grid: list[list[float]], spacing: float,
             threshold: float = 0.1, segments: int = 8) -> Drawing:
    """Varying-size circles. Darker = bigger circle."""
    rows, cols = _grid_dims(grid)
    max_r = spacing * 0.45
    paths = []

    for r in range(rows):
        for c in range(cols):
            dark = _cell_darkness(grid, r, c)
            if dark < threshold:
                continue
            radius = dark * max_r
            if radius < 0.3:
                continue
            cx, cy = _cell_to_mm(r, c, rows, spacing)

            # Circle as closed polygon
            pts = []
            for i in range(segments):
                a = 2 * math.pi * i / segments
                pts.append((round(cx + radius * math.cos(a), 6),
                            round(cy + radius * math.sin(a), 6)))
            # Close the circle explicitly
            pts.append(pts[0])
            paths.append(Path(pts))

    return Drawing(paths)


# ─── Stipple ────────────────────────────────────────────────────────────────

def stipple(grid: list[list[float]], spacing: float,
            threshold: float = 0.1, dot_size: float = 0.5,
            seed: int = 42) -> Drawing:
    """Random dots with density based on darkness."""
    rows, cols = _grid_dims(grid)
    rng = random.Random(seed)
    paths = []

    for r in range(rows):
        for c in range(cols):
            dark = _cell_darkness(grid, r, c)
            if dark < threshold:
                continue
            n = int(dark * 4)
            for _ in range(n):
                cx, cy = _cell_to_mm(r, c, rows, spacing)
                cx += rng.random() * spacing
                cy += rng.random() * spacing
                paths.append(Path([(cx, cy), (cx + dot_size, cy)]))

    return Drawing(paths)


# ─── Spiral ─────────────────────────────────────────────────────────────────

def spiral(grid: list[list[float]], spacing: float, width_mm: float,
           height_mm: float, threshold: float = 0.1) -> Drawing:
    """Continuous spiral from center outward, radius modulated by brightness."""
    rows, cols = _grid_dims(grid)
    cx_center = width_mm / 2
    cy_center = height_mm / 2
    max_r = min(width_mm, height_mm) / 2
    turns = max_r / spacing
    total = int(turns * 360)
    a_step = 2 * math.pi * turns / total

    current_pts: list[tuple[float, float]] = []
    paths = []

    for i in range(total):
        angle = i * a_step
        base_r = (i / total) * max_r
        px = cx_center + base_r * math.cos(angle)
        py = cy_center + base_r * math.sin(angle)

        col = int(px / spacing)
        row = rows - 1 - int(py / spacing)

        dark = 0.3
        if 0 <= row < rows and 0 <= col < cols:
            dark = _cell_darkness(grid, row, col)

        mod_r = base_r + dark * spacing * 0.3
        x = cx_center + mod_r * math.cos(angle)
        y = cy_center + mod_r * math.sin(angle)

        if dark > threshold:
            current_pts.append((x, y))
        else:
            if len(current_pts) >= 2:
                paths.append(Path(current_pts))
            current_pts = []

    if len(current_pts) >= 2:
        paths.append(Path(current_pts))

    return Drawing(paths)


# ─── Flow Field ──────────────────────────────────────────────────────────────

def flow_field(grid: list[list[float]], spacing: float, width_mm: float,
               height_mm: float, threshold: float = 0.1,
               noise_scale: float = 0.01, seed: int = 42) -> Drawing:
    """Lines following a vector field derived from image gradients.

    Each line starts at a seed point and follows the local gradient
    direction (perpendicular to it), creating flowing organic curves.
    """
    rows, cols = _grid_dims(grid)
    rng = random.Random(seed)
    paths = []

    # Compute gradient (Sobel-like)
    def gradient_at(r: int, c: int) -> tuple[float, float]:
        """Returns (gx, gy) — direction of increasing brightness."""
        if r <= 0 or r >= rows - 1 or c <= 0 or c >= cols - 1:
            return (0.0, 0.0)
        gx = grid[r][c + 1] - grid[r][c - 1]
        gy = grid[r + 1][c] - grid[r - 1][c]
        return (gx, gy)

    # Seed points on a grid
    step = max(2, int(spacing * 1.5 / spacing))

    for r in range(0, rows, step):
        for c in range(0, cols, step):
            if not _is_dark(grid, r, c, threshold):
                continue

            # Start point
            x = c * spacing + rng.uniform(-spacing * 0.3, spacing * 0.3)
            y = (rows - 1 - r) * spacing + rng.uniform(-spacing * 0.3, spacing * 0.3)

            pts = [(x, y)]
            max_steps = 80

            for _ in range(max_steps):
                col_i = int(x / spacing)
                row_i = rows - 1 - int(y / spacing)

                if not (0 <= row_i < rows and 0 <= col_i < cols):
                    break

                if not _is_dark(grid, row_i, col_i, threshold):
                    break

                gx, gy = gradient_at(row_i, col_i)

                # Perpendicular to gradient = flow direction
                mag = math.hypot(gx, gy)
                if mag < 0.001:
                    # No gradient — use a gentle curve based on position
                    angle = math.atan2(y - height_mm / 2, x - width_mm / 2) + math.pi / 2
                    fx = math.cos(angle) * spacing * 0.5
                    fy = math.sin(angle) * spacing * 0.5
                else:
                    # Perpendicular direction (rotate 90°)
                    fx = -gy / mag * spacing * 0.5
                    fy = gx / mag * spacing * 0.5

                x += fx
                y += fy
                pts.append((x, y))

            if len(pts) >= 2:
                paths.append(Path(pts))

    return Drawing(paths)


# ─── Meandering (wavy lines) ────────────────────────────────────────────────

def meandering(grid: list[list[float]], spacing: float, width_mm: float,
               height_mm: float, threshold: float = 0.15,
               wave_amplitude: float = 1.0, seed: int = 42) -> Drawing:
    """Wavy horizontal lines with amplitude modulated by darkness.

    Creates organic, hand-drawn looking fills.
    """
    rows, cols = _grid_dims(grid)
    paths = []

    for r in range(rows):
        y_base = (rows - 1 - r) * spacing
        # Build a continuous wavy line across dark regions
        pts = []
        in_dark = False

        for c in range(cols):
            should = _is_dark(grid, r, c, threshold)

            if should:
                x = c * spacing
                # Wave offset proportional to darkness
                wave = math.sin(c * 0.5) * wave_amplitude * _cell_darkness(grid, r, c)
                y = y_base + wave
                pts.append((x, y))
                in_dark = True
            elif in_dark and pts:
                paths.append(Path(pts))
                pts = []
                in_dark = False

        if len(pts) >= 2:
            paths.append(Path(pts))

    return Drawing(paths)


# ─── Edge Detection ──────────────────────────────────────────────────────────

def edge_detect(grid: list[list[float]], spacing: float,
                threshold: float = 0.15) -> Drawing:
    """Trace edges in the image using a Sobel-like gradient magnitude filter.

    Produces short path segments along edges where brightness changes rapidly.
    Uniform areas produce no output.
    """
    rows, cols = _grid_dims(grid)
    paths = []

    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            # Sobel-like gradient magnitude
            gx = (grid[r][c + 1] - grid[r][c - 1]) / 2.0
            gy = (grid[r + 1][c] - grid[r - 1][c]) / 2.0
            mag = math.hypot(gx, gy)

            if mag > threshold:
                x = c * spacing
                y = (rows - 1 - r) * spacing
                # Short segment perpendicular to gradient
                if mag > 0.001:
                    nx = -gy / mag
                    ny = gx / mag
                else:
                    nx, ny = 1.0, 0.0
                half = spacing * 0.3 * min(mag, 1.0)
                paths.append(Path([
                    (x - nx * half, y - ny * half),
                    (x + nx * half, y + ny * half),
                ]))

    return Drawing(paths)


# ─── Dots Grid ──────────────────────────────────────────────────────────────

def dots(grid: list[list[float]], spacing: float,
         threshold: float = 0.1) -> Drawing:
    """Regular grid of dots with size modulated by darkness.

    Like halftone but dots are small circles at grid intersections.
    """
    rows, cols = _grid_dims(grid)
    max_r = spacing * 0.3
    paths = []

    for r in range(rows):
        for c in range(cols):
            dark = _cell_darkness(grid, r, c)
            if dark < threshold:
                continue
            radius = dark * max_r
            if radius < 0.2:
                continue
            cx, cy = _cell_to_mm(r, c, rows, spacing)
            # Small circle (6 segments)
            pts = []
            for i in range(6):
                a = 2 * math.pi * i / 6
                pts.append((round(cx + radius * math.cos(a), 4),
                            round(cy + radius * math.sin(a), 4)))
            pts.append(pts[0])
            paths.append(Path(pts))

    return Drawing(paths)


# ─── Concentric ─────────────────────────────────────────────────────────────

def concentric(grid: list[list[float]], spacing: float,
               width_mm: float, height_mm: float,
               threshold: float = 0.1) -> Drawing:
    """Concentric rectangles from outside in, skipping white areas.

    Creates a topographic-map look.
    """
    rows, cols = _grid_dims(grid)
    paths = []
    cx = width_mm / 2
    cy = height_mm / 2
    max_half = min(width_mm, height_mm) / 2
    n_rings = int(max_half / spacing)

    for i in range(n_rings):
        half = max_half - i * spacing
        if half < spacing * 0.5:
            break

        # Build rectangle
        rect = [
            (cx - half, cy - half),
            (cx + half, cy - half),
            (cx + half, cy + half),
            (cx - half, cy + half),
            (cx - half, cy - half),
        ]

        # Sample darkness along this ring
        total_dark = 0
        count = 0
        for pt in rect[:-1]:
            col = int(pt[0] / spacing)
            row = rows - 1 - int(pt[1] / spacing)
            if 0 <= row < rows and 0 <= col < cols:
                total_dark += _cell_darkness(grid, row, col)
                count += 1

        if count > 0 and total_dark / count > threshold:
            paths.append(Path(rect))

    return Drawing(paths)


# ─── Woodcut ────────────────────────────────────────────────────────────────

def woodcut(grid: list[list[float]], spacing: float,
            threshold: float = 0.15, seed: int = 42) -> Drawing:
    """Thick engraved lines with variable width, like a woodcut print.

    Lines are horizontal but thickness varies with darkness.
    """
    rows, cols = _grid_dims(grid)
    rng = random.Random(seed)
    paths = []

    for r in range(rows):
        y_base = (rows - 1 - r) * spacing
        pts = []
        in_dark = False

        for c in range(cols + 1):
            dark = _cell_darkness(grid, r, c) if c < cols else 0.0
            should = dark > threshold

            if should:
                x = c * spacing
                # Wavy offset based on darkness
                wobble = rng.uniform(-0.3, 0.3) * dark * spacing
                pts.append((x, y_base + wobble))
                in_dark = True
            elif in_dark and pts:
                if len(pts) >= 2:
                    paths.append(Path(pts))
                pts = []
                in_dark = False

        if len(pts) >= 2:
            paths.append(Path(pts))

    return Drawing(paths)


# ─── Zigzag ──────────────────────────────────────────────────────────────────

def zigzag(grid: list[list[float]], spacing: float,
           threshold: float = 0.15, amplitude: float = 1.0) -> Drawing:
    """Zigzag lines with amplitude modulated by darkness.

    Creates a cross-stitch / embroidery look.
    """
    rows, cols = _grid_dims(grid)
    paths = []

    for r in range(rows):
        y_base = (rows - 1 - r) * spacing
        pts = []
        in_dark = False

        for c in range(cols + 1):
            dark = _cell_darkness(grid, r, c) if c < cols else 0.0
            should = dark > threshold

            if should:
                x = c * spacing
                # Alternate up/down
                offset = amplitude * dark * spacing * (1 if c % 2 == 0 else -1)
                pts.append((x, y_base + offset))
                in_dark = True
            elif in_dark and pts:
                if len(pts) >= 2:
                    paths.append(Path(pts))
                pts = []
                in_dark = False

        if len(pts) >= 2:
            paths.append(Path(pts))

    return Drawing(paths)


# ─── Tiles ───────────────────────────────────────────────────────────────────

def tiles(grid: list[list[float]], spacing: float,
          threshold: float = 0.15) -> Drawing:
    """Rectangular tiles of varying size based on darkness.

    Dark areas = small dense tiles, light areas = large sparse tiles.
    """
    rows, cols = _grid_dims(grid)
    paths = []

    # Process in blocks
    block = max(2, int(3))  # 3x3 sampling blocks

    for r in range(0, rows - block, block):
        for c in range(0, cols - block, block):
            # Average darkness in block
            total = 0.0
            for dr in range(block):
                for dc in range(block):
                    rr, cc = r + dr, c + dc
                    if rr < rows and cc < cols:
                        total += _cell_darkness(grid, rr, cc)
            dark = total / (block * block)

            if dark < threshold:
                continue

            # Tile size inversely proportional to darkness
            tile_size = spacing * block * (1.0 - dark * 0.7)
            cx = (c + block / 2) * spacing
            cy = (rows - 1 - r - block / 2) * spacing
            half = tile_size / 2

            rect = [
                (cx - half, cy - half),
                (cx + half, cy - half),
                (cx + half, cy + half),
                (cx - half, cy + half),
                (cx - half, cy - half),
            ]
            paths.append(Path(rect))

    return Drawing(paths)


# ─── Scribble (random chaotic lines) ─────────────────────────────────────────

def scribble(grid: list[list[float]], spacing: float,
             threshold: float = 0.15, seed: int = 42,
             density: int = 4) -> Drawing:
    """Chaotic overlapping scribble lines like hand-drawn sketch.

    Fills dark areas with short, overlapping random strokes creating
    an organic, hand-drawn look.
    """
    rows, cols = _grid_dims(grid)
    rng = random.Random(seed)
    paths = []

    for r in range(rows):
        for c in range(cols):
            dark = _cell_darkness(grid, r, c)
            if dark < threshold:
                continue
            cx, cy = _cell_to_mm(r, c, rows, spacing)
            n_strokes = int(dark * density)
            for _ in range(n_strokes):
                half = spacing * 0.4
                x1 = cx + rng.uniform(-half, half)
                y1 = cy + rng.uniform(-half, half)
                x2 = cx + rng.uniform(-half, half)
                y2 = cy + rng.uniform(-half, half)
                paths.append(Path([(x1, y1), (x2, y2)]))

    return Drawing(paths)


# ─── Contour (isolines) ──────────────────────────────────────────────────────

def contour(grid: list[list[float]], spacing: float,
            threshold: float = 0.1, levels: int = 5) -> Drawing:
    """Draw contour/isoline lines at fixed darkness levels.

    Creates a topographic-map aesthetic similar to elevation contours.
    """
    rows, cols = _grid_dims(grid)
    paths = []
    step = 1.0 / max(levels, 1)

    for level in range(1, levels + 1):
        target_dark = level * step
        band = step * 0.3  # tolerance around target

        for r in range(rows):
            y = (rows - 1 - r) * spacing
            seg_start = None

            for c in range(cols + 1):
                dark = _cell_darkness(grid, r, c) if c < cols else -1
                in_band = abs(dark - target_dark) < band

                if in_band and seg_start is None:
                    seg_start = (c * spacing, y)
                elif not in_band and seg_start is not None:
                    paths.append(Path([seg_start, (c * spacing, y)]))
                    seg_start = None

            if seg_start is not None:
                paths.append(Path([seg_start, (cols * spacing, y)]))

    return Drawing(paths)


# ─── Waves (Fresnel-like concentric arcs) ─────────────────────────────────────

def waves(grid: list[list[float]], spacing: float,
          width_mm: float, height_mm: float,
          threshold: float = 0.1, frequency: float = 0.5) -> Drawing:
    """Horizontal wave lines with amplitude modulated by darkness.

    Darker areas get larger amplitude waves, creating a water-like
    or fabric-like texture.
    """
    rows, cols = _grid_dims(grid)
    paths = []
    freq = 2 * math.pi * frequency / spacing

    for r in range(rows):
        y_base = (rows - 1 - r) * spacing
        pts = []
        in_dark = False

        for c in range(cols + 1):
            dark = _cell_darkness(grid, r, c) if c < cols else 0.0
            should = dark > threshold

            if should:
                x = c * spacing
                amp = dark * spacing * 0.5
                y = y_base + math.sin(x * freq) * amp
                pts.append((x, y))
                in_dark = True
            elif in_dark and pts:
                if len(pts) >= 2:
                    paths.append(Path(pts))
                pts = []
                in_dark = False

        if len(pts) >= 2:
            paths.append(Path(pts))

    return Drawing(paths)


# ─── Hexagon (honeycomb) ──────────────────────────────────────────────────────

def hexagon(grid: list[list[float]], spacing: float,
            threshold: float = 0.1) -> Drawing:
    """Hexagonal honeycomb grid with cell size based on darkness.

    Dark areas = small dense hexagons, light areas = large sparse ones.
    """
    rows, cols = _grid_dims(grid)
    paths = []
    hex_w = spacing * 1.5
    hex_h = spacing * math.sqrt(3)

    for r in range(0, rows, 2):
        for c in range(0, cols, 2):
            dark = _cell_darkness(grid, r, c)
            if dark < threshold:
                continue

            cx = c * spacing
            cy = (rows - 1 - r) * spacing
            radius = dark * spacing * 0.45
            if radius < 0.2:
                continue

            # Regular hexagon
            pts = []
            for i in range(6):
                a = math.pi / 3 * i
                pts.append((
                    round(cx + radius * math.cos(a), 4),
                    round(cy + radius * math.sin(a), 4),
                ))
            pts.append(pts[0])  # close
            paths.append(Path(pts))

    return Drawing(paths)


# ─── Converter Registry ─────────────────────────────────────────────────────

CONVERTERS = {
    "hatching": hatching,
    "cross-hatching": cross_hatching,
    "halftone": halftone,
    "stipple": stipple,
    "spiral": spiral,
    "flow-field": flow_field,
    "meandering": meandering,
    "edge-detect": edge_detect,
    "dots": dots,
    "concentric": concentric,
    "woodcut": woodcut,
    "zigzag": zigzag,
    "tiles": tiles,
    "scribble": scribble,
    "contour": contour,
    "waves": waves,
    "hexagon": hexagon,
}
