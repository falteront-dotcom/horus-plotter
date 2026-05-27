"""
Parametric Font Generator — produces 300+ unique handwriting fonts
from 5 base families via parametric transformations.

Transformations applied to base strokes:
  - slant: italic tilt
  - weight: stroke thickness variation
  - x_height: ascender/descender ratio
  - width: character narrowness
  - roundness: corner softening
  - wobble: organic randomness
  - baseline_shift: vertical offset jitter
  - letter_spacing: tracking adjustment
  - flourish: decorative extensions
  - serif: optional serif generation
"""

from __future__ import annotations
import math
import random
import copy
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .fonts import FONTS as BASE_FONTS, FONT_DISPLAY_NAMES as BASE_NAMES

Stroke = List[Tuple[float, float]]
Dot = Tuple[float, float]
CharDef = Tuple[List[Stroke], float, List[Dot]]


@dataclass
class FontVariant:
    """Parameters to transform a base font into a unique variant."""
    name: str
    base_family: str  # which of the 5 base fonts
    slant: float = 0.0           # italic angle in degrees
    weight: float = 1.0          # stroke thickness multiplier (0.5-2.0)
    x_height: float = 1.0        # ascender height ratio
    descender: float = 1.0       # descender depth ratio
    width: float = 1.0           # character width ratio
    roundness: float = 0.0       # corner smoothing 0-1
    wobble: float = 0.0          # random perturbation
    baseline_jitter: float = 0.0 # baseline randomness
    letter_spacing: float = 1.0  # tracking factor
    flourish: float = 0.0        # decorative complexity
    seed: int = 0


def generate_variants(base_family: str, count: int = 60, seed: int = 42) -> List[FontVariant]:
    """Generate parametric variants from a base font family.
    
    Creates count unique-looking fonts with different personality.
    """
    rng = random.Random(seed)
    variants = []
    
    for i in range(count):
        # Each variant gets a distinct "personality"
        personality = i / max(1, count - 1)  # 0-1 personality spectrum
        
        # Map personality to parameter clusters for recognizable styles
        if personality < 0.2:
            # Cluster: Upright formal
            slant = rng.uniform(-3, 3)
            weight = rng.uniform(0.9, 1.2)
            width = rng.uniform(0.9, 1.1)
            wobble = rng.uniform(0.0, 0.03)
            flourish = 0.0
        elif personality < 0.4:
            # Cluster: Slanted cursive
            slant = rng.uniform(8, 20)
            weight = rng.uniform(0.8, 1.1)
            width = rng.uniform(0.85, 0.95)
            wobble = rng.uniform(0.05, 0.12)
            flourish = rng.uniform(0.0, 0.15)
        elif personality < 0.6:
            # Cluster: Bold heavy
            slant = rng.uniform(-5, 5)
            weight = rng.uniform(1.3, 1.8)
            width = rng.uniform(1.0, 1.15)
            wobble = rng.uniform(0.01, 0.05)
            flourish = rng.uniform(0.0, 0.05)
        elif personality < 0.8:
            # Cluster: Light elegant
            slant = rng.uniform(2, 12)
            weight = rng.uniform(0.5, 0.8)
            width = rng.uniform(0.8, 0.95)
            wobble = rng.uniform(0.03, 0.08)
            flourish = rng.uniform(0.05, 0.2)
        else:
            # Cluster: Expressive artistic
            slant = rng.uniform(-8, 25)
            weight = rng.uniform(0.6, 1.5)
            width = rng.uniform(0.7, 1.2)
            wobble = rng.uniform(0.08, 0.2)
            flourish = rng.uniform(0.1, 0.3)
        
        x_height = rng.uniform(0.85, 1.15)
        descender = rng.uniform(0.8, 1.2)
        roundness = rng.uniform(0.0, 0.4)
        baseline_jitter = rng.uniform(0.0, 0.04)
        letter_spacing = rng.uniform(0.85, 1.15)
        
        # Name based on characteristics
        adj = _pick_adjective(personality, slant, weight, wobble, rng)
        name = f"{adj} {BASE_NAMES.get(base_family, base_family)} #{i}"
        
        variants.append(FontVariant(
            name=name, base_family=base_family,
            slant=slant, weight=weight, x_height=x_height,
            descender=descender, width=width, roundness=roundness,
            wobble=wobble, baseline_jitter=baseline_jitter,
            letter_spacing=letter_spacing, flourish=flourish,
            seed=rng.randint(0, 99999),
        ))
    
    return variants


def _pick_adjective(personality: float, slant: float, weight: float,
                    wobble: float, rng: random.Random) -> str:
    """Pick a descriptive adjective for the font variant name."""
    if weight > 1.5:
        pool = ["Жирный", "Толстый", "Массивный", "Тяжёлый", "Густой", "Плотный"]
    elif weight < 0.7:
        pool = ["Тонкий", "Лёгкий", "Воздушный", "Изящный", "Утончённый"]
    elif abs(slant) > 12:
        pool = ["Наклонный", "Курсивный", "Стремительный", "��инамичный"]
    elif wobble > 0.1:
        pool = ["Живой", "Экспрессивный", "Художественный", "Творческий"]
    elif personality < 0.3:
        pool = ["Строгий", "Формальный", "Чёткий", "Аккуратный"]
    else:
        pool = ["Обычный", "Стандартный", "Классический", "Ровный", "Мягкий",
                "Плавный", "Чистый", "Ясный", "Спокойный", "Уверенный"]
    return rng.choice(pool)


def transform_font(base_font: Dict[str, CharDef],
                   variant: FontVariant) -> Dict[str, CharDef]:
    """Apply parametric transformations to produce a unique font variant."""
    rng = random.Random(variant.seed)
    result = {}
    
    slant_rad = math.radians(variant.slant)
    
    for ch, (strokes, width, dots) in base_font.items():
        new_strokes = []
        
        for stroke in strokes:
            new_pts = []
            for x, y in stroke:
                # Apply slant (X shifts with Y)
                if variant.slant != 0:
                    x = x + y * math.tan(slant_rad) * 0.8
                
                # Apply x-height (scale Y)
                if y > 0:
                    y *= variant.x_height
                else:
                    y *= variant.descender
                
                # Apply width
                x *= variant.width
                
                # Apply wobble
                if variant.wobble > 0:
                    x += rng.uniform(-variant.wobble, variant.wobble) * 0.5
                    y += rng.uniform(-variant.wobble, variant.wobble) * 0.3
                
                new_pts.append((x, y))
            
            # Apply roundness (insert intermediate points for curved look)
            if variant.roundness > 0 and len(new_pts) >= 2:
                rounded = _round_corners(new_pts, variant.roundness)
                new_strokes.append(rounded)
            else:
                new_strokes.append(new_pts)
        
        # Apply flourish (add decorative extensions)
        if variant.flourish > 0 and new_strokes:
            first_stroke = new_strokes[0]
            if first_stroke:
                fx, fy = first_stroke[0]
                # Add a small leading curl
                curl_pts = [
                    (fx - variant.flourish * 0.3, fy + variant.flourish * 0.4),
                    (fx - variant.flourish * 0.15, fy + variant.flourish * 0.2),
                    (fx, fy),
                ]
                new_strokes = [curl_pts] + new_strokes
        
        # Adjust width for letter spacing
        new_width = width * variant.letter_spacing
        
        # Transform dots
        new_dots = [(x + y * math.tan(slant_rad) * 0.8, y * variant.x_height)
                    for x, y in dots]
        
        result[ch] = (new_strokes, new_width, new_dots)
    
    return result


def _round_corners(pts: List[Tuple[float, float]],
                   strength: float) -> List[Tuple[float, float]]:
    """Insert extra points at corners for a rounded appearance."""
    if len(pts) < 3:
        return pts
    
    result = [pts[0]]
    for i in range(1, len(pts) - 1):
        px, py = pts[i]
        px_prev, py_prev = pts[i - 1]
        px_next, py_next = pts[i + 1]
        
        # Insert rounded corner points
        if strength > 0.01:
            mid_prev = (px_prev * (1 - strength) + px * strength,
                       py_prev * (1 - strength) + py * strength)
            mid_next = (px_next * (1 - strength) + px * strength,
                       py_next * (1 - strength) + py * strength)
            result.append(mid_prev)
            result.append(mid_next)
        else:
            result.append((px, py))
    
    result.append(pts[-1])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# GENERATE ALL 300 FONTS
# ═══════════════════════════════════════════════════════════════════════════

def generate_all_fonts(per_family: int = 60) -> Dict[str, dict]:
    """Generate 300 font variants (60 per base family × 5 families).
    
    Returns {font_name: {char: CharDef}} mapping.
    """
    all_fonts = {}
    
    for base_name in BASE_FONTS.keys():
        variants = generate_variants(base_name, count=per_family, 
                                     seed=hash(base_name) % 99999)
        
        base_font = BASE_FONTS[base_name]
        
        for variant in variants:
            transformed = transform_font(base_font, variant)
            font_key = variant.name
            # Ensure uniqueness — append seed+counter if collision
            counter = 1
            base_key = font_key
            while font_key in all_fonts:
                counter += 1
                font_key = f"{base_key} #{variant.seed}_{counter}"
            all_fonts[font_key] = transformed
    
    return all_fonts


# Lazy cache
_FONT_CACHE: Dict[str, dict] = {}
_FONT_LIST: List[str] = []


def get_all_fonts() -> Dict[str, dict]:
    """Get all 300+ fonts (lazy generation)."""
    global _FONT_CACHE
    if not _FONT_CACHE:
        _FONT_CACHE = generate_all_fonts(per_family=60)
    return _FONT_CACHE


def get_font_by_name(name: str) -> dict:
    """Get a specific font by name."""
    fonts = get_all_fonts()
    return fonts.get(name, BASE_FONTS.get("semyon_cursive", {}))


def list_all_fonts() -> List[str]:
    """List all available font names (300+)."""
    global _FONT_LIST
    if not _FONT_LIST:
        _FONT_LIST = sorted(get_all_fonts().keys())
    return _FONT_LIST


# ═══════════════════════════════════════════════════════════════════════════
# FONT PREVIEW RENDERING
# ═══════════════════════════════════════════════════════════════════════════

def generate_font_preview_svg(font: Dict[str, CharDef],
                              sample_text: str = "Аа Бб Вв Гг Дд Ее Жж",
                              font_size: float = 20,
                              width: int = 400,
                              height: int = 80) -> str:
    """Generate an SVG preview of a font showing sample text.
    
    Returns SVG string with the font's rendering.
    """
    from .text_engine import HandwritingRenderer, TextConfig
    
    # Compute actual drawing bounds
    all_x, all_y = [], []
    x_pos = 0.0
    
    for ch in sample_text:
        if ch in font:
            strokes, char_w, dots = font[ch]
            for stroke in strokes:
                for sx, sy in stroke:
                    all_x.append(x_pos + sx * font_size)
                    all_y.append(sy * font_size)
            x_pos += char_w * font_size + 1
    
    if not all_x:
        return f'<svg width="{width}" height="{height}"><text y="20">No preview</text></svg>'
    
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    draw_w = max_x - min_x + 10
    draw_h = max_y - min_y + 10
    
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x - 5} {min_y - 5} {draw_w} {draw_h}" '
        f'width="{width}" height="{height}">',
        f'<rect width="100%" height="100%" fill="#1a1a2e"/>',
    ]
    
    x_pos = 0.0
    for ch in sample_text:
        if ch in font:
            strokes, char_w, dots = font[ch]
            for stroke in strokes:
                if len(stroke) >= 2:
                    pts = " ".join(f"{x_pos + sx * font_size:.1f},{sy * font_size:.1f}"
                                  for sx, sy in stroke)
                    lines.append(
                        f'<polyline points="{pts}" fill="none" '
                        f'stroke="#a78bfa" stroke-width="1.2" '
                        f'stroke-linecap="round" stroke-linejoin="round"/>'
                    )
            x_pos += char_w * font_size + 1.5
    
    lines.append('</svg>')
    return "\n".join(lines)


def generate_font_preview_all(limit: int = 300) -> Dict[str, str]:
    """Generate SVG previews for all fonts.
    
    Returns {font_name: svg_string} mapping.
    """
    fonts = get_all_fonts()
    previews = {}
    for i, (name, font) in enumerate(fonts.items()):
        if i >= limit:
            break
        try:
            svg = generate_font_preview_svg(font, sample_text="АБВГДЕ абвгде")
            previews[name] = svg
        except Exception:
            previews[name] = f'<svg><text>Error</text></svg>'
    return previews
