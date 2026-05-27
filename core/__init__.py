"""Core module: image → path extraction → path optimization → G-code.
Also: text → notebook pages → G-code."""

from __future__ import annotations

from .exceptions import (
    ConfigError,
    ConverterError,
    EmptyDocumentError,
    ImageLoadError,
    PlotterError,
    UnsupportedFormatError,
)
from .converters import CONVERTERS
from .font_data import FONT_MAP, get_char_definition, supported_chars
from .fonts import DIMENSION_PX, LABEL_PX, LEGEND_PX, TITLE_PX, resolve_font
from .gcode import PlotConfig, drawing_to_gcode, drawing_to_preview, gcode_stats
from .notebook import (
    NotebookConfig,
    PageLayout,
    generate_notebook_background,
    generate_margin_line,
    generate_ruled_lines,
    get_line_y,
    layout_pages,
)
from .paths import Drawing, Path, optimize
from .pipeline import image_to_gcode
from .preprocessing import preprocess_image
from .text_engine import HandwritingRenderer, TextConfig, text_to_drawing
from .text_pipeline import full_text_pipeline, notebook_page_to_gcode, text_to_notebook_drawing

__all__ = [
    # Exceptions
    "ConfigError",
    "ConverterError",
    "Drawing",
    "EmptyDocumentError",
    "FONT_MAP",
    "HandwritingRenderer",
    "ImageLoadError",
    "NotebookConfig",
    "PageLayout",
    "Path",
    "PlotConfig",
    "PlotterError",
    "TextConfig",
    "UnsupportedFormatError",
    "drawing_to_gcode",
    "drawing_to_preview",
    "full_text_pipeline",
    "gcode_stats",
    "generate_margin_line",
    "generate_notebook_background",
    "generate_ruled_lines",
    "get_char_definition",
    "get_line_y",
    "image_to_gcode",
    "layout_pages",
    "notebook_page_to_gcode",
    "optimize",
    "preprocess_image",
    "supported_chars",
    "text_to_drawing",
    "text_to_notebook_drawing",
]
