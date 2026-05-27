#!/usr/bin/env python
"""
Horus Plotter CLI — быстрая конвертация текста в G-code.

Usage:
  python plot.py текст.txt                          # конвертировать в G-код
  python plot.py текст.txt --font engineer_print    # другой шрифт  
  python plot.py текст.txt --auto                   # авто-оптимизация
  python plot.py текст.txt --output лекция.gcode     # в файл
  python plot.py текст.txt --preview                 # показать превью страниц
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.text_pipeline import full_text_pipeline
from core.notebook import NotebookConfig
from core.text_engine import TextConfig
from core.gcode import PlotConfig
from core.fonts import list_fonts, FONT_DISPLAY_NAMES
from core.vision import auto_optimize_layout


def main():
    parser = argparse.ArgumentParser(description="Horus Plotter — текст в G-код")
    parser.add_argument("file", help="Текстовый файл (.txt)")
    parser.add_argument("--font", choices=list_fonts(), default="semyon_cursive",
                        help="Шрифт (default: semyon_cursive)")
    parser.add_argument("--auto", action="store_true", help="Авто-оптимизация размера")
    parser.add_argument("--output", "-o", help="Выходной файл G-code")
    parser.add_argument("--preview", "-p", action="store_true", help="Показать статистику")
    parser.add_argument("--width", type=float, default=210, help="Ширина страницы мм")
    parser.add_argument("--height", type=float, default=297, help="Высота страницы мм")
    parser.add_argument("--margin", type=float, default=25, help="Левое поле мм")
    parser.add_argument("--size", type=float, default=5.0, help="Размер шрифта мм")
    parser.add_argument("--spacing", type=float, default=8.0, help="Межстрочный мм")

    args = parser.parse_args()

    # Load text
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Ошибка: файл {args.file} не найден")
        sys.exit(1)

    nc = NotebookConfig(
        page_width_mm=args.width, page_height_mm=args.height,
        left_margin_mm=args.margin,
    )

    # Auto-optimize
    if args.auto:
        result = auto_optimize_layout(text, nc.page_width_mm, nc.page_height_mm,
                                      nc.left_margin_mm, nc.top_margin_mm, nc.bottom_margin_mm)
        args.size = result['font_size_mm']
        args.spacing = result['line_spacing_mm']
        print(f"Авто-оптимизация: шрифт {args.size}мм, интервал {args.spacing}мм, "
              f"~{result['estimated_pages']} стр.")

    tc = TextConfig(
        font_name=args.font,
        font_size_mm=args.size,
        line_spacing_mm=args.spacing,
    )
    pc = PlotConfig()

    print(f"Шрифт: {FONT_DISPLAY_NAMES.get(args.font, args.font)}")
    print(f"Генерация...")

    results = full_text_pipeline(text, nc, tc, pc)
    print(f"Готово: {len(results)} страниц")

    if args.preview:
        for pn, drawing, gcode in results:
            lines = len([l for l in gcode.split('\n') if not l.startswith(';') and l.strip()])
            draw_mm = sum(p.length for p in drawing.paths)
            travel_mm = drawing.total_travel_length()
            print(f"  Стр. {pn + 1}: {lines} команд, "
                  f"рисование {draw_mm:.0f}мм, холостой {travel_mm:.0f}мм, "
                  f"путей {len(drawing.paths)}")

    # Save
    if args.output:
        out_path = args.output
    else:
        out_path = Path(args.file).stem + ".gcode"

    with open(out_path, "w", encoding="utf-8") as f:
        for pn, drawing, gcode in results:
            f.write(f"; Page {pn + 1}\n")
            f.write(gcode)
            f.write("\n\n")

    print(f"Сохранено: {out_path}")
    print("Открой в LaserGRBL / UGS → отправь на Хорус 🚀")


if __name__ == "__main__":
    main()
