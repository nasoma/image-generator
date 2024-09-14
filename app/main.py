import flet as ft
import requests
import json
import base64
from io import BytesIO
from PIL import Image
import threading
import os

from flet import ThemeMode, Theme, ColorScheme, colors
from flet_core import TextStyle


def generate_image(prompt, width, height, api_key):
    url = "https://api.deepinfra.com/v1/inference/black-forest-labs/FLUX-1-schnell"
    headers = {"Authorization": f"bearer {api_key}"}
    data = {"prompt": prompt, "width": width, "height": height}
    json_data = json.dumps(data)

    response = requests.post(url, headers=headers, data=json_data)

    if response.status_code == 200:
        response_data = response.json()
        image_data = response_data['images'][0].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        return image
    else:
        return None


def main(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = 20
    page.window.resizable = False
    page.window.width = 400
    page.window.center()

    # Define light and dark themes
    light_theme = Theme(
        color_scheme_seed="#524A20",
        color_scheme=ColorScheme(
            primary="#6B5E10",
            on_primary=colors.WHITE,
            secondary="#655F40",
            on_secondary=colors.WHITE,
            surface_variant="#E9E2D0",
        )
    )

    dark_theme = Theme(
        color_scheme_seed="#524A20",
        color_scheme=ColorScheme(
            primary="#D8C76F",
            on_primary="#383000",
            secondary="#D0C7A2",
            on_secondary="#363116",
            surface_variant="#4A4739",
        )
    )

    # Start with the light theme
    page.theme = light_theme
    page.theme_mode = ThemeMode.LIGHT

    api_key = ""
    generated_image = None
    is_generating = False

    # Image dimensions - use Dropdown now
    image_width = 512
    image_height = 512

    def settings_page():
        nonlocal api_key, page

        def save_api_key(e):
            nonlocal api_key
            api_key = api_key_field.value
            page.go("/")

        api_key_field = ft.TextField(label="DeepInfra API Key",
                                     label_style=TextStyle(size=10),
                                     text_size=12, bgcolor=page.theme.color_scheme.surface_variant)
        save_button = ft.FilledButton("Save", on_click=save_api_key, expand=True, width=page.width)

        return ft.Column(
            [
                api_key_field,
                save_button,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def main_page():
        nonlocal generated_image, is_generating, image_width, image_height

        def submit_prompt(e=None):
            nonlocal generated_image, is_generating, image_width, image_height
            if is_generating:
                return
            prompt = prompt_field.value
            if not prompt:
                page.open(ft.SnackBar(content=ft.Text("Please enter a prompt before generating an image.")))
                return

            is_generating = True
            image_view.src_base64 = None
            image_view.visible = False
            placeholder_text.visible = True
            download_button.visible = False
            progress_bar.visible = True
            page.update()

            def generate():
                nonlocal generated_image, is_generating, image_width, image_height
                try:
                    image = generate_image(prompt, image_width, image_height, api_key)
                    if image:
                        generated_image = image
                        image_bytes = BytesIO()
                        image.save(image_bytes, format="PNG")
                        image_bytes.seek(0)
                        image_view.src_base64 = base64.b64encode(image_bytes.getvalue()).decode()
                        image_view.visible = True
                        placeholder_text.visible = False
                        download_button.visible = True
                        page.update()
                    else:
                        image_view.src_base64 = None
                        image_view.visible = False
                        placeholder_text.visible = True
                        download_button.visible = False
                        page.open(ft.SnackBar(content=ft.Text("Failed to generate image. Please try again.")))
                except Exception as e:
                    print(f"Error generating image: {e}")
                    image_view.src_base64 = None
                    image_view.visible = False
                    placeholder_text.visible = True
                    download_button.visible = False
                    page.open(ft.SnackBar(content=ft.Text("An error occurred while generating the image.")))
                finally:
                    is_generating = False
                    progress_bar.visible = False
                    page.update()

            threading.Thread(target=generate).start()

        def on_prompt_change(e):
            if e.control.value.endswith("\n"):
                e.control.value = e.control.value.strip()
                submit_prompt()

        def save_image_result(e: ft.FilePickerResultEvent):
            save_path = e.path if e.path else e.files[0].path
            save_image(save_path)

        def save_image(path):
            nonlocal generated_image
            if generated_image and path:
                try:
                    if not path.lower().endswith('.png'):
                        path += '.png'
                    generated_image.save(path)
                    # Get the directory name and file name
                    dir_name = os.path.dirname(path)
                    file_name = os.path.basename(path)
                    # Get just the last folder name in the path
                    last_folder = os.path.basename(dir_name)
                    page.open(ft.SnackBar(content=ft.Text(f"Image saved as '{file_name}' in folder '{last_folder}'")))

                except Exception as save_error:
                    error_message = f"Error saving image: {str(save_error)}"
                    print(error_message)
                    page.open(ft.SnackBar(content=ft.Text(error_message)))
            else:
                if not generated_image:
                    page.open(
                        ft.SnackBar(content=ft.Text("No image to save. Please generate an image first.")))
                elif not path:
                    page.open(ft.SnackBar(content=ft.Text("No save location selected.")))

        def download_image(e):
            if generated_image:
                save_file_dialog.save_file(
                    file_name="generated_image.png",
                    allowed_extensions=["png"]
                )
            else:
                page.open(
                    ft.SnackBar(content=ft.Text("No image to save. Please generate an image first.")))

        def clear_prompt(e):
            prompt_field.value = ""
            width_dropdown.value = "512"
            height_dropdown.value = "512"
            page.update()

        def on_width_change(e):
            nonlocal image_width
            image_width = int(e.control.value)

        def on_height_change(e):
            nonlocal image_height
            image_height = int(e.control.value)

        prompt_field = ft.TextField(
            label="Enter your prompt",
            text_size=12,
            multiline=True,
            bgcolor=page.theme.color_scheme.surface_variant,
            min_lines=1,
            max_lines=3,
            on_change=on_prompt_change,
            border_radius=ft.border_radius.all(4),
            expand=True,
            label_style=ft.TextStyle(size=12)
        )

        # Use Dropdown for width and height
        width_dropdown = ft.Dropdown(
            width=150,
            options=[
                ft.dropdown.Option(value) for value in
                [128, 256, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024]
            ],
            value=str(image_width),  # Default value
            on_change=on_width_change,
            label="Width",
            bgcolor=page.theme.color_scheme.surface_variant,
            hint_text="Select a width for your image",
            border_radius=ft.border_radius.all(4),
            label_style=ft.TextStyle(size=10),
            text_size=12,
            content_padding=ft.padding.symmetric(0, 10),
            height=30
        )
        height_dropdown = ft.Dropdown(
            width=150,
            options=[
                ft.dropdown.Option(value) for value in
                [128, 256, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024]
            ],
            value=str(image_height),  # Default value
            on_change=on_height_change,
            bgcolor=page.theme.color_scheme.surface_variant,
            hint_text="Select a height for your image",
            border_radius=ft.border_radius.all(4),
            label="Height",
            label_style=ft.TextStyle(size=10),
            text_size=12,
            content_padding=ft.padding.symmetric(0, 10),
            height=30
        )
        submit_button = ft.ElevatedButton(
            "Generate Image", on_click=submit_prompt, bgcolor=page.theme.color_scheme.primary,
            color=page.theme.color_scheme.on_primary
        )
        clear_button = ft.ElevatedButton(
            "Clear Prompt", on_click=clear_prompt, bgcolor=page.theme.color_scheme.primary,
            color=page.theme.color_scheme.on_primary
        )
        image_view = ft.Image(
            src_base64=None, width=image_width, height=image_height, fit=ft.ImageFit.CONTAIN, visible=False
        )
        placeholder_text = ft.Text("The image is being generated", size=14, visible=False)
        download_button = ft.ElevatedButton(
            "Download Image", on_click=download_image, visible=False, bgcolor=page.theme.color_scheme.primary,
            color=page.theme.color_scheme.on_primary
        )
        progress_bar = ft.ProgressBar(visible=False, color=page.theme.color_scheme.secondary, height=3)
        save_file_dialog = ft.FilePicker(on_result=save_image_result)
        page.overlay.append(save_file_dialog)

        return ft.Column(
            [
                prompt_field,
                ft.Row(  # Row for width and height dropdowns
                    [
                        width_dropdown,
                        height_dropdown,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER  # Center horizontally
                ),
                ft.Row([submit_button, clear_button], alignment=ft.MainAxisAlignment.CENTER),
                ft.Stack(
                    [
                        ft.Container(
                            content=placeholder_text,
                            alignment=ft.alignment.center,
                            bgcolor=page.theme.color_scheme.surface_variant,
                            border_radius=ft.border_radius.all(2),
                        ),
                        image_view,
                        progress_bar,
                    ],
                    width=256,
                    height=256,
                ),
                ft.Container(content=download_button, alignment=ft.alignment.center),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=400
        )

    def route_change(route):
        page.views.clear()
        if page.route == "/settings":
            page.views.append(
                ft.View(
                    "/settings",
                    [
                        ft.AppBar(
                            title=ft.Text("Settings"),
                            title_text_style=ft.TextStyle(size=12, color=page.theme.color_scheme.on_secondary),
                            bgcolor=page.theme.color_scheme.secondary,
                            actions=[
                                ft.IconButton(
                                    icon=ft.icons.LIGHT_MODE_OUTLINED if page.theme_mode == ThemeMode.LIGHT else ft.icons.DARK_MODE_OUTLINED,
                                    on_click=toggle_theme,  # Define toggle_theme here
                                    icon_color=page.theme.color_scheme.on_secondary,
                                )
                            ]
                        ),
                        settings_page(),
                    ],
                )
            )
        else:
            page.views.append(
                ft.View(
                    "/",
                    [
                        ft.AppBar(
                            title=ft.Text("AI Image Generator"),
                            bgcolor=page.theme.color_scheme.secondary,
                            title_text_style=ft.TextStyle(size=12, color=page.theme.color_scheme.on_secondary),
                            actions=[
                                ft.IconButton(
                                    icon=ft.icons.SETTINGS,
                                    icon_color=page.theme.color_scheme.on_secondary,
                                    on_click=lambda _: page.go("/settings")
                                )
                            ]
                        ),
                        main_page(),
                    ],
                )
            )
        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    def toggle_theme(e):  # Define toggle_theme here
        nonlocal page
        if page.theme_mode == ThemeMode.LIGHT:
            page.theme = dark_theme
            page.theme_mode = ThemeMode.DARK
            page.go("/")
        else:
            page.theme = light_theme
            page.theme_mode = ThemeMode.LIGHT
            page.go("/")
        page.update()

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)


ft.app(target=main)