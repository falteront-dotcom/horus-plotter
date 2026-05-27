"""
Neuro-vision engine for Horus Plotter — smart page alignment & layout correction.

Uses computer vision to:
  1. Detect notebook page boundaries (corners, edges)
  2. Find red margin line position 
  3. Detect ruled lines for alignment
  4. Auto-calibrate writing area to match physical notebook
  5. Preview what the plotter will actually draw via simulation

Heavy lifting done with numpy + PIL. No deep learning needed — 
classical CV is more reliable for printed lines on paper.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    Image = None  # type: ignore


@dataclass
class PageCalibration:
    """Detected notebook page geometry."""
    top_left: tuple[float, float]      # mm
    top_right: tuple[float, float]     # mm  
    bottom_left: tuple[float, float]   # mm
    bottom_right: tuple[float, float]  # mm
    margin_line_x: float               # mm from left edge
    line_positions: list[float]        # Y coordinates of ruled lines
    confidence: float                  # 0-1 detection confidence
    page_width_mm: float
    page_height_mm: float


@dataclass
class WritingCorrection:
    """Corrections to apply for perfect alignment."""
    dx: float = 0.0           # X shift
    dy: float = 0.0           # Y shift  
    rotation_deg: float = 0.0 # page rotation
    scale_factor: float = 1.0 # if page size differs from config


def simulate_page_scan(
    notebook_width_mm: float = 210,
    notebook_height_mm: float = 297,
    left_margin_mm: float = 25,
    top_margin_mm: float = 20,
    line_spacing_mm: float = 8,
    rotation_deg: float = 0.0,
    dpi: int = 150,
) -> np.ndarray:
    """Generate a synthetic notebook page scan for testing calibration.

    Creates a realistic-looking notebook page image with:
    - Off-white paper background
    - Red margin line 
    - Blue/grey ruled lines
    - Slight rotation
    - Realistic paper texture noise

    Returns numpy array (H, W, 3) uint8 RGB.
    """
    w_px = int(notebook_width_mm / 25.4 * dpi)
    h_px = int(notebook_height_mm / 25.4 * dpi)
    
    # Paper background — warm white with texture
    img = np.ones((h_px, w_px, 3), dtype=np.float32)
    img *= np.array([0.96, 0.95, 0.91])  # warm off-white
    noise = np.random.normal(0, 0.015, (h_px, w_px, 3)).astype(np.float32)
    img += noise
    img = np.clip(img, 0, 1)
    
    # Red margin line
    margin_px = int(left_margin_mm / 25.4 * dpi)
    top_px = int(top_margin_mm / 25.4 * dpi)
    bottom_px = h_px - int(20 / 25.4 * dpi)
    
    # Draw margin line (2px wide red)
    for dx in [-1, 0, 1]:
        x = margin_px + dx
        if 0 <= x < w_px:
            img[top_px:bottom_px, x] = [0.8, 0.1, 0.1]
    
    # Draw ruled lines (subtle blue-grey)
    available_h = bottom_px - top_px
    line_px = int(line_spacing_mm / 25.4 * dpi)
    for y_px in range(top_px, bottom_px, line_px):
        if y_px < h_px:
            img[y_px, margin_px:w_px - 50] = [0.7, 0.78, 0.88]
    
    # Apply rotation if needed
    if abs(rotation_deg) > 0.1:
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray((img * 255).astype(np.uint8))
        pil_img = pil_img.rotate(rotation_deg, expand=True, fillcolor=(245, 242, 232))
        img = np.array(pil_img).astype(np.float32) / 255.0
    
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def calibrate_page_from_image(
    image: np.ndarray,
    dpi: int = 150,
) -> PageCalibration:
    """Analyze a photo of the notebook page to detect layout.

    Args:
        image: RGB image of notebook page (numpy uint8 HxWx3)
        dpi: DPI of the image

    Returns:
        PageCalibration with detected geometry.
    """
    h, w = image.shape[:2]
    
    # Convert to grayscale
    gray = np.mean(image, axis=2)
    
    # Detect red margin line (red channel significantly higher than others)
    r = image[:, :, 0].astype(float)
    g = image[:, :, 1].astype(float)
    b = image[:, :, 2].astype(float)
    red_mask = (r > g * 1.4) & (r > b * 1.4)
    
    # Find leftmost strong red column
    col_sums = red_mask.sum(axis=0)
    threshold = h * 0.1  # at least 10% of rows red
    red_cols = np.where(col_sums > threshold)[0]
    margin_line_px = int(np.median(red_cols)) if len(red_cols) > 0 else int(w * 0.12)
    margin_line_x = margin_line_px / dpi * 25.4
    
    # Detect horizontal ruled lines using horizontal gradient
    grad_y = np.abs(np.diff(gray.astype(float), axis=0))
    grad_y = np.pad(grad_y, ((1, 0), (0, 0)))
    h_profile = grad_y[:, margin_line_px + 10:].mean(axis=1)
    
    # Find peaks in horizontal profile
    from scipy import signal
    peaks, props = signal.find_peaks(
        np.convolve(h_profile, np.ones(3) / 3, mode='same'),
        height=np.percentile(h_profile, 70),
        distance=10,
    )
    
    line_positions = [(p / dpi * 25.4) for p in peaks]
    
    # Estimate page corners (simple approximation)
    tl = (0.0, 0.0)
    tr = (w / dpi * 25.4, 0.0)
    bl = (0.0, h / dpi * 25.4)
    br = (w / dpi * 25.4, h / dpi * 25.4)
    
    confidence = 0.7 if len(line_positions) > 3 else 0.3
    
    return PageCalibration(
        top_left=tl, top_right=tr,
        bottom_left=bl, bottom_right=br,
        margin_line_x=margin_line_x,
        line_positions=line_positions,
        confidence=confidence,
        page_width_mm=w / dpi * 25.4,
        page_height_mm=h / dpi * 25.4,
    )


def compute_writing_correction(
    calibration: PageCalibration,
    expected_width: float = 210,
    expected_height: float = 297,
) -> WritingCorrection:
    """Calculate corrections to align writing with detected notebook layout.

    Args:
        calibration: Detected page geometry
        expected_width: Expected page width in mm
        expected_height: Expected page height in mm

    Returns:
        WritingCorrection with shifts/rotation to apply.
    """
    # Scale correction
    scale_w = calibration.page_width_mm / expected_width if expected_width > 0 else 1.0
    scale_h = calibration.page_height_mm / expected_height if expected_height > 0 else 1.0
    scale = (scale_w + scale_h) / 2
    
    # Rotation from page corners
    dx = calibration.top_right[0] - calibration.top_left[0]
    dy = calibration.top_right[1] - calibration.top_left[1]
    rotation = math.degrees(math.atan2(dy, dx)) if dx > 0 else 0.0
    
    # X shift to align margin
    dx_shift = calibration.margin_line_x - expected_width * 0.12  # ~25mm
    
    return WritingCorrection(
        dx=dx_shift,
        dy=0.0,
        rotation_deg=rotation,
        scale_factor=scale,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Writing quality optimizer
# ═══════════════════════════════════════════════════════════════════════════

def optimize_line_density(
    text: str,
    target_lines: int,
    font_size_range: tuple[float, float] = (3.0, 8.0),
) -> float:
    """Calculate optimal font size to fit text onto target number of lines.
    
    Args:
        text: The text to fit
        target_lines: Desired number of lines
        font_size_range: (min, max) font size in mm
        
    Returns:
        Optimal font_size_mm
    """
    avg_chars_per_line = 45  # rough estimate for A4
    total_chars = len(text)
    estimated_lines = total_chars / avg_chars_per_line
    
    if estimated_lines <= 0:
        return font_size_range[1]
    
    # Scale font size to fit target lines
    ratio = estimated_lines / target_lines
    size = font_size_range[1]  # default: larger
    
    if ratio > 1.5:  # too many lines, shrink
        size = font_size_range[1] / math.sqrt(ratio)
    elif ratio < 0.5:  # too few lines, grow
        size = font_size_range[1] * (1.0 / max(ratio, 0.2))
    
    size = max(font_size_range[0], min(font_size_range[1], size))
    return round(size, 1)


def auto_optimize_layout(
    text: str,
    page_width_mm: float,
    page_height_mm: float,
    margin_x_mm: float,
    top_margin_mm: float,
    bottom_margin_mm: float,
) -> dict:
    """Auto-calculate optimal text rendering parameters.

    Returns dict with:
        font_size_mm, line_spacing_mm, chars_per_line,
        lines_per_page, estimated_pages
    """
    text_width = page_width_mm - margin_x_mm - 15
    available_height = page_height_mm - top_margin_mm - bottom_margin_mm
    
    # Estimate optimal font size
    avg_width_per_char = 0.55  # ratio of char width to font height
    chars_per_line = int(text_width / (avg_width_per_char * 5.0))
    
    total_chars = len(text)
    total_lines = math.ceil(total_chars / max(1, chars_per_line))
    
    # Target: 30 lines per page
    target_lines_per_page = 35
    line_spacing = available_height / target_lines_per_page
    font_size = line_spacing * 0.62  # characters occupy ~62% of line height
    
    # Clamp
    font_size = max(3.5, min(7.0, font_size))
    line_spacing = max(5.0, min(10.0, line_spacing))
    
    chars_per_line = int(text_width / (font_size * avg_width_per_char))
    lines_per_page = int(available_height / line_spacing)
    estimated_pages = math.ceil(total_chars / (chars_per_line * lines_per_page))
    
    return {
        'font_size_mm': round(font_size, 1),
        'line_spacing_mm': round(line_spacing, 1),
        'chars_per_line': chars_per_line,
        'lines_per_page': lines_per_page,
        'estimated_pages': estimated_pages,
    }
