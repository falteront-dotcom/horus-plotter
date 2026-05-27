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
from .extras import (
    BatchQueue, ResumeCheckpoint,
    draw_box, draw_horizontal_rule, draw_strikethrough, draw_underline,
    draw_watermark, generate_toc, render_bullet_point,
    render_checkbox, render_numbered_marker,
    subscript_baseline, superscript_baseline,
)
from .ultra_core import (
    Bounds, CalibrationData, GrblPrecisionConfig, PenProfile,
    apply_calibration, calibrate_from_measured,
    compute_drawing_bounds, compute_junction_speed, compute_pressure,
    drawing_quality_score, dry_run_estimate,
    export_dxf, export_hpgl,
    generate_calibration_grid, generate_calibration_square,
    generate_grbl_config_gcode, generate_pen_change_gcode,
    get_kerning, hilbert_order,
    optimize_2opt, optimize_paths_full,
    smooth_path, validate_gcode_bounds,
    hyphenate_word, justify_text, detect_rivers, apply_ligatures,
)
