"""
Horus Plotter v4.0 — NEURAL DASHBOARD UI
Ultra-premium dark theme with particle effects, live neural status,
glassmorphism, and cinematic animations.
"""
import asyncio, math, random, threading, time, os

import flet as ft
import serial
import serial.tools.list_ports

from core.gcode import PlotConfig
from core.pipeline import image_to_gcode
from core.notebook import NotebookConfig
from core.text_engine import TextConfig
from core.text_pipeline import full_text_pipeline
from core.fonts import list_fonts, FONT_DISPLAY_NAMES
from core.vision import auto_optimize_layout
from core.improvements import estimate_plot_time, validate_config
from core.features import PlotHistoryDB

# ─── NEURAL THEME ──────────────────────────────────────────────────────────
PALETTE = {
    "bg": "#06060f",
    "surface": "#0e0e1f",
    "card": "#141429",
    "card_hover": "#1a1a40",
    "primary": "#7c3aed",
    "primary_glow": "#a78bfa",
    "primary_dim": "#5b21b6",
    "accent": "#06b6d4",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "text": "#e2e8f0",
    "text_dim": "#94a3b8",
    "text_muted": "#64748b",
    "border": "#1e1e3a",
    "border_glow": "#7c3aed40",
}

class ParticleSystem:
    """Animated neural particles in background."""
    def __init__(self, width=1100, height=900, count=80):
        self.width = width
        self.height = height
        self.particles = []
        self.connections = []
        for _ in range(count):
            self.particles.append({
                "x": random.uniform(0, width),
                "y": random.uniform(0, height),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.3, 0.3),
                "size": random.uniform(1.5, 3.5),
                "hue": random.choice([270, 280, 290, 200, 170]),
                "pulse": random.uniform(0, math.pi * 2),
            })
        # Pre-compute connections
        for i, a in enumerate(self.particles):
            for j, b in enumerate(self.particles[i+1:], i+1):
                if math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < 100:
                    self.connections.append((i, j))
    
    def update(self):
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["pulse"] += 0.02
            if p["x"] < -20: p["x"] = self.width + 20
            if p["x"] > self.width + 20: p["x"] = -20
            if p["y"] < -20: p["y"] = self.height + 20
            if p["y"] > self.height + 20: p["y"] = -20

class PlotterSender:
    def __init__(self, port="COM3", baud=115200):
        self.port = port; self.baud = baud; self._ser = None
        self._buf = ""; self._cancelled = False; self.start_time = None
    
    def connect(self):
        self._ser = serial.Serial(self.port, self.baud, timeout=1)
        time.sleep(1.5); self._buf = ""
        self._ser.reset_input_buffer()
        self._ser.write(b"$X\n"); self._read_ok()
        self.start_time = time.time()
    
    def _read_ok(self, timeout=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._ser.in_waiting:
                self._buf += self._ser.read(self._ser.in_waiting).decode(errors="replace")
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                if line.strip() in ("ok", ""): return True
                if line.strip().startswith("error"): return False
            time.sleep(0.01)
        return False
    
    def send(self, gcode, on_progress=None):
        cmds = [l.strip() for l in gcode.split("\n") if l.strip() and not l.startswith(";")]
        total = len(cmds); self._cancelled = False
        for i, cmd in enumerate(cmds):
            if self._cancelled: break
            self._ser.write((cmd + "\n").encode()); self._read_ok()
            if on_progress: on_progress(i + 1, total)
    
    def send_raw(self, cmd):
        if self._ser and self._ser.is_open:
            self._ser.write((cmd.strip() + "\n").encode()); self._read_ok()
    
    def cancel(self): self._cancelled = True
    def disconnect(self):
        if self._ser and self._ser.is_open: self._ser.close()
    
    def eta_seconds(self, done, total):
        if not self.start_time or done == 0: return 0
        elapsed = time.time() - self.start_time
        rate = done / elapsed
        return (total - done) / rate if rate > 0 else 0

def list_serial_ports(): return [p.device for p in serial.tools.list_ports.comports()]

# ─── NEURAL CANVAS ─────────────────────────────────────────────────────────
class NeuralCanvas(ft.UserControl):
    """Real-time animated neural network background."""
    def __init__(self, width=1100, height=200):
        super().__init__()
        self.width = width
        self.height = height
        self.particles = ParticleSystem(width, height, 60)
        self.frame = 0
    
    def build(self):
        self.canvas = ft.Canvas(
            [ft.Canvas(fill=ft.Paint(color=PALETTE["bg"]))],
            width=self.width, height=self.height,
        )
        return ft.Container(self.canvas, width=self.width, height=self.height)
    
    def did_mount(self):
        self.running = True
        self._tick()
    
    def will_unmount(self):
        self.running = False
    
    def _tick(self):
        if not self.running: return
        self.particles.update()
        self.frame += 1
        
        shapes = []
        ps = self.particles.particles
        
        # Draw connections (edges)
        for i, j in self.particles.connections:
            ax, ay = ps[i]["x"], ps[i]["y"]
            bx, by = ps[j]["x"], ps[j]["y"]
            dist = math.hypot(ax - bx, ay - by)
            alpha = max(0, 1 - dist / 100) * 0.15
            shapes.append(ft.Line(
                ax, ay, bx, by,
                ft.Paint(color="#7c3aed", stroke_width=0.5,
                         style=ft.PaintingStyle.STROKE),
            ))
        
        # Draw particles (nodes)
        for p in ps:
            glow = (math.sin(p["pulse"]) + 1) / 2
            r = p["size"]
            color = f"#{p['hue']:02x}"
            shapes.append(ft.Circle(
                p["x"], p["y"], r + glow * 2,
                ft.Paint(color="#7c3aed20", style=ft.PaintingStyle.FILL),
            ))
            shapes.append(ft.Circle(
                p["x"], p["y"], r,
                ft.Paint(color="#a78bfa", style=ft.PaintingStyle.FILL),
            ))
        
        self.canvas.shapes = shapes
        self.canvas.update()
        
        # Throttle updates
        threading.Timer(0.05, self._tick).start()

# ─── GLASS CARD ──────────────────────��─────────────────────────────────────
def glass_card(child, width=None, height=None, padding=20, border_glow=False):
    border = ft.Border.all(1, PALETTE["border_glow"] if border_glow else PALETTE["border"])
    return ft.Container(
        content=child,
        width=width, height=height,
        padding=padding,
        border_radius=16,
        border=border,
        bgcolor=PALETTE["card"],
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color="#00000040"),
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left, end=ft.alignment.bottom_right,
            colors=[PALETTE["card"], PALETTE["card_hover"]],
        ),
    )

def neural_button(text, icon=None, on_click=None, primary=False, small=False):
    """Glowing neural-styled button."""
    return ft.Container(
        content=ft.Row([
            ft.Icon(icon, size=18, color=PALETTE["primary_glow"]) if icon else ft.Container(),
            ft.Text(text, size=13 if small else 15,
                    color=PALETTE["primary_glow"] if not primary else "#fff",
                    weight=ft.FontWeight.W_600),
        ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        padding=ft.padding.symmetric(horizontal=20, vertical=10),
        border_radius=12,
        border=ft.Border.all(1, PALETTE["primary"] if not primary else PALETTE["primary_glow"]),
        bgcolor=PALETTE["primary_dim"] if not primary else PALETTE["primary"],
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=PALETTE["primary"] + "30"),
        on_click=on_click,
        ink=True,
    )

def status_badge(text, color, icon=None):
    return ft.Container(
        content=ft.Row([
            ft.Container(width=8, height=8, border_radius=4, bgcolor=color,
                        shadow=ft.BoxShadow(blur_radius=6, color=color + "80")),
            ft.Text(text, size=12, color=color, weight=ft.FontWeight.W_600),
        ], spacing=6),
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border_radius=20,
        border=ft.Border.all(1, color + "30"),
        bgcolor=color + "10",
    )

def stat_card(label, value, sub="", icon=None, color=PALETTE["primary_glow"]):
    return glass_card(
        ft.Column([
            ft.Row([ft.Icon(icon, size=16, color=color) if icon else ft.Container(),
                    ft.Text(label, size=11, color=PALETTE["text_muted"])], spacing=6),
            ft.Text(value, size=28, weight=ft.FontWeight.BOLD, color=color),
            ft.Text(sub, size=11, color=PALETTE["text_dim"]) if sub else ft.Container(),
        ], spacing=4),
        width=180, height=90, padding=15,
    )

# ─── MAIN APP ──────────────────────���───────────────────────────────────────
async def main(page: ft.Page):
    page.title = "Horus Neural Plotter"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 1280
    page.window.height = 900
    page.window.min_width = 1000
    page.window.min_height = 700
    page.padding = 0
    page.bgcolor = PALETTE["bg"]
    page.fonts = {"SpaceGrotesk": "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap"}

    _loop = asyncio.get_running_loop()
    
    state = {
        "image_path": None, "gcode": None, "text_gcode": None,
        "text_pages": [], "current_text_page": 0,
        "sender": None, "plotting": False, "connected": False,
        "current_tab": 0, "plot_count": 0, "total_plot_mm": 0,
    }
    
    file_picker = ft.FilePicker(); page.services.append(file_picker)
    
    # ─── SIDEBAR ────────────��──────────────────────────────────────────
    def on_nav_click(idx):
        return lambda e: switch_tab(idx)
    
    nav_items = [
        ("Dashboard", ft.Icons.DASHBOARD, 0),
        ("Текст / Конспекты", ft.Icons.EDIT_NOTE, 1),
        ("Изображения", ft.Icons.IMAGE, 2),
        ("История", ft.Icons.HISTORY, 3),
        ("Настройки", ft.Icons.SETTINGS, 4),
    ]
    
    nav_btns = []
    for label, icon, idx in nav_items:
        is_active = idx == 0
        nav_btns.append(ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=20, color=PALETTE["primary_glow"] if is_active else PALETTE["text_muted"]),
                ft.Text(label, size=13, color=PALETTE["primary_glow"] if is_active else PALETTE["text_dim"],
                       weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL),
            ], spacing=12),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=10,
            border=ft.Border(left=ft.BorderSide(3, PALETTE["primary"])) if is_active else None,
            bgcolor=PALETTE["primary_dim"] + "30" if is_active else None,
            on_click=on_nav_click(idx),
            ink=True,
            animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT),
        ))
    
    # Store nav buttons for updating active state
    for i, (_, _, _) in enumerate(nav_items):
        state[f"nav_{i}"] = nav_btns[i]
    
    def switch_tab(idx):
        state["current_tab"] = idx
        for i in range(len(nav_items)):
            container = nav_btns[i]
            is_active = i == idx
            container.border = ft.Border(left=ft.BorderSide(3, PALETTE["primary"])) if is_active else None
            container.bgcolor = PALETTE["primary_dim"] + "30" if is_active else None
            # Update icon + text color
            row = container.content
            row.controls[0].color = PALETTE["primary_glow"] if is_active else PALETTE["text_muted"]
            row.controls[1].color = PALETTE["primary_glow"] if is_active else PALETTE["text_dim"]
            row.controls[1].weight = ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL
            container.update()
        for i, panel in enumerate(content_panels):
            panel.visible = i == idx
            if panel.visible: panel.update()
        page.update()
    
    sidebar = ft.Container(
        content=ft.Column([
            # Logo
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text("⚡", size=24),
                        width=36, height=36, border_radius=10,
                        bgcolor=PALETTE["primary"],
                        alignment=ft.alignment.center,
                        shadow=ft.BoxShadow(blur_radius=12, color=PALETTE["primary"] + "60"),
                    ),
                    ft.Column([
                        ft.Text("HORUS", size=18, weight=ft.FontWeight.BOLD,
                               color=PALETTE["primary_glow"]),
                        ft.Text("neural plotter", size=10, color=PALETTE["text_muted"]),
                    ], spacing=-2),
                ], spacing=12),
                padding=ft.padding.only(bottom=30),
            ),
            # Navigation
            *nav_btns,
            # Bottom status
            ft.Container(expand=True),
            ft.Divider(color=PALETTE["border"]),
            status_badge("🧠 Neural Active", PALETTE["success"]),
        ], spacing=4),
        width=240, height=page.window.height,
        padding=20,
        bgcolor=PALETTE["surface"],
        border=ft.Border(right=ft.BorderSide(1, PALETTE["border"])),
    )
    
    # ─── TOP BAR ───────────────────────────────────────────────────────
    ports = list_serial_ports()
    port_val = ports[0] if ports else "COM3"
    
    top_bar = ft.Container(
        content=ft.Row([
            ft.Text("Dashboard", size=22, weight=ft.FontWeight.BOLD, color=PALETTE["text"]),
            ft.Row([], expand=True),  # spacer
            status_badge("🟢 GRBL Connected" if state["connected"] else "⚫ Offline",
                        PALETTE["success"] if state["connected"] else PALETTE["text_muted"]),
            ft.Container(width=10),
            ft.Text(port_val, size=12, color=PALETTE["text_muted"]),
            ft.Container(width=20),
            neural_button("Подключить", ft.Icons.CABLE, on_click=lambda e: connect_plotter(), small=True),
        ], spacing=12),
        padding=ft.padding.only(left=24, right=24, top=16, bottom=16),
        bgcolor=PALETTE["surface"],
        border=ft.Border(bottom=ft.BorderSide(1, PALETTE["border"])),
    )
    
    # ─── CONTENT PANELS ────────────────────────────────────────────────
    
    # Panel 0: DASHBOARD
    neural_canvas = NeuralCanvas(width=1040, height=180)
    
    dashboard = ft.Column([
        ft.Container(
            content=ft.Column([
                ft.Text("Нейронный статус", size=16, weight=ft.FontWeight.W_700,
                       color=PALETTE["primary_glow"]),
                ft.Text("Система активна. Двигатели откалиброваны. GRBL v1.1", size=12,
                       color=PALETTE["text_muted"]),
            ], spacing=4),
            padding=ft.padding.only(left=24, top=20),
        ),
        neural_canvas,
        ft.Container(height=20),
        ft.Row([
            stat_card("Страниц готово", "0", "на сегодня", ft.Icons.DESCRIPTION, PALETTE["primary_glow"]),
            stat_card("Время печати", "0 мин", "оценка", ft.Icons.TIMER, PALETTE["accent"]),
            stat_card("Команд G-code", "0", "всего", ft.Icons.CODE, PALETTE["warning"]),
            stat_card("Пройдено", "0 м", "пера", ft.Icons.STRAIGHTEN, PALETTE["success"]),
        ], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
        ft.Container(height=20),
        ft.Row([
            neural_button("📝 Новая лекция", ft.Icons.POST_ADD, on_click=lambda e: switch_tab(1)),
            neural_button("📥 Импорт текста", ft.Icons.FILE_OPEN, on_click=lambda e: file_picker.pick_files()),
            neural_button("🔍 Скан тетради", ft.Icons.CAMERA_ALT),
            neural_button("🚀 Начать печать", ft.Icons.PLAY_ARROW, primary=True,
                         on_click=lambda e: send_to_plotter()),
        ], spacing=12, alignment=ft.MainAxisAlignment.CENTER),
    ], scroll=ft.ScrollMode.AUTO)
    
    dashboard_panel = ft.Container(dashboard, padding=20, expand=True)
    
    # Panel 1: TEXT MODE (simplified for now — will be full later)
    text_input = ft.TextField(
        label="Текст лекции", multiline=True, min_lines=10, max_lines=15,
        width=700, border_radius=12,
        border_color=PALETTE["border"], cursor_color=PALETTE["primary_glow"],
        bgcolor=PALETTE["card"], text_style=ft.TextStyle(color=PALETTE["text"]),
    )
    
    font_dd = ft.Dropdown(
        label="Шрифт", width=220,
        options=[ft.dropdown.Option(k, v) for k, v in FONT_DISPLAY_NAMES.items()],
        value="semyon_cursive",
        border_radius=10, border_color=PALETTE["border"],
        bgcolor=PALETTE["card"], color=PALETTE["text"],
    )
    
    text_panel = ft.Container(
        ft.Column([
            ft.Text("📝 Текст / Конспекты", size=22, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            text_input,
            ft.Container(height=10),
            ft.Row([font_dd, neural_button("Авто-оптимизация", ft.Icons.TUNE),
                    neural_button("Сгенерировать", ft.Icons.AUTO_STORIES, primary=True)]),
            ft.Container(height=10),
            ft.Text("Превью появится здесь после генерации", size=12, color=PALETTE["text_muted"]),
        ], spacing=4),
        padding=30, expand=True,
    )
    
    # Panel 2: IMAGE MODE
    image_panel = ft.Container(
        ft.Column([
            ft.Text("🖼 Изображения", size=22, weight=ft.FontWeight.BOLD),
            ft.Text("Загрузите изображение для конвертации", size=12, color=PALETTE["text_muted"]),
        ]),
        padding=30, expand=True,
    )
    
    # Panel 3: HISTORY
    history_panel = ft.Container(
        ft.Column([
            ft.Text("📋 История", size=22, weight=ft.FontWeight.BOLD),
            ft.Text("Здесь будет история всех печатей", size=12, color=PALETTE["text_muted"]),
        ]),
        padding=30, expand=True,
    )
    
    # Panel 4: SETTINGS
    settings_panel = ft.Container(
        ft.Column([
            ft.Text("⚙️ Настройки", size=22, weight=ft.FontWeight.BOLD),
            ft.Text("Настройки плоттера и приложения", size=12, color=PALETTE["text_muted"]),
        ]),
        padding=30, expand=True,
    )
    
    content_panels = [dashboard_panel, text_panel, image_panel, history_panel, settings_panel]
    for p in content_panels[1:]: p.visible = False
    
    # ─── ASSEMBLE ──────────────────────────────────────────────────────
    main_content = ft.Column([
        top_bar,
        ft.Stack(content_panels, expand=True),
    ], expand=True)
    
    page.add(
        ft.Row([
            sidebar,
            ft.VerticalDivider(width=1, color=PALETTE["border"]),
            main_content,
        ], spacing=0, expand=True),
    )
    
    # ─── ACTIONS ───────────────────────────────────────────────────────
    def connect_plotter():
        try:
            s = PlotterSender(port=port_val)
            s.connect()
            state["sender"] = s
            state["connected"] = True
            page.update()
        except Exception as e:
            print(f"Connect error: {e}")
    
    def send_to_plotter():
        pass  # Will be wired up

if __name__ == "__main__":
    ft.run(main)
