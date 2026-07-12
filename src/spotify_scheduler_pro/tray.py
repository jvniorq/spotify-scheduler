from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from PIL import Image, ImageDraw

LOGGER = logging.getLogger("spotify_scheduler_pro.tray")


def _make_icon() -> Image.Image:
    image = Image.new("RGBA", (64, 64), (24, 24, 24, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((5, 5, 59, 59), fill=(30, 215, 96, 255))
    draw.arc((18, 20, 48, 42), start=210, end=330, fill=(15, 15, 15, 255), width=4)
    draw.arc((20, 27, 46, 47), start=210, end=330, fill=(15, 15, 15, 255), width=4)
    draw.arc((22, 34, 44, 52), start=210, end=330, fill=(15, 15, 15, 255), width=4)
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
                    "Spotify Scheduler Pro · Pausado"
                    if paused
                    else "Spotify Scheduler Pro · Activo"
                )

        def quit_app(_icon=None, _item=None):
            self.exit_callback()

        self._icon = pystray.Icon(
            "SpotifySchedulerPro",
            _make_icon(),
            "Spotify Scheduler Pro",
            menu=pystray.Menu(
                pystray.MenuItem("Mostrar", show, default=True),
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
