from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    config: Path
    database: Path
    oauth_cache: Path
    logs_dir: Path
    log_file: Path

    @classmethod
    def create(cls) -> AppPaths:
        root = Path(user_data_path("SpotifySchedulerPro", appauthor=False, ensure_exists=True))
        logs_dir = root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            root=root,
            config=root / "config.json",
            database=root / "scheduler.db",
            oauth_cache=root / "spotify_cache.json",
            logs_dir=logs_dir,
            log_file=logs_dir / "app.log",
        )
