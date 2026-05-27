"""
Text pipeline: text → notebook pages → G-code for Horus Plotter.

Combines the handwriting renderer and notebook layout engine
to produce complete G-code for writing lectures in a notebook.
"""

from __future__ import annotations

import copy
from typing import Optional

from .notebook import (
    NotebookConfig,
    layout_pages,
    generate_notebook_background,
    generate_paragraph_indent_marker,
    PageLayout,
)
from .text_engine import HandwritingRenderer, TextConfig
from .paths import Drawing, Path, optimize
from .gcode import PlotConfig, drawing_to_gcode


def text_to_notebook_drawing(
    text: str,
    notebook_cfg: NotebookConfig,
    text_cfg: TextConfig,
    start_page: int = 0,
) -> list[tuple[int, Drawing]]:
    """Convert text into a sequence of notebook page Drawings.

    Each page includes:
      - Notebook background (margin line, ruled lines)
      - Handwriting text overlaid on ruled lines

    Args:
        text: The lecture text.
        notebook_cfg: Notebook layout parameters.
        text_cfg: Text rendering parameters.
        start_page: Page number to start from.

    Returns:
        List of (page_number, Drawing) tuples.
    """
    renderer = HandwritingRenderer(text_cfg)

    # Calculate characters per line
    avg_char_width = text_cfg.font_size_mm * 0.6  # ~60% of height
    chars_per_line = int(notebook_cfg.text_width / avg_char_width)

    # Split into pages
    pages = layout_pages(text, notebook_cfg, chars_per_line)

    results = []

    for page in pages:
        paths = []

        # 1. Notebook background
        bg = generate_notebook_background(notebook_cfg)
        paths.extend(bg.paths)

        # 2. Text lines
        y_offset = page.start_line_y

        for i, line in enumerate(page.lines):
            line_y = y_offset + i * notebook_cfg.line_spacing_mm

            if not line:
                continue

            # Check for paragraph indent
            if line.startswith('\t'):
                line = line[1:]
                # Draw indent marker
                indent_marker = generate_paragraph_indent_marker(notebook_cfg, line_y)
                paths.append(indent_marker)
                x_start = notebook_cfg.text_x_start + notebook_cfg.paragraph_indent_mm
            else:
                x_start = notebook_cfg.text_x_start

            # Render the line
            drawing, _ = renderer.render_text(
                line,
                x_start=x_start,
                y_start=line_y,
                max_width_mm=notebook_cfg.page_width_mm - notebook_cfg.right_margin_mm - x_start,
            )
            paths.extend(drawing.paths)

        results.append((start_page + page.page_index, Drawing(paths)))

    return results


def notebook_page_to_gcode(
    drawing: Drawing,
    plot_cfg: PlotConfig,
    page_number: int,
) -> str:
    """Convert a single notebook page Drawing to G-code.

    The drawing is NOT centered — notebook pages use absolute coordinates
    matching the page dimensions. Origin (0,0) = top-left of page.
    """
    # Optimize paths
    optimized = optimize(
        drawing,
        join_tolerance=plot_cfg.join_tolerance,
        simplify_epsilon=plot_cfg.simplify_epsilon,
    )

    gcode = drawing_to_gcode(optimized, plot_cfg, offset_x=0.0, offset_y=0.0)
    return gcode


def full_text_pipeline(
    text: str,
    notebook_cfg: Optional[NotebookConfig] = None,
    text_cfg: Optional[TextConfig] = None,
    plot_cfg: Optional[PlotConfig] = None,
    start_page: int = 0,
    smart_paragraphs: bool = True,
    smart_typo: bool = True,
) -> list[tuple[int, Drawing, str]]:
    """Full pipeline: text → notebook pages → (page_num, Drawing, G-code).

    Args:
        text: Raw lecture text.
        notebook_cfg: Notebook layout config.
        text_cfg: Text rendering config.
        plot_cfg: Plotter config.
        start_page: First page number (for resume).
        smart_paragraphs: Auto-detect paragraph breaks.
        smart_typo: Replace ASCII with Unicode typography.
    """
    nc = notebook_cfg or NotebookConfig()
    tc = text_cfg or TextConfig()
    pc = plot_cfg or PlotConfig()

    text = text.strip()
    if not text:
        return []  # Fix #1: empty text -> 0 pages

    if smart_typo:
        from .improvements import apply_smart_typography
        text = apply_smart_typography(text)

    if smart_paragraphs:
        from .improvements import smart_detect_paragraphs
        text = smart_detect_paragraphs(text)

    pages = text_to_notebook_drawing(text, nc, tc, start_page=start_page)

    results = []
    for page_num, drawing in pages:
        gcode = notebook_page_to_gcode(drawing, pc, page_num)
        results.append((page_num, drawing, gcode))

    return results
