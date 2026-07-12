from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import keyring
from keyring.errors import KeyringError

SERVICE_NAME = "SpotifySchedulerPro"
SECRET_KEY = "spotify_client_secret"


@dataclass
class AppConfig:
    client_id: str = ""
    redirect_uri: str = "http://127.0.0.1:23918"
    default_device_name: str = ""
    polling_seconds: float = 3.0
    pause_outside_schedule: bool = True
    launch_spotify_if_missing: bool = True
    skip_explicit: bool = False
    start_minimized: bool = False
    minimize_to_tray: bool = True
    start_with_windows: bool = False
    prevent_sleep: bool = False
    random_queue_limit: int = 100
    avoid_recent_tracks: int = 30
    language: str = "es"


class ConfigManager:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> AppConfig:
        if not self.path.exists():
            config = AppConfig()
            self.save(config)
            return config

        try:
            loaded: Any = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}

        raw: dict[str, Any] = loaded if isinstance(loaded, dict) else {}
        defaults = asdict(AppConfig())
        values = {key: raw.get(key, default) for key, default in defaults.items()}
        return AppConfig(**values)

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def save_client_secret(secret: str) -> None:
        try:
            if secret:
                keyring.set_password(SERVICE_NAME, SECRET_KEY, secret)
            else:
                try:
                    keyring.delete_password(SERVICE_NAME, SECRET_KEY)
                except KeyringError:
                    pass
        except KeyringError as exc:
            raise RuntimeError(
                "No fue posible guardar el Client Secret en el almacén seguro del sistema."
            ) from exc

    @staticmethod
    def get_client_secret() -> str:
        try:
            return keyring.get_password(SERVICE_NAME, SECRET_KEY) or ""
        except KeyringError:
            return ""

    @staticmethod
    def delete_client_secret() -> None:
        try:
            keyring.delete_password(SERVICE_NAME, SECRET_KEY)
        except KeyringError:
            pass
