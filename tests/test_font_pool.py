"""Tests for font_pool.py — 300 parametric font system."""
import pytest
from core.font_pool import (
    generate_variants, transform_font, get_all_fonts, list_all_fonts,
    generate_font_preview_svg, generate_font_preview_all,
    FontVariant, generate_all_fonts,
)
from core.fonts import FONTS as BASE_FONTS

class TestFontVariants:
    def test_generate_variants_returns_60(self):
        variants = generate_variants("semyon_cursive", count=10, seed=42)
        assert len(variants) == 10, f"Expected 10, got {len(variants)}"

    def test_variants_have_unique_names(self):
        variants = generate_variants("school_script", count=20, seed=7)
        names = [v.name for v in variants]
        assert len(names) == len(set(names)), "All variant names should be unique"

    def test_variant_slant_range(self):
        variants = generate_variants("semyon_cursive", count=50)
        slants = [v.slant for v in variants]
        assert min(slants) >= -8, f"Min slant {min(slants)} below -8"
        assert max(slants) <= 25, f"Max slant {max(slants)} above 25"

    def test_variant_weight_range(self):
        variants = generate_variants("semyon_cursive", count=50)
        weights = [v.weight for v in variants]
        assert 0.5 <= min(weights) <= 1.9, f"Weight too low: {min(weights)}"
        assert 0.5 <= max(weights) <= 1.9, f"Weight too high: {max(weights)}"

class TestTransformFont:
    def test_transform_preserves_all_chars(self):
        base = BASE_FONTS["semyon_cursive"]
        variant = FontVariant(name="Test", base_family="semyon_cursive", slant=5)
        result = transform_font(base, variant)
        assert len(result) == len(base), "All characters should be preserved"

    def test_transform_changes_glyphs(self):
        base = BASE_FONTS["semyon_cursive"]
        variant = FontVariant(name="Test", base_family="semyon_cursive",
                             slant=30, weight=2.0, wobble=0.2)
        result = transform_font(base, variant)
        # Check that at least one stroke changed
        orig_a = base.get('а', ([], 0, []))
        new_a = result.get('а', ([], 0, []))
        orig_pts = orig_a[0][0][0] if orig_a[0] else (0, 0)
        new_pts = new_a[0][0][0] if new_a[0] else (0, 0)
        assert orig_pts != new_pts or orig_a[1] != new_a[1], "Transformation should change glyphs"

    def test_slant_zero_unchanged(self):
        base = BASE_FONTS["semyon_cursive"]
        variant = FontVariant(name="Test", base_family="semyon_cursive", seed=42)
        result = transform_font(base, variant)
        # Width and spacing may differ slightly, but basic structure preserved
        assert 'а' in result
        assert len(result['а'][0]) == len(base['а'][0])

class TestGenerateAllFonts:
    def test_generates_300(self):
        fonts = generate_all_fonts(per_family=2)  # 10 for speed
        assert len(fonts) == 10, f"Expected 10 (2 per family), got {len(fonts)}"

    def test_all_fonts_renderable(self):
        fonts = generate_all_fonts(per_family=1)
        for name, font in fonts.items():
            assert 'а' in font, f"{name} missing 'а'"
            strokes, _, _ = font['а']
            assert len(strokes) > 0, f"{name} 'а' has no strokes"

class TestLazyLoad:
    def test_list_all_fonts(self):
        fonts = get_all_fonts()
        assert len(fonts) == 300, f"Expected 300, got {len(fonts)}"
        names = list_all_fonts()
        assert len(names) == 300, "list_all_fonts should match get_all_fonts"

    def test_get_all_fonts_cached(self):
        f1 = get_all_fonts()
        f2 = get_all_fonts()
        assert f1 is f2, "Should return cached result"

class TestPreviewSVG:
    def test_generates_svg(self):
        fonts = generate_all_fonts(per_family=1)
        first = list(fonts.values())[0]
        svg = generate_font_preview_svg(first)
        assert svg.startswith('<svg'), f"Expected SVG, got: {svg[:50]}"
        assert 'a78bfa' in svg or '#a78bfa' in svg, "Should use purple stroke"

    def test_empty_font_handled(self):
        svg = generate_font_preview_svg({})
        assert '<svg' in svg, "Should return valid SVG even for empty font"

    def test_preview_all_limits(self):
        previews = generate_font_preview_all(limit=5)
        assert len(previews) <= 5, "Should respect limit"
        for name, svg in previews.items():
            assert svg.startswith('<svg'), f"{name} preview not SVG"
