"""Core module for Horus Plotter — image + text → G-code."""

from __future__ import annotations

from .exceptions import (
    ConfigError, ConverterError, EmptyDocumentError,
    ImageLoadError, PlotterError, UnsupportedFormatError,
)
from .converters import CONVERTERS
from .fonts import FONTS, FONT_DISPLAY_NAMES, get_font, list_fonts
from .font_data import FONT_MAP, get_char_definition, supported_chars
from .gcode import PlotConfig, drawing_to_gcode, drawing_to_preview, gcode_stats
from .notebook import (
    NotebookConfig, PageLayout,
    generate_notebook_background, generate_margin_line,
    generate_ruled_lines, get_line_y, layout_pages,
)
from .paths import Drawing, Path, optimize
from .pipeline import image_to_gcode
from .preprocessing import preprocess_image
from .text_engine import HandwritingRenderer, TextConfig, text_to_drawing
from .text_pipeline import full_text_pipeline, notebook_page_to_gcode, text_to_notebook_drawing
from .vision import (
    PageCalibration, WritingCorrection,
    auto_optimize_layout, calibrate_page_from_image,
    compute_writing_correction, optimize_line_density, simulate_page_scan,
)

__all__ = [
    "CONVERTERS",
    "ConfigError",
    "ConverterError",
    "Drawing",
    "EmptyDocumentError",
    "FONT_DISPLAY_NAMES",
    "FONTS",
    "FONT_MAP",
    "HandwritingRenderer",
    "ImageLoadError",
    "NotebookConfig",
    "PageCalibration",
    "PageLayout",
    "Path",
    "PlotConfig",
    "PlotterError",
    "TextConfig",
    "UnsupportedFormatError",
    "WritingCorrection",
    "auto_optimize_layout",
    "calibrate_page_from_image",
    "compute_writing_correction",
    "drawing_to_gcode",
    "drawing_to_preview",
    "full_text_pipeline",
    "gcode_stats",
    "generate_margin_line",
    "generate_notebook_background",
    "generate_ruled_lines",
    "get_char_definition",
    "get_font",
    "get_line_y",
    "image_to_gcode",
    "layout_pages",
    "list_fonts",
    "notebook_page_to_gcode",
    "optimize",
    "optimize_line_density",
    "preprocess_image",
    "simulate_page_scan",
    "supported_chars",
    "text_to_drawing",
    "text_to_notebook_drawing",
]
