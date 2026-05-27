"""
Horus Plotter — загрузи картинку ИЛИ текст → отправь на плоттер.
Режимы: Изображение (18 стилей) + Текст (рукописный конспект в тетради).
Flet 0.84 async UI + core pipeline + pyserial GRBL sender.
"""

import asyncio
import os
import threading
import time

import flet as ft
import serial
import serial.tools.list_ports

from core.gcode import PlotConfig, drawing_to_gcode, gcode_stats
from core.pipeline import image_to_gcode
from core.notebook import NotebookConfig
from core.text_engine import TextConfig
from core.text_pipeline import full_text_pipeline
from core.fonts import list_fonts, FONT_DISPLAY_NAMES
from core.vision import auto_optimize_layout


# ═══════════════════════════════════════════════════════════════════════════
# GRBL Serial Sender
# ═══════════════════════════════════════════════════════════════════════════

class PlotterSender:
    def __init__(self, port: str = "COM3", baud: int = 115200):
        self.port = port
        self.baud = baud
        self._ser = None
        self._buf = ""
        self._cancelled = False
        self.start_time = None

    def connect(self):
        self._ser = serial.Serial(self.port, self.baud, timeout=1)
        time.sleep(1.5)
        self._buf = ""
        self._ser.reset_input_buffer()
        self._ser.write(b"$X\n")
        self._read_ok()
        self.start_time = time.time()

    def _read_ok(self, timeout=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._ser.in_waiting:
                self._buf += self._ser.read(self._ser.in_waiting).decode(errors="replace")
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                line = line.strip()
                if line in ("ok", ""):
                    return True
                if line.startswith("error"):
                    return False
            time.sleep(0.01)
        return False

    def send(self, gcode: str, on_progress=None):
        commands = [l.strip() for l in gcode.split("\n") if l.strip() and not l.strip().startswith(";")]
        total = len(commands)
        self._cancelled = False
        for i, cmd in enumerate(commands):
            if self._cancelled:
                break
            self._ser.write((cmd + "\n").encode())
            self._read_ok()
            if on_progress:
                on_progress(i + 1, total)

    def send_raw(self, cmd: str):
        if self._ser and self._ser.is_open:
            self._ser.write((cmd.strip() + "\n").encode())
            self._read_ok()

    def cancel(self):
        self._cancelled = True

    def disconnect(self):
        if self._ser and self._ser.is_open:
            self._ser.close()

    def eta_seconds(self, done: int, total: int) -> float:
        if not self.start_time or done == 0:
            return 0
        elapsed = time.time() - self.start_time
        rate = done / elapsed
        remaining = (total - done) / rate if rate > 0 else 0
        return remaining


def list_serial_ports() -> list[str]:
    return [p.device for p in serial.tools.list_ports.comports()]


# ═══════════════════════════════════════════════════════════════════════════
# Стили изображений
# ═══════════════════════════════════════════════════════════════════════════

STYLE_NAMES = {
    "hatching": "Штриховка",
    "cross-hatching": "Крестовая",
    "halftone": "Полутон",
    "stipple": "Точечная",
    "spiral": "Спираль",
    "flow-field": "Потоковое поле",
    "meandering": "Извилистая",
    "edge-detect": "Контуры",
    "dots": "Точки (сетка)",
    "concentric": "Концентрическая",
    "woodcut": "Гравюра",
    "zigzag": "Зигзаг",
    "tiles": "Плитка",
    "scribble": "Каракули",
    "contour": "Изолинии",
    "waves": "Волны",
    "hexagon": "Соты",
}


# ═══════════════════════════════════════════════════════════════════════════
# Flet UI
# ═══════════════════════════════════════════════════════════════════════════

async def main(page: ft.Page):
    page.title = "Horus Plotter"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 1100
    page.window.height = 950
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    _loop = asyncio.get_running_loop()

    state = {
        "image_path": None,
        "gcode": None,
        "text_gcode": None,
        "text_pages": [],
        "current_text_page": 0,
        "sender": None,
        "plotting": False,
        "connected": False,
    }

    # ─── File picker ─────────────────────────────────────────────────────
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    # ─── Общие элементы ──────────────────────────────────────────────────
    ports = list_serial_ports()
    port_dd = ft.Dropdown(
        label="Порт",
        options=[ft.dropdown.Option(p) for p in ports] or [ft.dropdown.Option("COM3")],
        value=ports[0] if ports else "COM3", width=150,
    )

    status_text = ft.Text("Загрузите изображение или введите текст", size=14, color=ft.Colors.GREY_400)
    stats_text = ft.Text("", size=12, color=ft.Colors.GREY_500)
    progress_bar = ft.ProgressBar(visible=False, width=500)

    # Глобальные настройки плоттера (общие для изображений и текста)
    pen_down_tf = ft.TextField(label="Перо вниз Z", value="5", width=100, input_filter=ft.NumbersOnlyInputFilter())
    pen_up_tf = ft.TextField(label="Перо вверх Z", value="0", width=100, input_filter=ft.NumbersOnlyInputFilter())
    speed_sl = ft.Slider(min=500, max=5000, divisions=45, label="{value} мм/мин", value=3000)
    travel_speed_sl = ft.Slider(min=1000, max=10000, divisions=45, label="{value} мм/мин", value=8000)
    pen_down_delay_tf = ft.TextField(label="Задержка вниз (с)", value="0", width=120, input_filter=ft.NumbersOnlyInputFilter())
    pen_up_delay_tf = ft.TextField(label="Задержка вверх (с)", value="0", width=120, input_filter=ft.NumbersOnlyInputFilter())

    # ─── Кнопки действий ─────────────────────────────────────────────────
    btn_save_gcode = ft.OutlinedButton("Сохранить G-code", icon=ft.Icons.SAVE, disabled=True, visible=False)
    btn_cancel = ft.OutlinedButton("Отмена", icon=ft.Icons.STOP, visible=False)

    btn_home = ft.OutlinedButton("Домой", icon=ft.Icons.HOME, disabled=True)
    btn_pen_up = ft.OutlinedButton("Перо вверх", icon=ft.Icons.ARROW_UPWARD, disabled=True)
    btn_pen_down = ft.OutlinedButton("Перо вниз", icon=ft.Icons.ARROW_DOWNWARD, disabled=True)
    btn_connect = ft.OutlinedButton("Подключить", icon=ft.Icons.CABLE)

    # ══════════════════════════════════════════════════════════════════════
    # РЕЖИМ 1: ИЗОБРАЖЕНИЕ
    # ══════════════════════════════════════════════════════════════════════

    img_display = ft.Image(src="", width=350, height=350, fit=ft.BoxFit.CONTAIN, visible=False, border_radius=8)
    img_placeholder = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE, size=48, color=ft.Colors.PURPLE_300),
            ft.Text("Нажмите «Загрузить» ниже", size=14, color=ft.Colors.GREY_400),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.MainAxisAlignment.CENTER),
        width=350, height=350,
        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.PURPLE_200),
        border=ft.Border.all(2, ft.Colors.PURPLE_400),
        border_radius=12, padding=20,
    )

    preview_img = ft.Image(src="", width=350, height=350, fit=ft.BoxFit.FILL, visible=False, border_radius=8)
    preview_placeholder = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.DRAW, size=36, color=ft.Colors.GREY_600),
            ft.Text("Превью появится здесь", color=ft.Colors.GREY_500, size=13),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.MainAxisAlignment.CENTER),
        width=350, height=350,
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
        border_radius=8, padding=20,
    )

    invert_indicator = ft.Text("", size=12, color=ft.Colors.ORANGE_400, visible=False)

    # Настройки изображения
    style_dd = ft.Dropdown(
        label="Стиль",
        options=[ft.dropdown.Option(k, v) for k, v in STYLE_NAMES.items()],
        value="hatching", width=200,
    )
    width_sl = ft.Slider(min=50, max=300, divisions=25, label="{value} мм", value=200)
    spacing_sl = ft.Slider(min=1, max=10, divisions=18, label="{value} мм", value=3)
    threshold_sl = ft.Slider(min=0.05, max=0.5, divisions=9, label="{value}", value=0.15)
    invert_chk = ft.Checkbox(label="Инверсия", value=False)
    auto_invert_chk = ft.Checkbox(label="Авто-инверсия (тёмный фон)", value=True)
    brightness_sl = ft.Slider(min=0.2, max=3.0, divisions=14, label="×{value}", value=1.0)
    contrast_sl = ft.Slider(min=0.2, max=3.0, divisions=14, label="×{value}", value=1.0)
    blur_sl = ft.Slider(min=0, max=5, divisions=10, label="{value} px", value=0)
    work_x_tf = ft.TextField(label="Зона X (мм)", value="300", width=100, input_filter=ft.NumbersOnlyInputFilter())
    work_y_tf = ft.TextField(label="Зона Y (мм)", value="300", width=100, input_filter=ft.NumbersOnlyInputFilter())

    btn_pick = ft.Button("Загрузить изображение", icon=ft.Icons.IMAGE)
    btn_send_img = ft.Button("Отправить на плоттер", icon=ft.Icons.SEND, disabled=True,
                              style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE_700))

    # ─── Image config builder ────────────────────────────────────────────
    def _build_img_config() -> PlotConfig:
        return PlotConfig(
            style=style_dd.value,
            width_mm=width_sl.value,
            spacing_mm=spacing_sl.value,
            speed=int(speed_sl.value),
            travel_speed=int(travel_speed_sl.value),
            pen_down_z=float(pen_down_tf.value),
            pen_up_z=float(pen_up_tf.value),
            pen_down_delay=float(pen_down_delay_tf.value or 0),
            pen_up_delay=float(pen_up_delay_tf.value or 0),
            threshold=threshold_sl.value,
            invert=invert_chk.value,
            auto_invert=auto_invert_chk.value,
            brightness=brightness_sl.value,
            contrast=contrast_sl.value,
            blur=blur_sl.value,
            work_area_x=float(work_x_tf.value or 300),
            work_area_y=float(work_y_tf.value or 300),
        )

    async def _update_image_preview():
        if not state["image_path"]:
            return
        cfg = _build_img_config()
        try:
            gcode, preview_b64 = await asyncio.get_running_loop().run_in_executor(
                None, image_to_gcode, state["image_path"], cfg
            )
            state["gcode"] = gcode
            if preview_b64:
                preview_img.src = f"data:image/png;base64,{preview_b64}"
                preview_img.visible = True
                preview_placeholder.visible = False
            n = len([l for l in gcode.split("\n") if l.strip() and not l.strip().startswith(";")])
            status_text.value = f"G-code готов: {n} команд"
            status_text.color = ft.Colors.GREEN_400
            btn_send_img.disabled = False
            btn_save_gcode.disabled = False
            btn_save_gcode.visible = True
        except Exception as ex:
            status_text.value = f"Ошибка: {ex}"
            status_text.color = ft.Colors.RED_400
        page.update()

    async def on_pick(e):
        result = await file_picker.pick_files(
            dialog_title="Загрузить изображение",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["png", "jpg", "jpeg", "bmp", "webp", "gif", "pdf", "docx", "tiff", "tif"],
        )
        if not result:
            return
        path = result[0].path
        state["image_path"] = path
        img_display.src = path
        img_display.visible = True
        img_placeholder.visible = False
        preview_img.visible = False
        preview_placeholder.visible = True
        status_text.value = f"Загружено: {os.path.basename(path)}"
        status_text.color = ft.Colors.GREEN_400
        page.update()
        await _update_image_preview()

    btn_pick.on_click = on_pick

    # ══════════════════════════════════════════════════════════════════════
    # РЕЖИМ 2: ТЕКСТ (КОНСПЕКТЫ)
    # ══════════════════════════════════════════════════════════════════════

    text_input = ft.TextField(
        label="Введите текст лекции / конспекта",
        multiline=True,
        min_lines=8,
        max_lines=16,
        width=700,
        value="",
    )

    # Notebook layout settings
    page_w_tf = ft.TextField(label="Ширина страницы (мм)", value="210", width=110, input_filter=ft.NumbersOnlyInputFilter())
    page_h_tf = ft.TextField(label="Высота страницы (мм)", value="297", width=110, input_filter=ft.NumbersOnlyInputFilter())
    left_margin_tf = ft.TextField(label="Левое поле (мм)", value="25", width=100, input_filter=ft.NumbersOnlyInputFilter())
    right_margin_tf = ft.TextField(label="Правое поле (мм)", value="10", width=100, input_filter=ft.NumbersOnlyInputFilter())
    top_margin_tf = ft.TextField(label="Верхнее поле (мм)", value="20", width=100, input_filter=ft.NumbersOnlyInputFilter())
    bottom_margin_tf = ft.TextField(label="Нижнее поле (мм)", value="20", width=100, input_filter=ft.NumbersOnlyInputFilter())

    # Text rendering settings
    fonts_list = list_fonts()
    font_dd = ft.Dropdown(
        label="Шрифт",
        options=[ft.dropdown.Option(k, v) for k, v in FONT_DISPLAY_NAMES.items()],
        value=fonts_list[0] if fonts_list else "semyon_cursive",
        width=220,
    )
    font_size_tf = ft.TextField(label="Размер шрифта (мм)", value="5.0", width=110, input_filter=ft.NumbersOnlyInputFilter())
    line_spacing_tf = ft.TextField(label="Межстр. интервал (мм)", value="8.0", width=120, input_filter=ft.NumbersOnlyInputFilter())
    char_spacing_tf = ft.TextField(label="Пробел букв (мм)", value="0.8", width=110, input_filter=ft.NumbersOnlyInputFilter())
    word_spacing_tf = ft.TextField(label="Пробел слов (мм)", value="2.0", width=110, input_filter=ft.NumbersOnlyInputFilter())
    para_indent_tf = ft.TextField(label="Абзацный отступ (мм)", value="12.5", width=120, input_filter=ft.NumbersOnlyInputFilter())
    variability_sl = ft.Slider(min=0.0, max=0.5, divisions=10, label="{value}", value=0.15)

    margin_line_chk = ft.Checkbox(label="Красные поля", value=True)
    ruled_lines_chk = ft.Checkbox(label="Линии строк", value=True)

    # Colors
    margin_color_tf = ft.TextField(label="Цвет полей", value="#CC0000", width=100)
    ruled_color_tf = ft.TextField(label="Цвет строк", value="#A0C4E8", width=100)

    text_page_info = ft.Text("Страница: —", size=13, color=ft.Colors.GREY_400)
    text_preview_img = ft.Image(src="", width=350, height=490, fit=ft.BoxFit.FILL, visible=False, border_radius=8)
    text_preview_placeholder = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.EDIT_NOTE, size=48, color=ft.Colors.AMBER_300),
            ft.Text("Превью страницы тетради", size=14, color=ft.Colors.GREY_500),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.MainAxisAlignment.CENTER),
        width=350, height=490,
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.WHITE),
        border_radius=8, padding=20,
    )

    btn_generate_text = ft.Button("Сгенерировать конспект", icon=ft.Icons.AUTO_STORIES,
                                   style=ft.ButtonStyle(bgcolor=ft.Colors.AMBER_800))
    btn_auto_opt = ft.OutlinedButton("Авто-оптимизация", icon=ft.Icons.TUNE)
    btn_send_text = ft.Button("Писать в тетрадь", icon=ft.Icons.EDIT, disabled=True,
                               style=ft.ButtonStyle(bgcolor=ft.Colors.PURPLE_700))
    btn_prev_page = ft.IconButton(ft.Icons.ARROW_LEFT, disabled=True)
    btn_next_page = ft.IconButton(ft.Icons.ARROW_RIGHT, disabled=True)

    text_progress = ft.Text("", size=13, color=ft.Colors.GREY_400)

    def _build_notebook_config() -> NotebookConfig:
        return NotebookConfig(
            page_width_mm=float(page_w_tf.value or 210),
            page_height_mm=float(page_h_tf.value or 297),
            left_margin_mm=float(left_margin_tf.value or 25),
            right_margin_mm=float(right_margin_tf.value or 10),
            top_margin_mm=float(top_margin_tf.value or 20),
            bottom_margin_mm=float(bottom_margin_tf.value or 20),
            line_spacing_mm=float(line_spacing_tf.value or 8),
            paragraph_indent_mm=float(para_indent_tf.value or 12.5),
            draw_margin_line=margin_line_chk.value,
            draw_ruled_lines=ruled_lines_chk.value,
        )

    def _build_text_config() -> TextConfig:
        return TextConfig(
            font_name=font_dd.value,
            font_size_mm=float(font_size_tf.value or 5),
            char_spacing_mm=float(char_spacing_tf.value or 0.8),
            word_spacing_mm=float(word_spacing_tf.value or 2.0),
            paragraph_indent_mm=float(para_indent_tf.value or 12.5),
            line_spacing_mm=float(line_spacing_tf.value or 8),
            variability=variability_sl.value,
            seed=0,
        )

    def _show_text_page(page_idx: int):
        """Show preview for a specific text page."""
        if not state["text_pages"] or page_idx < 0 or page_idx >= len(state["text_pages"]):
            return
        state["current_text_page"] = page_idx
        _, drawing, gcode = state["text_pages"][page_idx]
        state["text_gcode"] = gcode

        # Generate preview
        try:
            from core.gcode import drawing_to_preview
            nc = _build_notebook_config()
            preview_b64 = drawing_to_preview(drawing, cw=350, ch=490,
                                              work_area_x=nc.page_width_mm,
                                              work_area_y=nc.page_height_mm)
            if preview_b64:
                text_preview_img.src = f"data:image/png;base64,{preview_b64}"
                text_preview_img.visible = True
                text_preview_placeholder.visible = False
        except Exception:
            pass

        text_page_info.value = f"Страница {page_idx + 1} из {len(state['text_pages'])}"
        btn_prev_page.disabled = (page_idx == 0)
        btn_next_page.disabled = (page_idx >= len(state["text_pages"]) - 1)
        btn_send_text.disabled = False
        btn_save_gcode.disabled = False
        btn_save_gcode.visible = True
        status_text.value = f"Готово: {len(state['text_pages'])} страниц"
        status_text.color = ft.Colors.GREEN_400
        page.update()

    async def on_auto_optimize(e):
        text = text_input.value.strip()
        if not text:
            status_text.value = "Введите текст для анализа!"
            status_text.color = ft.Colors.ORANGE_400
            page.update()
            return
        nc = _build_notebook_config()
        result = auto_optimize_layout(text, nc.page_width_mm, nc.page_height_mm,
                                      nc.left_margin_mm, nc.top_margin_mm, nc.bottom_margin_mm)
        font_size_tf.value = str(result['font_size_mm'])
        line_spacing_tf.value = str(result['line_spacing_mm'])
        status_text.value = f"Оптимально: {result['font_size_mm']}мм шрифт, {result['estimated_pages']} стр."
        status_text.color = ft.Colors.GREEN_400
        page.update()

    btn_auto_opt.on_click = on_auto_optimize

    async def on_generate_text(e):
        text = text_input.value.strip()
        if not text:
            status_text.value = "Введите текст лекции!"
            status_text.color = ft.Colors.ORANGE_400
            page.update()
            return

        nc = _build_notebook_config()
        tc = _build_text_config()
        pc = _build_img_config()

        status_text.value = "Генерация конспекта..."
        status_text.color = ft.Colors.AMBER_400
        page.update()

        try:
            results = await asyncio.get_running_loop().run_in_executor(
                None, full_text_pipeline, text, nc, tc, pc
            )
            state["text_pages"] = results
            state["current_text_page"] = 0
            text_progress.value = f"Сгенерировано {len(results)} страниц"
            _show_text_page(0)
        except Exception as ex:
            status_text.value = f"Ошибка генерации: {ex}"
            status_text.color = ft.Colors.RED_400
            page.update()

    btn_generate_text.on_click = on_generate_text

    async def on_prev_page(e):
        _show_text_page(state["current_text_page"] - 1)

    async def on_next_page(e):
        _show_text_page(state["current_text_page"] + 1)

    btn_prev_page.on_click = on_prev_page
    btn_next_page.on_click = on_next_page

    # Загрузка текста из файла
    async def on_load_text(e):
        result = await file_picker.pick_files(
            dialog_title="Загрузить текстовый файл",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["txt"],
        )
        if not result:
            return
        try:
            with open(result[0].path, "r", encoding="utf-8") as f:
                text_input.value = f.read()
            status_text.value = f"Загружен: {os.path.basename(result[0].path)}"
            status_text.color = ft.Colors.GREEN_400
            page.update()
        except Exception as ex:
            status_text.value = f"Ошибка чтения: {ex}"
            status_text.color = ft.Colors.RED_400
            page.update()

    btn_load_text = ft.OutlinedButton("Загрузить .txt", icon=ft.Icons.FILE_OPEN)

    btn_load_text.on_click = on_load_text

    # ══════════════════════════════════════════════════════════════════════
    # ОБЩИЕ ДЕЙСТВИЯ
    # ══════════════════════════════════════════════════════════════════════

    async def on_save_gcode_click(e):
        gcode = state.get("text_gcode") or state.get("gcode")
        if not gcode:
            return
        result = await file_picker.save_file(
            dialog_title="Сохранить G-code",
            file_name="plot.gcode",
            allowed_extensions=["gcode", "nc", "txt"],
        )
        if result and result.path:
            with open(result.path, "w") as f:
                f.write(gcode)
            status_text.value = f"Сохранено: {os.path.basename(result.path)}"
            status_text.color = ft.Colors.GREEN_400
            page.update()

    btn_save_gcode.on_click = on_save_gcode_click

    async def on_send_current(e):
        gcode = state.get("text_gcode") or state.get("gcode")
        if not gcode:
            return
        await _send_gcode(gcode)

    async def _send_gcode(gcode: str):
        state["plotting"] = True
        btn_send_img.disabled = True
        btn_send_text.disabled = True
        btn_cancel.visible = True
        progress_bar.visible = True
        progress_bar.value = 0
        status_text.value = "Подключение..."
        status_text.color = ft.Colors.PURPLE_300
        page.update()

        port = port_dd.value

        def _worker():
            try:
                s = PlotterSender(port=port)
                state["sender"] = s
                s.connect()

                def on_progress(done, total):
                    progress_bar.value = done / total
                    eta = s.eta_seconds(done, total)
                    eta_str = f"{int(eta // 60)}м{int(eta % 60)}с" if eta > 0 else "..."
                    status_text.value = f"Печать... {done}/{total} Осталось {eta_str}"

                s.send(gcode, on_progress=on_progress)
                s.disconnect()
                status_text.value = "Печать завершена!"
                status_text.color = ft.Colors.GREEN_400
            except Exception as ex:
                status_text.value = f"Ошибка: {ex}"
                status_text.color = ft.Colors.RED_400
            finally:
                state["plotting"] = False
                btn_send_img.disabled = False
                btn_send_text.disabled = False
                btn_cancel.visible = False
                progress_bar.visible = False
                page.update()

        threading.Thread(target=_worker, daemon=True).start()

    btn_send_img.on_click = on_send_current
    btn_send_text.on_click = on_send_current

    async def on_cancel_click(e):
        if state["sender"]:
            state["sender"].cancel()
        status_text.value = "Отменено"
        status_text.color = ft.Colors.ORANGE_400
        btn_cancel.visible = False
        page.update()

    btn_cancel.on_click = on_cancel_click

    # ─── Ручное управление ───────────────────────────────────────────────
    async def on_connect_click(e):
        port = port_dd.value
        try:
            s = PlotterSender(port=port)
            s.connect()
            state["sender"] = s
            state["connected"] = True
            btn_home.disabled = False
            btn_pen_up.disabled = False
            btn_pen_down.disabled = False
            btn_connect.disabled = True
            status_text.value = f"Подключено к {port}"
            status_text.color = ft.Colors.GREEN_400
        except Exception as ex:
            status_text.value = f"Ошибка подключения: {ex}"
            status_text.color = ft.Colors.RED_400
        page.update()

    btn_connect.on_click = on_connect_click

    async def on_home_click(e):
        if state["sender"]:
            state["sender"].send_raw("G0 Z0")
            state["sender"].send_raw("G0 X0 Y0")
            status_text.value = "Домой"
            status_text.color = ft.Colors.GREEN_400
            page.update()

    btn_home.on_click = on_home_click

    async def on_pen_up_click(e):
        if state["sender"]:
            state["sender"].send_raw(f"G0 Z{pen_up_tf.value}")
            status_text.value = "Перо поднято"
            status_text.color = ft.Colors.GREEN_400
            page.update()

    btn_pen_up.on_click = on_pen_up_click

    async def on_pen_down_click(e):
        if state["sender"]:
            state["sender"].send_raw(f"G1 Z{pen_down_tf.value} F{speed_sl.value}")
            status_text.value = "Перо опущено"
            status_text.color = ft.Colors.GREEN_400
            page.update()

    btn_pen_down.on_click = on_pen_down_click

    def _switch_ui():
        """Toggle visibility between image mode and text mode UI groups."""
        is_text = tabs.selected_index == 1
        img_group.visible = not is_text
        text_group.visible = is_text
        # Update send button visibility
        btn_send_img.visible = not is_text
        btn_send_text.visible = is_text
        btn_pick.visible = not is_text
        if is_text:
            btn_save_gcode.visible = bool(state.get("text_gcode"))
        else:
            btn_save_gcode.visible = bool(state.get("gcode"))
        page.update()

    # ─── Tabs переключатель ──────────────────────────────────────────────
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        on_change=lambda e: _switch_ui(),
        tabs=[
            ft.Tab(text="🖼 Изображение", content=ft.Container()),
            ft.Tab(text="📝 Текст / Конспекты", content=ft.Container()),
        ],
    )

    # ══════════════════════════════════════════════════════════════════════
    # СБОРКА UI
    # ══════════════════════════════════════════════════════════════════════

    # --- IMAGE MODE CONTROLS ---
    img_group = ft.Column([
        ft.Text("Настройки изображения", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_300),
        ft.Row([style_dd, pen_down_tf, pen_up_tf, pen_down_delay_tf, pen_up_delay_tf, port_dd]),
        ft.Row([
            ft.Column([ft.Text("Ширина (мм)"), width_sl], width=200),
            ft.Column([ft.Text("Шаг (мм)"), spacing_sl], width=200),
            ft.Column([ft.Text("Скорость печати"), speed_sl], width=200),
            ft.Column([ft.Text("Скорость холостого"), travel_speed_sl], width=200),
        ]),
        ft.Row([
            ft.Column([ft.Text("Порог"), threshold_sl], width=200),
            ft.Column([ft.Text("Яркость"), brightness_sl], width=200),
            ft.Column([ft.Text("Контраст"), contrast_sl], width=200),
            ft.Column([ft.Text("Размытие"), blur_sl], width=200),
        ]),
        ft.Row([invert_chk, auto_invert_chk, work_x_tf, work_y_tf]),
        ft.Divider(height=10),
        # Image preview row
        ft.Row([
            ft.Column([
                ft.Text("Оригинал", size=12, color=ft.Colors.GREY_500),
                ft.Stack([img_placeholder, img_display], width=350, height=350),
                btn_pick,
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.VerticalDivider(width=20, color=ft.Colors.TRANSPARENT),
            ft.Column([
                ft.Text("Превью", size=12, color=ft.Colors.GREY_500),
                ft.Stack([preview_placeholder, preview_img], width=350, height=350),
                invert_indicator,
            ], alignment=ft.MainAxisAlignment.CENTER),
        ], alignment=ft.MainAxisAlignment.CENTER),
    ], visible=True)

    # --- TEXT MODE CONTROLS ---
    text_group = ft.Column([
        ft.Row([
            ft.Text("Текст лекции / конспекта", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.AMBER_300),
            btn_load_text,
        ]),
        text_input,
        ft.Divider(height=10),
        ft.Text("Формат тетради", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_300),
        ft.Row([
            page_w_tf, page_h_tf, left_margin_tf, right_margin_tf,
            top_margin_tf, bottom_margin_tf,
        ]),
        ft.Row([margin_line_chk, ruled_lines_chk]),
        ft.Divider(height=10),
        ft.Text("Параметры письма", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_300),
        ft.Row([font_dd, font_size_tf, line_spacing_tf, char_spacing_tf]),
        ft.Row([
            word_spacing_tf, para_indent_tf,
            ft.Column([ft.Text("Естественность"), variability_sl], width=200),
        ]),
        ft.Divider(height=10),
        ft.Text("Общие настройки плоттера", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_300),
        ft.Row([pen_down_tf, pen_up_tf, pen_down_delay_tf, pen_up_delay_tf, port_dd]),
        ft.Row([
            ft.Column([ft.Text("Скорость печати"), speed_sl], width=200),
            ft.Column([ft.Text("Скорость холостого"), travel_speed_sl], width=200),
        ]),
        ft.Divider(height=10),
        ft.Row([btn_generate_text, btn_auto_opt]),
        ft.Divider(height=10),
        # Page navigation + preview
        ft.Row([
            ft.Column([
                text_page_info,
                ft.Row([btn_prev_page, btn_next_page]),
            ]),
        ]),
        ft.Row([
            ft.Stack([text_preview_placeholder, text_preview_img], width=350, height=490),
            ft.VerticalDivider(width=20, color=ft.Colors.TRANSPARENT),
            ft.Column([
                text_progress,
                ft.Text("Страницы генерируются\nс фоном тетради\n(поля + линии строк)", size=12, color=ft.Colors.GREY_500),
            ]),
        ], alignment=ft.MainAxisAlignment.START),
    ], visible=False)

    # ─── Финальный layout ────────────────────────────────────────────────
    page.add(
        ft.Row([
            ft.Text("Horus Plotter", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.PURPLE_400),
            ft.Text("загрузи картинку или текст → плоттер нарисует", size=14, color=ft.Colors.GREY_500,
                    offset=ft.Offset(0, 8)),
        ]),
        tabs,
        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
        img_group,
        text_group,
        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
        ft.Row([btn_send_img, btn_send_text, btn_cancel, btn_save_gcode]),
        progress_bar,
        status_text,
        ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
        ft.Text("Ручное управление", size=14, weight=ft.FontWeight.W_600, color=ft.Colors.GREY_300),
        ft.Row([btn_connect, btn_home, btn_pen_up, btn_pen_down]),
    )


if __name__ == "__main__":
    ft.run(main)
