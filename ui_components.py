"""UI Components for Horus Plotter — reusable neural-styled widgets."""
import flet as ft

PALETTE = {
    "bg": "#06060f", "surface": "#0e0e1f", "card": "#141429",
    "card_hover": "#1a1a40", "primary": "#7c3aed", "primary_glow": "#a78bfa",
    "primary_dim": "#5b21b6", "accent": "#06b6d4", "success": "#10b981",
    "warning": "#f59e0b", "danger": "#ef4444", "text": "#e2e8f0",
    "text_dim": "#94a3b8", "text_muted": "#64748b", "border": "#1e1e3a",
    "border_glow": "#7c3aed40",
}

def glass_card(child, width=None, height=None, padding=20, border_glow=False):
    border = ft.Border.all(1, PALETTE["border_glow"] if border_glow else PALETTE["border"])
    return ft.Container(
        content=child, width=width, height=height, padding=padding,
        border_radius=16, border=border, bgcolor=PALETTE["card"],
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color="#00000040"),
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
            colors=[PALETTE["card"], PALETTE["card_hover"]],
        ),
    )

def neural_button(text, icon=None, on_click=None, primary=False, small=False):
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
        on_click=on_click, ink=True,
    )

def status_badge(text, color, icon=None):
    return ft.Container(
        content=ft.Row([
            ft.Container(width=8, height=8, border_radius=4, bgcolor=color,
                        shadow=ft.BoxShadow(blur_radius=6, color=color + "80")),
            ft.Text(text, size=12, color=color, weight=ft.FontWeight.W_600),
        ], spacing=6),
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        border_radius=20, border=ft.Border.all(1, color + "30"),
        bgcolor=color + "10",
    )

def stat_card(label, value, sub="", icon=None, color=None):
    if color is None: color = PALETTE["primary_glow"]
    return glass_card(
        ft.Column([
            ft.Row([ft.Icon(icon, size=16, color=color) if icon else ft.Container(),
                    ft.Text(label, size=11, color=PALETTE["text_muted"])], spacing=6),
            ft.Text(value, size=28, weight=ft.FontWeight.BOLD, color=color),
            ft.Text(sub, size=11, color=PALETTE["text_dim"]) if sub else ft.Container(),
        ], spacing=4),
        width=180, height=90, padding=15,
    )
