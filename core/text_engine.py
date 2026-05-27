"""
Text → Drawing engine: converts text to plotter paths using the handwriting font.

renders a string of text into a Drawing using the stroke-based handwriting font,
supporting soft-wrapping, indentation, and multi-page output.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from .font_data import FONT_MAP, get_char_definition, _DEFAULT
from .paths import Drawing, Path


# ─── Configuration ──────────────────────���───────────────────────────────────

@dataclass
class TextConfig:
    font_size_mm: float = 5.0         # character height
    char_spacing_mm: float = 0.8      # extra space between characters
    word_spacing_mm: float = 2.0      # space width between words
    paragraph_indent_mm: float = 8.0  # first-line indent
    line_spacing_mm: float = 8.0      # vertical distance between lines
    slant_angle: float = 0.0          # italic slant in degrees (not yet implemented)
    variability: float = 0.15         # random variation for natural look (0-1)
    seed: int = 0                     # random seed (0 = random each time)


# ─── Renderer ────────────��──────────────────────────────────────────────────

class HandwritingRenderer:
    """Renders text to stroke paths using the built-in handwriting font."""

    def __init__(self, config: Optional[TextConfig] = None):
        self.cfg = config or TextConfig()

    def render_char(self, ch: str, x_mm: float, y_mm: float,
                    rng: Optional[random.Random] = None) -> list[Path]:
        """Render a single character at (x_mm, y_mm) baseline.

        Y is the BASELINE (bottom of letters). Returns list of Paths.
        """
        strokes, width, dots = get_char_definition(ch)
        fs = self.cfg.font_size_mm
        paths = []

        if rng is None:
            rng = random.Random(self.cfg.seed)

        # Random slanted offset per char for natural look
        wobble_x = (rng.random() - 0.5) * self.cfg.variability * fs * 0.3
        wobble_y = (rng.random() - 0.5) * self.cfg.variability * fs * 0.2

        # Convert strokes to mm paths
        for stroke in strokes:
            if len(stroke) < 2:
                continue
            pts = []
            for sx, sy in stroke:
                # Y is inverted: font coords go from bottom (descender) to top (ascender)
                # In the font data, y=0 is baseline, y=1 is top of tall letters
                # In plotter coords, we want y to increase UP the page
                pt_x = x_mm + sx * fs + wobble_x
                pt_y = y_mm + sy * fs + wobble_y
                pts.append((pt_x, pt_y))
            if len(pts) >= 2:
                paths.append(Path(pts))

        # Render dots (for i, j, !, ?, :, ;, ё, й)
        for dx, dy in dots:
            px = x_mm + dx * fs + wobble_x
            py = y_mm + dy * fs + wobble_y
            # Small circle
            d = fs * 0.08
            circle = [
                (px + d, py), (px, py + d), (px - d, py), (px, py - d), (px + d, py)
            ]
            paths.append(Path(circle))

        return paths

    def char_width_mm(self, ch: str) -> float:
        """Return the advance width of a character in mm."""
        _, width, _ = get_char_definition(ch)
        return width * self.cfg.font_size_mm + self.cfg.char_spacing_mm

    def render_word(self, word: str, x_mm: float, y_mm: float,
                    rng: random.Random) -> tuple[list[Path], float]:
        """Render a word, return paths and total width."""
        all_paths = []
        cx = x_mm
        for ch in word:
            all_paths.extend(self.render_char(ch, cx, y_mm, rng))
            cx += self.char_width_mm(ch)
        return all_paths, cx - x_mm

    def render_text(self, text: str,
                    x_start: float = 0.0,
                    y_start: float = 0.0,
                    max_width_mm: float = 180.0) -> tuple[Drawing, float]:
        """Render multi-line text with soft-wrapping.

        Starting from (x_start, y_start) which is the TOP of the first line.
        Y increases DOWN the page (plotter coordinate: y=0 is top).

        Args:
            text: The text to render.
            x_start: X offset for the first line.
            y_start: Y offset for the first line (top of text block).
            max_width_mm: Maximum line width before wrapping.

        Returns:
            (Drawing, total_height_mm) — the rendered paths and total height used.
        """
        rng = random.Random(self.cfg.seed) if self.cfg.seed else random.Random()

        lines = self._wrap_text(text, max_width_mm)
        all_paths = []
        current_y = y_start

        for i, line in enumerate(lines):
            words = line.split()
            if not words:
                current_y += self.cfg.line_spacing_mm
                continue

            x = x_start
            # First-line indent for paragraphs (detected by leading tab or indent flag)
            # We don't auto-detect paragraphs here — caller handles that

            for j, word in enumerate(words):
                paths, w = self.render_word(word, x, current_y, rng)
                all_paths.extend(paths)
                x += w + self.cfg.word_spacing_mm

            current_y += self.cfg.line_spacing_mm

        # Calculate symbol width in mm for space
        total_width = max_width_mm  # approximate
        total_height = current_y - y_start

        return Drawing(all_paths), total_height

    def measure_char(self, ch: str) -> float:
        """Return the mm width of a single character."""
        return self.char_width_mm(ch)

    def _wrap_text(self, text: str, max_width_mm: float) -> list[str]:
        """Soft-wrap text into lines that fit within max_width_mm."""
        lines = []
        for paragraph in text.split('\n'):
            words = paragraph.split()
            if not words:
                lines.append('')
                continue

            current_line = ''
            current_width = 0.0

            for word in words:
                word_width = sum(self.measure_char(ch) for ch in word)
                space_width = self.cfg.word_spacing_mm if current_line else 0.0

                if current_width + space_width + word_width <= max_width_mm:
                    current_line += (' ' if current_line else '') + word
                    current_width += space_width + word_width
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
                    current_width = word_width

            if current_line:
                lines.append(current_line)

        return lines


# ─── Convenience function ───────────────────────────────────────────────────

def text_to_drawing(text: str, cfg: TextConfig,
                    x_start: float = 0.0, y_start: float = 0.0,
                    max_width_mm: float = 180.0) -> tuple[Drawing, float]:
    """Convert text to a Drawing using the handwriting font."""
    renderer = HandwritingRenderer(cfg)
    return renderer.render_text(text, x_start, y_start, max_width_mm)
