
from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from PIL import Image, ImageDraw

from .branding import DISPLAY_NAME

LOGGER = logging.getLogger("spotify_scheduler_pro.tray")


def _make_icon() -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (5, 5, 59, 59),
        radius=17,
        fill=(18, 26, 43, 255),
        outline=(124, 92, 252, 255),
        width=3,
    )
    draw.arc((16, 14, 48, 36), start=190, end=350, fill=(56, 214, 199, 255), width=5)
    draw.arc((16, 28, 48, 50), start=10, end=170, fill=(124, 92, 252, 255), width=5)
    draw.ellipse((42, 17, 48, 23), fill=(56, 214, 199, 255))
    draw.ellipse((16, 41, 22, 47), fill=(124, 92, 252, 255))
    return image


class TrayController:
    def __init__(
        self,
        show_callback: Callable[[], None],
        pause_callback: Callable[[], bool],
        exit_callback: Callable[[], None],
    ):
        self.show_callback = show_callback
        self.pause_callback = pause_callback
        self.exit_callback = exit_callback
        self._icon = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        try:
            import pystray
        except ImportError:
            LOGGER.warning("pystray no está instalado; bandeja deshabilitada.")
            return

        def show(_icon=None, _item=None):
            self.show_callback()

        def pause(_icon=None, _item=None):
            paused = self.pause_callback()
            if self._icon:
                self._icon.title = (
                    f"{DISPLAY_NAME} · Pausado"
                    if paused
                    else f"{DISPLAY_NAME} · Activo"
                )

        def quit_app(_icon=None, _item=None):
            self.exit_callback()

        self._icon = pystray.Icon(
            DISPLAY_NAME,
            _make_icon(),
            DISPLAY_NAME,
            menu=pystray.Menu(
                pystray.MenuItem(f"Abrir {DISPLAY_NAME}", show, default=True),
                pystray.MenuItem("Pausar/Reanudar automatización", pause),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Salir", quit_app),
            ),
        )
        self._thread = threading.Thread(
            target=self._icon.run,
            name="TrayIcon",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                LOGGER.exception("No se pudo detener el icono de bandeja.")
            self._icon = None
