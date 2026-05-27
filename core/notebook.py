"""
Notebook page layout engine — draws notebook pages with margins and ruled lines.

Generates Drawing paths for notebook pages:
  - Red margin line (left side, 25mm from edge)
  - Ruled horizontal lines (light blue)
  - Page borders (optional)
  - Top/bottom margins

Used by the text pipeline to create complete notebook pages with handwriting text
overlaid on ruled notebook paper.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .paths import Drawing, Path


# ─── Notebook layout parameters ─────────────────────────────────────────────

@dataclass
class NotebookConfig:
    """Physical notebook dimensions and layout preferences.

    All dimensions in millimetres.
    """
    page_width_mm: float = 210.0         # A4
    page_height_mm: float = 297.0        # A4
    left_margin_mm: float = 25.0         # red margin line position
    right_margin_mm: float = 10.0        # right margin
    top_margin_mm: float = 20.0          # top margin
    bottom_margin_mm: float = 20.0       # bottom margin
    line_spacing_mm: float = 8.0         # distance between ruled lines
    paragraph_indent_mm: float = 12.5    # first-line paragraph indent

    # Visual options
    draw_margin_line: bool = True        # red margin line
    draw_ruled_lines: bool = True        # horizontal ruled lines

    # Writeable area (computed)
    @property
    def text_x_start(self) -> float:
        """X position where text starts (right of margin line + small gap)."""
        return self.left_margin_mm + 2.5

    @property
    def text_width(self) -> float:
        """Available width for text."""
        return self.page_width_mm - self.left_margin_mm - self.right_margin_mm - 2.5

    @property
    def text_y_start(self) -> float:
        """Y position of the first text line (top margin + first line height)."""
        return self.top_margin_mm + self.line_spacing_mm

    @property
    def lines_per_page(self) -> int:
        """Number of ruled lines fit on one page."""
        available = self.page_height_mm - self.top_margin_mm - self.bottom_margin_mm
        return int(available / self.line_spacing_mm)

    @property
    def text_area_height(self) -> float:
        return self.page_height_mm - self.top_margin_mm - self.bottom_margin_mm


# ─── Notebook page generator ──────────────────────���─────────────────────────

def generate_margin_line(cfg: NotebookConfig) -> Path:
    """Generate the red margin line for one page."""
    return Path([
        (cfg.left_margin_mm, cfg.top_margin_mm),
        (cfg.left_margin_mm, cfg.page_height_mm - cfg.bottom_margin_mm),
    ])


def generate_ruled_lines(cfg: NotebookConfig) -> list[Path]:
    """Generate horizontal ruled lines for one page."""
    lines = []
    num_lines = cfg.lines_per_page

    for i in range(num_lines + 1):
        y = cfg.top_margin_mm + i * cfg.line_spacing_mm
        if y > cfg.page_height_mm - cfg.bottom_margin_mm:
            break
        # Stop at margin line on the left, right margin on the right
        x_start = cfg.left_margin_mm
        x_end = cfg.page_width_mm - cfg.right_margin_mm
        lines.append(Path([(x_start, y), (x_end, y)]))

    return lines


def generate_page_border(cfg: NotebookConfig) -> list[Path]:
    """Generate page border rectangle (optional)."""
    border = Path([
        (0, 0),
        (cfg.page_width_mm, 0),
        (cfg.page_width_mm, cfg.page_height_mm),
        (0, cfg.page_height_mm),
        (0, 0),
    ])
    return [border]


def generate_paragraph_indent_marker(cfg: NotebookConfig, y_mm: float) -> Path:
    """Generate a small indent marker at the start of a paragraph."""
    indent_x = cfg.text_x_start + cfg.paragraph_indent_mm
    return Path([(cfg.text_x_start, y_mm), (indent_x, y_mm)])


def generate_notebook_background(cfg: NotebookConfig) -> Drawing:
    """Generate the full notebook page background (margin + ruled lines).

    This is a "page skeleton" — the text will be overlaid on it.
    """
    paths = []

    # Red margin line
    if cfg.draw_margin_line:
        paths.append(generate_margin_line(cfg))

    # Ruled lines
    if cfg.draw_ruled_lines:
        paths.extend(generate_ruled_lines(cfg))

    return Drawing(paths)


def get_line_y(cfg: NotebookConfig, line_index: int) -> float:
    """Get the Y coordinate (top of the writing area) for a given line index.

    Line 0 is the first line at the top of the page.
    """
    return cfg.top_margin_mm + (line_index + 1) * cfg.line_spacing_mm


# ─── Page layout calculator ─────────────────────────────────────────────────

@dataclass
class PageLayout:
    """Layout of text on one notebook page."""
    page_index: int
    lines: list[str]            # text lines on this page
    start_line_y: float         # Y of first line
    end_line_y: float           # Y after last line


def layout_pages(text: str, cfg: NotebookConfig,
                 chars_per_line: int) -> list[PageLayout]:
    """Split text into pages based on notebook dimensions.

    Args:
        text: Raw text (can contain newlines).
        cfg: Notebook configuration.
        chars_per_line: Approximate characters per line.

    Returns:
        List of PageLayout objects.
    """
    pages = []
    current_lines: list[str] = []
    line_count = 0

    paragraphs = text.split('\n')

    for para_idx, para in enumerate(paragraphs):
        if not para.strip():
            # Empty paragraph = blank line
            if line_count < cfg.lines_per_page:
                current_lines.append('')
                line_count += 1
            else:
                pages.append(PageLayout(
                    page_index=len(pages),
                    lines=current_lines,
                    start_line_y=cfg.text_y_start,
                    end_line_y=cfg.text_y_start + cfg.line_spacing_mm * (len(current_lines) - 1),
                ))
                current_lines = ['']
                line_count = 1
            continue

        # Word-wrap the paragraph
        words = para.split()
        wrapped_lines = []
        current_line = ''
        current_width = 0

        for word in words:
            word_len = len(word)
            word_width = word_len + 1  # +1 for space

            if current_width + word_width > chars_per_line and current_line:
                wrapped_lines.append(current_line.strip())
                current_line = ''
                current_width = 0

            current_line += word + ' '
            current_width += word_width

        if current_line.strip():
            wrapped_lines.append(current_line.strip())

        # First line gets paragraph indent
        is_first = True

        for line in wrapped_lines:
            if line_count >= cfg.lines_per_page:
                # Start new page
                pages.append(PageLayout(
                    page_index=len(pages),
                    lines=current_lines,
                    start_line_y=cfg.text_y_start,
                    end_line_y=cfg.text_y_start + cfg.line_spacing_mm * (len(current_lines) - 1),
                ))
                current_lines = []
                line_count = 0

            indent_prefix = '\t' if is_first and para_idx > 0 else ''
            current_lines.append(indent_prefix + line)
            line_count += 1
            is_first = False

    # Last page
    if current_lines:
        pages.append(PageLayout(
            page_index=len(pages),
            lines=current_lines,
            start_line_y=cfg.text_y_start,
            end_line_y=cfg.text_y_start + cfg.line_spacing_mm * (len(current_lines) - 1),
        ))

    return pages
