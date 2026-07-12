from __future__ import annotations

import logging
import tkinter as tk

from .config import ConfigManager
from .gui.main_window import MainWindow
from .logging_setup import configure_logging
from .paths import AppPaths
from .spotify_client import SpotifyService
from .storage import Storage

LOGGER = logging.getLogger("spotify_scheduler_pro.app")


def create_application(*, start_minimized: bool = False) -> tuple[tk.Tk, MainWindow]:
    paths = AppPaths.create()
    configure_logging(paths.log_file)

    config_manager = ConfigManager(paths.config)
    storage = Storage(paths.database)
    spotify = SpotifyService(config_manager, paths, storage)

    root = tk.Tk()
    window = MainWindow(
        root,
        paths=paths,
        config_manager=config_manager,
        storage=storage,
        spotify=spotify,
        start_minimized=start_minimized,
    )
    return root, window


def run(*, start_minimized: bool = False) -> None:
    root, _window = create_application(start_minimized=start_minimized)
    root.mainloop()
