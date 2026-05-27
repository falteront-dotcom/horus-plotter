"""Test 2: hardcoded image + file picker with with_data"""
import base64
import flet as ft
from PIL import Image
import io

async def main(page: ft.Page):
    page.title = "Horus Test 2"
    page.theme_mode = ft.ThemeMode.DARK

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    # Hardcoded image test
    img = ft.Image(src="C:/Users/Semyon/horus-plotter/test_img.png", width=200, height=200, fit=ft.BoxFit.CONTAIN)
    status = ft.Text("Testing...", color=ft.Colors.GREY_400)

    # Test base64 preview
    pimg = Image.new("RGB", (100, 100), (108, 99, 255))
    buf = io.BytesIO()
    pimg.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    preview = ft.Image(src=f"data:image/png;base64,{b64}", width=200, height=200, fit=ft.BoxFit.FILL)

    async def on_pick(e):
        status.value = "Opening picker..."
        page.update()

        try:
            result = await file_picker.pick_files(
                dialog_title="Pick an image",
                file_type=ft.FilePickerFileType.IMAGE,
                with_data=True,
            )
            status.value = f"Result type: {type(result)}, len: {len(result) if result else 0}"
            if result:
                f = result[0]
                status.value = f"path={f.path}, name={f.name}, size={f.size}, has_bytes={f.bytes is not None}"
                if f.path:
                    img.src = f.path
                elif f.bytes:
                    b = base64.b64encode(f.bytes).decode()
                    img.src = f"data:image/png;base64,{b}"
            page.update()
        except Exception as ex:
            status.value = f"Error: {ex}"
            page.update()

    btn = ft.Button("Pick Image", icon=ft.Icons.IMAGE, on_click=on_pick)

    page.add(
        ft.Text("Hardcoded image (local path):"),
        img,
        ft.Text("Base64 preview:"),
        preview,
        btn,
        status,
    )

if __name__ == "__main__":
    ft.run(main)
