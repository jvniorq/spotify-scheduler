from __future__ import annotations

import ctypes
import logging
import os
import platform
import subprocess
from pathlib import Path

import psutil

LOGGER = logging.getLogger("spotify_scheduler_pro.system")

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def set_prevent_sleep(enabled: bool) -> None:
    if platform.system() != "Windows":
        return
    flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED if enabled else ES_CONTINUOUS
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
    except Exception:
        LOGGER.exception("No fue posible cambiar la política de suspensión.")


def spotify_process_running() -> bool:
    names = {"spotify.exe", "spotify"}
    for process in psutil.process_iter(["name"]):
        try:
            if str(process.info.get("name") or "").casefold() in names:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def launch_spotify() -> bool:
    system = platform.system()

    try:
        if system == "Windows":
            candidates = [
                Path(os.environ.get("APPDATA", "")) / "Spotify" / "Spotify.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps" / "Spotify.exe",
            ]
            for candidate in candidates:
                if candidate.exists():
                    subprocess.Popen([str(candidate)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
            os.startfile("spotify:")  # type: ignore[attr-defined]
            return True

        if system == "Darwin":
            subprocess.Popen(["open", "-a", "Spotify"])
            return True

        subprocess.Popen(["spotify"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        LOGGER.exception("No fue posible iniciar Spotify.")
        return False
