"""Minimal test: file picker + image display in Flet 0.84"""
import flet as ft

async def main(page: ft.Page):
    page.title = "Horus Test"
    page.theme_mode = ft.ThemeMode.DARK

    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    img = ft.Image(src="", width=300, height=300, fit=ft.BoxFit.CONTAIN, visible=False)
    status = ft.Text("Click the button", color=ft.Colors.GREY_400)

    async def on_pick(e):
        status.value = "Opening picker..."
        page.update()

        result = await file_picker.pick_files(
            dialog_title="Pick an image",
            file_type=ft.FilePickerFileType.IMAGE,
        )

        status.value = f"pick_files returned: {result}"
        page.update()

        if result and len(result) > 0:
            path = result[0].path
            status.value = f"Path: {path}"
            img.src = path
            img.visible = True
            page.update()
        else:
            status.value = "No file selected or result is empty"
            page.update()

    btn = ft.Button("Pick Image", icon=ft.Icons.IMAGE, on_click=on_pick)

    page.add(btn, img, status)

if __name__ == "__main__":
    ft.run(main)
