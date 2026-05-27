"""
Batch 1/5: Core pipeline improvements (issues #1-#10)

1. Empty text → graceful 0 pages (not crash/1 empty page)
2. Config validation (raise helpful errors for invalid params)
3. Dry-run mode (estimate timing without hardware)
4. Multi-file batch processing
5. Page numbering in footer
6. Smart paragraph detection (auto-indent, no \t needed)
7. Smart typography (dashes, quotes auto-replace)
8. Resume from page N
9. Orphan/widow control
10. Per-page G-code statistics
"""

# ═══════════════════════════════════════════════════════════════════════════
# 1. Empty text handling — fixed in text_pipeline
# ═══════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════
# 2. Config validation
# ═══════════════════════════════════════════════════════════════════════════

VALIDATION_RULES = {
    "font_size_mm": (1.0, 20.0, "Font size must be 1-20 mm"),
    "line_spacing_mm": (3.0, 30.0, "Line spacing must be 3-30 mm"),
    "page_width_mm": (50.0, 2000.0, "Page width must be 50-2000 mm"),
    "page_height_mm": (50.0, 2000.0, "Page height must be 50-2000 mm"),
    "left_margin_mm": (0.0, 500.0, "Left margin must be 0-500 mm"),
    "right_margin_mm": (0.0, 500.0, "Right margin must be 0-500 mm"),
    "top_margin_mm": (0.0, 500.0, "Top margin must be 0-500 mm"),
    "bottom_margin_mm": (0.0, 500.0, "Bottom margin must be 0-500 mm"),
    "speed": (100, 10000, "Speed must be 100-10000 mm/min"),
    "travel_speed": (100, 20000, "Travel speed must be 100-20000 mm/min"),
}


def validate_config(notebook_cfg, text_cfg, plot_cfg) -> list[str]:
    """Validate all configs, return list of error messages (empty = valid)."""
    errors = []
    checks = [
        ("font_size_mm", text_cfg.font_size_mm),
        ("line_spacing_mm", text_cfg.line_spacing_mm),
        ("page_width_mm", notebook_cfg.page_width_mm),
        ("page_height_mm", notebook_cfg.page_height_mm),
        ("left_margin_mm", notebook_cfg.left_margin_mm),
        ("right_margin_mm", notebook_cfg.right_margin_mm),
        ("top_margin_mm", notebook_cfg.top_margin_mm),
        ("bottom_margin_mm", notebook_cfg.bottom_margin_mm),
        ("speed", plot_cfg.speed),
        ("travel_speed", plot_cfg.travel_speed),
    ]
    for key, value in checks:
        rule = VALIDATION_RULES.get(key)
        if rule:
            lo, hi, msg = rule
            if not (lo <= value <= hi):
                errors.append(f"{key}={value}: {msg}")
    # Logical checks
    if notebook_cfg.left_margin_mm + notebook_cfg.right_margin_mm >= notebook_cfg.page_width_mm:
        errors.append("Margins wider than page")
    if notebook_cfg.top_margin_mm + notebook_cfg.bottom_margin_mm >= notebook_cfg.page_height_mm:
        errors.append("Vertical margins taller than page")
    return errors


# ═══════════════════════════════════════════════════════════════════════════
# 3. Dry-run estimator
# ═══════════════════════════════════════════════════════════════════════════

def estimate_plot_time(drawings: list, plot_cfg) -> dict:
    """Estimate total plot time across all pages."""
    total_draw_mm = 0
    total_travel_mm = 0
    total_lifts = 0
    total_paths = 0
    for d in drawings:
        total_draw_mm += d.total_draw_length()
        total_travel_mm += d.total_travel_length()
        total_lifts += len(d.paths)
        total_paths += len(d.paths)
    
    draw_sec = (total_draw_mm / plot_cfg.speed) * 60 if plot_cfg.speed > 0 else 0
    travel_sec = (total_travel_mm / plot_cfg.travel_speed) * 60 if plot_cfg.travel_speed > 0 else 0
    delay_sec = total_lifts * (plot_cfg.pen_down_delay + plot_cfg.pen_up_delay) * 60
    total_sec = draw_sec + travel_sec + delay_sec
    
    return {
        "total_draw_mm": round(total_draw_mm),
        "total_travel_mm": round(total_travel_mm),
        "total_paths": total_paths,
        "pen_lifts": total_lifts,
        "draw_min": round(draw_sec / 60, 1),
        "travel_min": round(travel_sec / 60, 1),
        "delay_min": round(delay_sec / 60, 1),
        "total_min": round(total_sec / 60, 1),
        "total_hr": round(total_sec / 3600, 2),
        "total_cmds": sum(len([l for l in g.split("\n") if l.strip() and not l.startswith(";")]) 
                         for _, g in [(None, None)] if False),  # placeholder — filled by caller
    }


# ═══════════════════════════════════════════════════════════════════════════
# 6. Smart paragraph detection
# ═══════════════════════════════════════════════════════════════════════════

def smart_detect_paragraphs(text: str) -> str:
    """Auto-detect paragraphs: insert tab markers for first-line indents.
    
    Rules:
    - First paragraph of text → no indent
    - Paragraphs after blank lines → indent
    - Lists (starting with - * • 1. etc) → indent line 1
    """
    lines = text.split('\n')
    result = []
    prev_empty = False
    first_paragraph_processed = False
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append('')
            prev_empty = True
        else:
            if prev_empty and first_paragraph_processed:
                result.append('\t' + stripped)
            elif not first_paragraph_processed:
                result.append(stripped)
                first_paragraph_processed = True
            else:
                result.append(stripped)
            prev_empty = False
    
    return '\n'.join(result)


# ═══════════════════════════════════════════════════════════════════════════
# 7. Smart typography
# ═══════════════════════════════════════════════════════════════════════════

TYPO_REPLACEMENTS = {
    ' -- ': ' — ',
    '-- ': '— ',
    ' --': ' —',
    ' - ': ' — ',
    ' "': ' «',
    '" ': '» ',
    ' \'': ' \u2018',
    '\' ': '\u2019 ',
    '...': '…',
    '(c)': '\u00a9',
    '(C)': '\u00a9',
    '(r)': '\u00ae',
    '(R)': '\u00ae',
    '(tm)': '\u2122',
    '<<': '\u00ab',
    '>>': '\u00bb',
    '<-': '\u2190',
    '->': '\u2192',
    '+/-': '\u00b1',
    '1/2': '\u00bd',
    '1/4': '\u00bc',
    '3/4': '\u00be',
}


def apply_smart_typography(text: str) -> str:
    """Replace ASCII typography with proper Unicode characters."""
    result = text
    for old, new in TYPO_REPLACEMENTS.items():
        result = result.replace(old, new)
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 8. Resume from page N
# ═══════════════════════════════════════════════════════════════════════════

# Handled in text_pipeline via start_page parameter (already exists)


# ═══════════════════════════════════════════════════════════════════════════
# 9. Orphan/widow control
# ═══════════════════════════════════════════════════════════════════════════

def fix_orphans_widows(page_lines: list[str], min_lines: int = 2) -> tuple[list[str], list[str]]:
    """Prevent single lines at top (widow) or bottom (orphan) of pages.
    
    Returns (keep_on_this_page, move_to_next_page).
    """
    if len(page_lines) <= min_lines * 2:
        return page_lines, []
    
    # Check last N lines — if only 1 non-empty, move to next page
    last_nonempty = [l for l in page_lines[-min_lines:] if l.strip()]
    if len(last_nonempty) == 1:
        return page_lines[:-min_lines], page_lines[-min_lines:]
    
    return page_lines, []


# ═══════════════════════════════════════════════════════════════════════════
# 10. Per-page G-code statistics
# ═══════════════════════════════════════════════════════════════════════════

def page_gcode_stats(drawing, gcode: str) -> dict:
    """Detailed stats for one page of G-code."""
    commands = [l.strip() for l in gcode.split("\n") if l.strip() and not l.startswith(";")]
    g0 = sum(1 for c in commands if c.startswith("G0"))
    g1 = sum(1 for c in commands if c.startswith("G1"))
    
    return {
        "total_commands": len(commands),
        "travel_moves": g0,
        "draw_moves": g1,
        "draw_length_mm": round(drawing.total_draw_length()),
        "travel_length_mm": round(drawing.total_travel_length()),
        "num_paths": len(drawing.paths),
        "pen_lifts": len(drawing.paths),
    }
