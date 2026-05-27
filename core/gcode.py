"""Drawing → G-code conversion, preview rendering, and statistics."""

from __future__ import annotations

import base64
import io
import math
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from .fonts import DIMENSION_PX, LABEL_PX, LEGEND_PX, resolve_font
from .paths import Drawing, Path


# ─── Preview colour constants ───────────────────────────────────────────────

_BG_DARK = (22, 22, 30)
_SHADOW = (12, 12, 18)
_PAPER = (250, 248, 242)
_PAPER_OUTLINE = (160, 160, 170)
_GRID = (215, 213, 207)
_MARGIN = (180, 195, 230)
_DIM = (150, 150, 170)
_DIM_UNIT = (110, 110, 130)
_DIM_BOX = (100, 90, 160)
_DIM_LABEL = (140, 130, 200)
_DRAW = (70, 50, 200)
_TRAVEL = (160, 70, 70)
_LEGEND_TEXT = (140, 140, 160)

_LABEL_MARGIN = 30
_GRID_STEP_MM = 50
_MARGIN_MM = 10
_SHADOW_OFF = 4
_DASH_LEN = 4


@dataclass
class PlotConfig:
    style: str = "hatching"
    width_mm: float = 200
    spacing_mm: float = 3
    speed: int = 3000
    travel_speed: int = 8000
    pen_down_z: float = 5
    pen_up_z: float = 0
    threshold: float = 0.15
    join_tolerance: float = 0.5
    simplify_epsilon: float = 0.1
    pen_down_delay: float = 0.0
    pen_up_delay: float = 0.0
    invert: bool = False
    auto_invert: bool = True
    brightness: float = 1.0
    contrast: float = 1.0
    blur: float = 0.0
    work_area_x: float = 300.0
    work_area_y: float = 300.0


def drawing_to_gcode(drawing: Drawing, cfg: PlotConfig,
                     offset_x: float = 0.0, offset_y: float = 0.0) -> str:
    """Convert a Drawing to G-code string for GRBL.

    offset_x/y are computed by the pipeline to center the drawing
    within the work area. All coordinates are shifted by these offsets.
    """
    lines = [
        "; Horus Plotter",
        "G21 ; mm",
        "G90 ; absolute",
        f"G0 Z{cfg.pen_up_z} ; pen up",
        "G0 X0 Y0 ; home",
    ]

    for path in drawing.paths:
        if path.is_empty():
            continue

        # Move to start (pen up, travel speed)
        sx = path.start[0] + offset_x
        sy = path.start[1] + offset_y
        lines.append(f"G0 X{sx:.2f} Y{sy:.2f} F{cfg.travel_speed}")

        # Pen down
        lines.append(f"G1 Z{cfg.pen_down_z} F{cfg.speed}")
        if cfg.pen_down_delay > 0:
            lines.append(f"G4 P{cfg.pen_down_delay:.3f}")

        # Draw path
        for px, py in path.points[1:]:
            px += offset_x
            py += offset_y
            lines.append(f"G1 X{px:.2f} Y{py:.2f} F{cfg.speed}")

        # Pen up
        lines.append(f"G0 Z{cfg.pen_up_z}")
        if cfg.pen_up_delay > 0:
            lines.append(f"G4 P{cfg.pen_up_delay:.3f}")

    lines.extend([
        f"G0 Z{cfg.pen_up_z}",
        "G0 X0 Y0",
        "M2 ; end",
    ])

    return "\n".join(lines)


def drawing_to_preview(drawing: Drawing, cw: int = 400, ch: int = 400,
                       show_travel: bool = True,
                       work_area_x: float = 300, work_area_y: float = 300) -> str:
    """Render a Drawing to base64 PNG — modern preview with paper sheet.

    Features:
    - Dark background with subtle grid
    - Paper sheet with drop shadow
    - Dashed work area boundary
    - Blue margin lines
    - Dimension labels (mm)
    - Purple draw moves, dim red travel moves
    - Color legend
    """
    if not drawing.paths:
        return ""

    # Compute drawing bounding box
    all_x = [x for p in drawing.paths for x, _ in p.points]
    all_y = [y for p in drawing.paths for _, y in p.points]
    if not all_x:
        return ""

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    actual_w = max_x - min_x
    actual_h = max_y - min_y

    # Scale paper to fit in the preview canvas with margin for labels
    sc = min(
        (cw - _LABEL_MARGIN * 2) / max(1, work_area_x),
        (ch - _LABEL_MARGIN * 2) / max(1, work_area_y),
    )
    paper_px_w = work_area_x * sc
    paper_px_h = work_area_y * sc
    paper_ox = (cw - paper_px_w) / 2
    paper_oy = (ch - paper_px_h) / 2

    # Centering offset (same as pipeline uses)
    offset_x = (work_area_x - actual_w) / 2 - min_x
    offset_y = (work_area_y - actual_h) / 2 - min_y

    pimg = Image.new("RGB", (cw, ch), _BG_DARK)
    draw = ImageDraw.Draw(pimg)

    _draw_paper_sheet(draw, paper_ox, paper_oy, paper_px_w, paper_px_h)
    _draw_grid(draw, paper_ox, paper_oy, work_area_x, work_area_y, sc)
    _draw_margin_lines(draw, paper_ox, paper_oy, paper_px_w, paper_px_h, sc)
    _draw_dimension_labels(draw, paper_ox, paper_oy, work_area_x, work_area_y, sc)
    _draw_drawing_bounds(
        draw, min_x, min_y, max_x, max_y, offset_x, offset_y, sc, paper_ox, paper_oy
    )
    _draw_paths(draw, drawing, offset_x, offset_y, sc, paper_ox, paper_oy, show_travel)
    _draw_origin_marker(draw, paper_ox, paper_oy, paper_px_h)
    _draw_legend(draw, paper_ox, paper_oy, paper_px_w, paper_px_h)

    buf = io.BytesIO()
    pimg.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ─── Preview rendering helpers ──────────────────────────────────────────────

def _draw_paper_sheet(
    draw: ImageDraw.ImageDraw,
    ox: float, oy: float, w: float, h: float
) -> None:
    """Draw paper background with drop shadow."""
    # Drop shadow
    draw.rectangle(
        [ox + _SHADOW_OFF, oy + _SHADOW_OFF,
         ox + w + _SHADOW_OFF, oy + h + _SHADOW_OFF],
        fill=_SHADOW,
    )
    # Paper
    draw.rectangle(
        [ox, oy, ox + w, oy + h],
        fill=_PAPER, outline=_PAPER_OUTLINE, width=1,
    )


def _draw_grid(
    draw: ImageDraw.ImageDraw,
    ox: float, oy: float,
    paper_w: float, paper_h: float,
    sc: float,
) -> None:
    """Draw subtle grid lines every 50 mm."""
    for mm in range(_GRID_STEP_MM, int(paper_w), _GRID_STEP_MM):
        px = ox + mm * sc
        draw.line([(px, oy), (px, oy + paper_h * sc)], fill=_GRID, width=1)
    for mm in range(_GRID_STEP_MM, int(paper_h), _GRID_STEP_MM):
        py = oy + mm * sc
        draw.line([(ox, py), (ox + paper_w * sc, py)], fill=_GRID, width=1)


def _draw_margin_lines(
    draw: ImageDraw.ImageDraw,
    ox: float, oy: float, w: float, h: float, sc: float
) -> None:
    """Draw blue margin lines (like notebook paper)."""
    margin_px = _MARGIN_MM * sc
    draw.line(
        [(ox + margin_px, oy), (ox + margin_px, oy + h)],
        fill=_MARGIN, width=1,
    )
    draw.line(
        [(ox, oy + margin_px), (ox + w, oy + margin_px)],
        fill=_MARGIN, width=1,
    )


def _draw_dimension_labels(
    draw: ImageDraw.ImageDraw,
    ox: float, oy: float,
    paper_w: float, paper_h: float,
    sc: float,
) -> None:
    """Draw mm labels along the paper edges with tick marks."""
    font = resolve_font(DIMENSION_PX)
    tick = 4

    # X-axis labels (top) with tick marks
    for mm in range(0, int(paper_w) + 1, 100):
        px = ox + mm * sc
        draw.line([(px, oy), (px, oy + tick)], fill=_DIM, width=1)
        draw.text((px - 8, oy - 16), f"{mm}", fill=_DIM, font=font)

    # Y-axis labels (left) with tick marks
    for mm in range(0, int(paper_h) + 1, 100):
        py = oy + mm * sc
        draw.line([(ox, py), (ox + tick, py)], fill=_DIM, width=1)
        draw.text((ox - 30, py - 6), f"{mm}", fill=_DIM, font=font)

    # Unit labels
    draw.text((ox + paper_w * sc + 4, oy - 16), "мм", fill=_DIM_UNIT, font=font)
    draw.text((ox - 30, oy + paper_h * sc + 4), "мм", fill=_DIM_UNIT, font=font)


def _draw_drawing_bounds(
    draw: ImageDraw.ImageDraw,
    min_x: float, min_y: float, max_x: float, max_y: float,
    offset_x: float, offset_y: float,
    sc: float, paper_ox: float, paper_oy: float,
) -> None:
    """Draw a dashed rectangle around the actual drawing bounds."""
    x0 = (min_x + offset_x) * sc + paper_ox
    y0 = (min_y + offset_y) * sc + paper_oy
    x1 = (max_x + offset_x) * sc + paper_ox
    y1 = (max_y + offset_y) * sc + paper_oy

    for side in [
        [(x0, y0), (x1, y0)],
        [(x1, y0), (x1, y1)],
        [(x1, y1), (x0, y1)],
        [(x0, y1), (x0, y0)],
    ]:
        x_start, y_start = side[0]
        x_end, y_end = side[1]
        length = math.hypot(x_end - x_start, y_end - y_start)
        if length < 1:
            continue
        dx, dy = (x_end - x_start) / length, (y_end - y_start) / length
        pos = 0.0
        on = True
        while pos < length:
            seg = min(_DASH_LEN, length - pos)
            sx = x_start + dx * pos
            sy = y_start + dy * pos
            ex = x_start + dx * (pos + seg)
            ey = y_start + dy * (pos + seg)
            if on:
                draw.line([(sx, sy), (ex, ey)], fill=_DIM_BOX, width=1)
            on = not on
            pos += _DASH_LEN

    # Dimensions label
    font = resolve_font(DIMENSION_PX)
    dim_label = f"{max_x - min_x:.0f}×{max_y - min_y:.0f} мм"
    draw.text((x1 + 3, y1 + 2), dim_label, fill=_DIM_LABEL, font=font)


def _draw_paths(
    draw: ImageDraw.ImageDraw,
    drawing: Drawing,
    offset_x: float, offset_y: float,
    sc: float, paper_ox: float, paper_oy: float,
    show_travel: bool,
) -> None:
    """Draw the actual plotter paths and travel moves."""
    prev_end = None

    for path in drawing.paths:
        if len(path.points) < 2:
            continue
        scaled = [
            ((x + offset_x) * sc + paper_ox, (y + offset_y) * sc + paper_oy)
            for x, y in path.points
        ]

        if show_travel and prev_end is not None:
            draw.line([prev_end, scaled[0]], fill=_TRAVEL, width=1)

        draw.line(scaled, fill=_DRAW, width=1)
        prev_end = scaled[-1]


def _draw_origin_marker(
    draw: ImageDraw.ImageDraw,
    ox: float, oy: float,
    paper_px_h: float,
) -> None:
    """Draw origin (0,0) marker with crosshair and label."""
    font = resolve_font(LABEL_PX)
    size = 6
    x0 = ox
    y0 = oy + paper_px_h

    # Crosshair
    draw.line([(x0 - size, y0), (x0 + size, y0)], fill=(200, 60, 60), width=1)
    draw.line([(x0, y0 - size), (x0, y0 + size)], fill=(200, 60, 60), width=1)
    # Label
    draw.text((x0 - 12, y0 + 4), "0,0", fill=(200, 60, 60), font=font)


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    ox: float, oy: float,
    paper_px_w: float, paper_px_h: float,
) -> None:
    """Draw colour legend below the paper sheet."""
    font = resolve_font(LEGEND_PX)
    legend_y = oy + paper_px_h + 22  # moved down for origin marker
    legend_x = ox

    # Draw line sample
    draw.line(
        [(legend_x, legend_y + 5), (legend_x + 20, legend_y + 5)],
        fill=_DRAW, width=1,
    )
    draw.text((legend_x + 24, legend_y), "Рисование", fill=_LEGEND_TEXT, font=font)

    # Travel line sample
    draw.line(
        [(legend_x + 90, legend_y + 5), (legend_x + 110, legend_y + 5)],
        fill=_TRAVEL, width=1,
    )
    draw.text((legend_x + 114, legend_y), "Холостой", fill=_LEGEND_TEXT, font=font)


def gcode_stats(drawing: Drawing, cfg: PlotConfig) -> dict:
    """Calculate statistics about the planned plot.

    Returns dict with:
        pen_lifts: number of pen up/down cycles
        total_draw_mm: total distance with pen down
        total_travel_mm: total distance with pen up
        estimated_time_sec: rough time estimate
        num_paths: number of paths
    """
    num_paths = len(drawing.paths)
    pen_lifts = num_paths
    total_draw = drawing.total_draw_length()
    total_travel = drawing.total_travel_length()

    # Rough time estimate: draw at cfg.speed, travel at cfg.travel_speed
    draw_time = (total_draw / cfg.speed) * 60 if cfg.speed > 0 else 0
    travel_time = (total_travel / cfg.travel_speed) * 60 if cfg.travel_speed > 0 else 0
    pen_delay_time = pen_lifts * (cfg.pen_down_delay + cfg.pen_up_delay)
    estimated_sec = draw_time + travel_time + pen_delay_time

    return {
        "pen_lifts": pen_lifts,
        "total_draw_mm": round(total_draw, 1),
        "total_travel_mm": round(total_travel, 1),
        "estimated_time_sec": round(estimated_sec, 1),
        "num_paths": num_paths,
    }
