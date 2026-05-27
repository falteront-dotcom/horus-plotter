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
from .improvements import (
    apply_smart_typography, estimate_plot_time, fix_orphans_widows,
    page_gcode_stats, smart_detect_paragraphs, validate_config,
)
from .features import (
    PlotHistoryDB, calculate_plot_cost, detect_page_from_photo,
    export_as_html_preview, export_as_svg, score_page_quality,
    register_plugin, get_plugin, list_plugins,
)

__all__ = [
    "CONVERTERS", "ConfigError", "ConverterError", "Drawing",
    "EmptyDocumentError", "FONT_DISPLAY_NAMES", "FONTS", "FONT_MAP",
    "HandwritingRenderer", "ImageLoadError", "NotebookConfig",
    "PageCalibration", "PageLayout", "Path", "PlotConfig",
    "PlotHistoryDB", "PlotterError", "TextConfig", "UnsupportedFormatError",
    "WritingCorrection",
    "apply_smart_typography", "auto_optimize_layout",
    "calculate_plot_cost", "calibrate_page_from_image",
    "compute_writing_correction", "detect_page_from_photo",
    "drawing_to_gcode", "drawing_to_preview",
    "estimate_plot_time", "export_as_html_preview", "export_as_svg",
    "fix_orphans_widows", "full_text_pipeline",
    "gcode_stats", "generate_margin_line", "generate_notebook_background",
    "generate_ruled_lines", "get_char_definition", "get_font",
    "get_line_y", "get_plugin", "image_to_gcode", "layout_pages",
    "list_fonts", "list_plugins", "notebook_page_to_gcode", "optimize",
    "optimize_line_density", "page_gcode_stats", "preprocess_image",
    "register_plugin", "score_page_quality", "simulate_page_scan",
    "smart_detect_paragraphs", "supported_chars", "text_to_drawing",
    "text_to_notebook_drawing", "validate_config",
]
