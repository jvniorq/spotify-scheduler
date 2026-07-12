from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

from .branding import LEGACY_AUTOSTART_NAME

APP_NAME = LEGACY_AUTOSTART_NAME


def _windows_startup_shortcut() -> Path:
    appdata = Path(os.environ.get("APPDATA", Path.home()))
    return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"{APP_NAME}.cmd"


def set_start_with_windows(enabled: bool) -> None:
    if platform.system() != "Windows":
        return

    shortcut = _windows_startup_shortcut()
    shortcut.parent.mkdir(parents=True, exist_ok=True)

    if not enabled:
        shortcut.unlink(missing_ok=True)
        return

    if getattr(sys, "frozen", False):
        command = f'@start "" "{Path(sys.executable)}" --minimized\r\n'
    else:
        python = Path(sys.executable)
        pythonw = python.with_name("pythonw.exe")
        if pythonw.exists():
            python = pythonw
        command = f'@start "" "{python}" -m spotify_scheduler_pro --minimized\r\n'
    shortcut.write_text(command, encoding="utf-8")


def start_with_windows_enabled() -> bool:
    if platform.system() != "Windows":
        return False
    return _windows_startup_shortcut().exists()
