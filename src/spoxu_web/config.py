from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class WebSettings:
    environment: str
    base_url: str
    data_dir: Path
    timezone: str
    cookie_secure: bool
    automation_enabled: bool
    session_secret: str
    admin_password_hash: str
    token_encryption_key: str
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str

    @property
    def database_path(self) -> Path:
        return self.data_dir / "spoxu.sqlite3"

    @property
    def token_path(self) -> Path:
        return self.data_dir / "spotify.token"

    @classmethod
    def from_env(cls) -> "WebSettings":
        settings = cls(
            environment=os.getenv("SPOXU_ENVIRONMENT", "production").strip().lower(),
            base_url=os.getenv("SPOXU_BASE_URL", "").strip().rstrip("/"),
            data_dir=Path(os.getenv("SPOXU_DATA_DIR", "/data")),
            timezone=os.getenv("SPOXU_TIMEZONE", "America/Lima").strip(),
            cookie_secure=_env_bool("SPOXU_COOKIE_SECURE", True),
            automation_enabled=_env_bool("SPOXU_AUTOMATION_ENABLED", True),
            session_secret=os.getenv("SPOXU_SESSION_SECRET", ""),
            admin_password_hash=os.getenv("SPOXU_ADMIN_PASSWORD_HASH", ""),
            token_encryption_key=os.getenv("SPOXU_TOKEN_ENCRYPTION_KEY", ""),
            spotify_client_id=os.getenv("SPOXU_SPOTIFY_CLIENT_ID", ""),
            spotify_client_secret=os.getenv("SPOXU_SPOTIFY_CLIENT_SECRET", ""),
            spotify_redirect_uri=os.getenv("SPOXU_SPOTIFY_REDIRECT_URI", ""),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        errors: list[str] = []
        if self.environment not in {"production", "development", "test"}:
            errors.append("SPOXU_ENVIRONMENT debe ser production, development o test.")
        if len(self.session_secret) < 32:
            errors.append("SPOXU_SESSION_SECRET debe tener al menos 32 caracteres.")
        if not self.admin_password_hash.startswith("$argon2"):
            errors.append("SPOXU_ADMIN_PASSWORD_HASH debe ser un hash Argon2.")
        try:
            Fernet(self.token_encryption_key.encode("ascii"))
        except Exception:
            errors.append("SPOXU_TOKEN_ENCRYPTION_KEY debe ser una clave Fernet válida.")

        if not self.spotify_client_id:
            errors.append("Falta SPOXU_SPOTIFY_CLIENT_ID.")
        if not self.spotify_client_secret:
            errors.append("Falta SPOXU_SPOTIFY_CLIENT_SECRET.")
        if not self.spotify_redirect_uri:
            errors.append("Falta SPOXU_SPOTIFY_REDIRECT_URI.")
        else:
            parsed = urlparse(self.spotify_redirect_uri)
            loopback = parsed.hostname in {"127.0.0.1", "::1"}
            if self.environment == "production" and parsed.scheme != "https" and not loopback:
                errors.append("Spotify Redirect URI debe usar HTTPS en producción.")

        if self.environment == "production" and not self.cookie_secure:
            errors.append("SPOXU_COOKIE_SECURE debe estar activo en producción.")
        if errors:
            raise ValueError(" ".join(errors))
