"""Bug hunt: test all 5 fonts with edge cases."""
from core.text_pipeline import full_text_pipeline
from core.notebook import NotebookConfig
from core.text_engine import TextConfig
from core.gcode import PlotConfig
from core.fonts import list_fonts

test_cases = [
    ("normal", "Привет! Как дела? Всё хорошо."),
    ("empty", ""),
    ("long_word", "А" * 500),
    ("many_newlines", "Тест\n\n\nМного\n\n\nпустых\n\n\nстрок"),
    ("many_spaces", "   много    пробелов   между    словами   "),
    ("digits_symbols", "12345 !@#$% тест"),
    ("special_chars", "\u0401\u0451\u0419\u0439\u042a\u044a\u042c\u044c \u2014 \u00ab\u0435\u043b\u043e\u0447\u043a\u0438\u00bb"),
    ("latin_fallback", "A" * 1000),
]

for name in list_fonts():
    tc = TextConfig(font_name=name)
    nc = NotebookConfig()
    pc = PlotConfig()
    errors = []
    for desc, text in test_cases:
        try:
            results = full_text_pipeline(text, nc, tc, pc)
            if text and not results:
                errors.append(f"  {desc}: empty results")
        except Exception as e:
            errors.append(f"  {desc}: {type(e).__name__}: {e}")
    if errors:
        print(f"{name}: BUGS FOUND")
        for e in errors:
            print(e)
    else:
        print(f"{name}: OK ({len(test_cases)} cases)")

# Check vision module
print()
from core.vision import calibrate_page_from_image, simulate_page_scan, auto_optimize_layout
try:
    img = simulate_page_scan()
    cal = calibrate_page_from_image(img)
    print(f"Vision: margin={cal.margin_line_x:.1f}mm, lines={len(cal.line_positions)}, ok")
except Exception as e:
    print(f"Vision: ERROR - {e}")

# Check all empty/missing key paths
print()
print("Checking font coverage...")
from core.fonts import FONTS
needed = "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ0123456789.,-:;!?()\"'"
for name, font in FONTS.items():
    missing = [ch for ch in needed if ch not in font]
    if missing:
        print(f"{name}: MISSING {len(missing)} chars: {''.join(missing[:20])}...")
    else:
        print(f"{name}: all {len(needed)} chars covered")

print()
print("Done.")
