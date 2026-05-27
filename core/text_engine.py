"""Text rendering engine for Horus Plotter — multi-font handwriting."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from .fonts import get_font
from .paths import Drawing, Path


def _simple_line(a: tuple, b: tuple) -> list:
    return [a, b]


@dataclass
class TextConfig:
    font_name: str = "semyon_cursive"
    font_size_mm: float = 5.0
    char_spacing_mm: float = 0.8
    word_spacing_mm: float = 2.0
    paragraph_indent_mm: float = 8.0
    line_spacing_mm: float = 8.0
    variability: float = 0.15
    seed: int = 0


class HandwritingRenderer:
    """Renders text using any of the 5 built-in handwriting fonts."""

    def __init__(self, config: Optional[TextConfig] = None):
        self.cfg = config or TextConfig()
        self._font_map = get_font(self.cfg.font_name)
        self._default = ([_simple_line((.10, .05), (.50, .90))], .40, [])

    def set_font(self, font_name: str):
        self.cfg.font_name = font_name
        self._font_map = get_font(font_name)

    def _get_char_def(self, ch: str):
        return self._font_map.get(ch, self._default)

    def render_char(self, ch: str, x_mm: float, y_mm: float,
                    rng: Optional[random.Random] = None) -> list[Path]:
        strokes, width, dots = self._get_char_def(ch)
        fs = self.cfg.font_size_mm
        paths = []
        if rng is None:
            rng = random.Random(self.cfg.seed)
        wx = (rng.random() - 0.5) * self.cfg.variability * fs * 0.3
        wy = (rng.random() - 0.5) * self.cfg.variability * fs * 0.2
        for stroke in strokes:
            if len(stroke) < 2:
                continue
            pts = [(x_mm + sx * fs + wx, y_mm + sy * fs + wy)
                   for sx, sy in stroke]
            paths.append(Path(pts))
        for dx, dy in dots:
            px, py = x_mm + dx * fs + wx, y_mm + dy * fs + wy
            d = fs * 0.08
            paths.append(Path([(px + d, py), (px, py + d), (px - d, py),
                               (px, py - d), (px + d, py)]))
        return paths

    def char_width_mm(self, ch: str) -> float:
        _, width, _ = self._get_char_def(ch)
        return width * self.cfg.font_size_mm + self.cfg.char_spacing_mm

    def render_word(self, word: str, x_mm: float, y_mm: float,
                    rng: random.Random) -> tuple[list[Path], float]:
        all_paths = []
        cx = x_mm
        for ch in word:
            all_paths.extend(self.render_char(ch, cx, y_mm, rng))
            cx += self.char_width_mm(ch)
        return all_paths, cx - x_mm

    def render_text(self, text: str, x_start: float = 0.0,
                    y_start: float = 0.0,
                    max_width_mm: float = 180.0) -> tuple[Drawing, float]:
        rng = random.Random(self.cfg.seed) if self.cfg.seed else random.Random()
        lines = self._wrap_text(text, max_width_mm)
        all_paths = []
        current_y = y_start
        for line in lines:
            words = line.split()
            if not words:
                current_y += self.cfg.line_spacing_mm
                continue
            x = x_start
            for word in words:
                paths, w = self.render_word(word, x, current_y, rng)
                all_paths.extend(paths)
                x += w + self.cfg.word_spacing_mm
            current_y += self.cfg.line_spacing_mm
        return Drawing(all_paths), current_y - y_start

    def measure_char(self, ch: str) -> float:
        return self.char_width_mm(ch)

    def _wrap_text(self, text: str, max_width_mm: float) -> list[str]:
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
                space = self.cfg.word_spacing_mm if current_line else 0.0
                if current_width + space + word_width <= max_width_mm:
                    current_line += (' ' if current_line else '') + word
                    current_width += space + word_width
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
                    current_width = word_width
            if current_line:
                lines.append(current_line)
        return lines


def text_to_drawing(text: str, cfg: TextConfig, x_start: float = 0.0,
                    y_start: float = 0.0,
                    max_width_mm: float = 180.0) -> tuple[Drawing, float]:
    renderer = HandwritingRenderer(cfg)
    return renderer.render_text(text, x_start, y_start, max_width_mm)
