from __future__ import annotations

import base64
import io
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path.cwd()
PAYLOAD = ROOT / ".github" / "bootstrap" / "spotify-scheduler-pro.zip.b64"
PREFIX = "spotify-scheduler-pro/"

payload_text = PAYLOAD.read_text(encoding="utf-8").strip()
payload_bytes = base64.b64decode(payload_text, validate=True)
code_of_conduct = (ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")
bootstrap_source = Path(__file__).read_text(encoding="utf-8")
bootstrap_workflow_path = ROOT / ".github" / "workflows" / "bootstrap-pro.yml"
bootstrap_workflow = bootstrap_workflow_path.read_text(encoding="utf-8")

subprocess.run(["git", "rm", "-rf", "--", "."], check=True)

with zipfile.ZipFile(io.BytesIO(payload_bytes)) as archive:
    bad_member = archive.testzip()
    if bad_member is not None:
        raise RuntimeError(f"ZIP corrupto: {bad_member}")

    for info in archive.infolist():
        if info.is_dir() or not info.filename.startswith(PREFIX):
            continue
        relative = info.filename[len(PREFIX):]
        if not relative or relative == "CODIGO_COMPLETO.txt":
            continue
        target = (ROOT / relative).resolve()
        if ROOT.resolve() not in target.parents:
            raise RuntimeError(f"Ruta insegura en ZIP: {info.filename}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(info.filename))

(ROOT / "CODE_OF_CONDUCT.md").write_text(code_of_conduct, encoding="utf-8")
bootstrap_dir = ROOT / ".github" / "bootstrap"
bootstrap_dir.mkdir(parents=True, exist_ok=True)
(ROOT / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
(ROOT / ".github" / "bootstrap" / "apply.py").write_text(
    bootstrap_source,
    encoding="utf-8",
)
PAYLOAD.write_text(payload_text, encoding="utf-8")
bootstrap_workflow_path.write_text(bootstrap_workflow, encoding="utf-8")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: se esperaba una coincidencia y se encontraron {count}")
    write(path, text.replace(old, new, 1))


replace_once(
    "pyproject.toml",
    """authors = [
  {name = "Szymon Andrzejewski", email = "upstream-author@example.invalid"},
  {name = "Modified educational edition"}
]""",
    """authors = [
  {name = "Szymon Andrzejewski"},
  {name = "Spotify Scheduler Pro contributors"}
]""",
)

for script in ("run_windows.ps1", "build_exe.ps1"):
    replace_once(
        script,
        '$ErrorActionPreference = "Stop"\n\n',
        '$ErrorActionPreference = "Stop"\nSet-Location -LiteralPath $PSScriptRoot\n\n',
    )

replace_once(
    "src/spotify_scheduler_pro/config.py",
    """        try:
            raw: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}

        defaults = asdict(AppConfig())""",
    """        try:
            loaded: Any = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}

        raw: dict[str, Any] = loaded if isinstance(loaded, dict) else {}
        defaults = asdict(AppConfig())""",
)

replace_once(
    "src/spotify_scheduler_pro/models.py",
    "        return self.end_time <= self.start_time",
    "        return self.end_time < self.start_time",
)
replace_once(
    "src/spotify_scheduler_pro/models.py",
    """        if not self.playlist_id.strip():
            errors.append("Debes ingresar una playlist.")
        if self.kind == ScheduleKind.WEEKLY""",
    """        if not self.playlist_id.strip():
            errors.append("Debes ingresar una playlist.")
        if self.start_time == self.end_time:
            errors.append("La hora inicial y final no pueden ser iguales.")
        if self.kind == ScheduleKind.WEEKLY""",
)
replace_once(
    "src/spotify_scheduler_pro/models.py",
    '    def copy_with(self, **changes: Any) -> "ScheduleEntry":',
    "    def copy_with(self, **changes: Any) -> ScheduleEntry:",
)
replace_once(
    "src/spotify_scheduler_pro/paths.py",
    '    def create(cls) -> "AppPaths":',
    "    def create(cls) -> AppPaths:",
)

replace_once(
    "src/spotify_scheduler_pro/storage.py",
    "from typing import Iterator",
    "from collections.abc import Iterator",
)
replace_once(
    "src/spotify_scheduler_pro/storage.py",
    """            conn = sqlite3.connect(self.database_path)
            conn.row_factory = sqlite3.Row""",
    """            conn = sqlite3.connect(self.database_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 5000")""",
)

replace_once(
    "src/spotify_scheduler_pro/random_queue.py",
    "from collections import deque\nfrom typing import Iterable",
    "from collections import deque\nfrom collections.abc import Iterable",
)
replace_once(
    "src/spotify_scheduler_pro/random_queue.py",
    "    - postpones recently played tracks,",
    "    - excludes recently played tracks,",
)
replace_once(
    "src/spotify_scheduler_pro/random_queue.py",
    """    preferred = [track for uri, track in unique.items() if uri not in recent_uris]
    deferred = [track for uri, track in unique.items() if uri in recent_uris]
    rng.shuffle(preferred)
    rng.shuffle(deferred)

    pool = deque(preferred + deferred)""",
    """    eligible = [track for uri, track in unique.items() if uri not in recent_uris]
    rng.shuffle(eligible)

    pool = deque(eligible)""",
)

replace_once(
    "src/spotify_scheduler_pro/scheduler.py",
    "from .models import ScheduleEntry, ScheduleKind\n\n\nDAY_NAMES_ES",
    "from .models import ScheduleEntry, ScheduleKind\n\nDAY_NAMES_ES",
)
replace_once(
    "src/spotify_scheduler_pro/scheduler.py",
    """    @staticmethod
    def _weekly_segments(entry: ScheduleEntry) -> list[tuple[int, int]]:
        if entry.day_of_week is None:
            return []

        start = entry.day_of_week * 24 * 60 + entry.start_time.hour * 60 + entry.start_time.minute
        end = entry.day_of_week * 24 * 60 + entry.end_time.hour * 60 + entry.end_time.minute

        if not entry.crosses_midnight:
            return [(start, end)]

        week_minutes = 7 * 24 * 60
        end = ((entry.day_of_week + 1) % 7) * 24 * 60 + entry.end_time.hour * 60 + entry.end_time.minute
        if end > start:
            return [(start, end)]
        return [(start, week_minutes), (0, end)]""",
    """    @staticmethod
    def _seconds_of_day(value: time) -> int:
        return value.hour * 3600 + value.minute * 60 + value.second

    @classmethod
    def _weekly_segments(cls, entry: ScheduleEntry) -> list[tuple[int, int]]:
        if entry.day_of_week is None:
            return []

        day_seconds = 24 * 3600
        week_seconds = 7 * day_seconds
        start = entry.day_of_week * day_seconds + cls._seconds_of_day(entry.start_time)
        end = entry.day_of_week * day_seconds + cls._seconds_of_day(entry.end_time)

        if not entry.crosses_midnight:
            return [(start, end)]

        end = ((entry.day_of_week + 1) % 7) * day_seconds + cls._seconds_of_day(
            entry.end_time
        )
        if end > start:
            return [(start, end)]
        return [(start, week_seconds), (0, end)]""",
)
replace_once(
    "src/spotify_scheduler_pro/scheduler.py",
    """                if dated_segment:
                    cursor = dated_segment[0]
                    while cursor < dated_segment[1]:
                        if weekly.matches(cursor):
                            conflicts.append(
                                ScheduleConflict(
                                    candidate,
                                    existing,
                                    "La regla semanal coincide con el horario de fecha específica.",
                                )
                            )
                            break
                        cursor += timedelta(minutes=1)""",
    """                if dated_segment and weekly.day_of_week is not None:
                    cursor_date = dated_segment[0].date() - timedelta(days=1)
                    final_date = dated_segment[1].date()

                    while cursor_date <= final_date:
                        if cursor_date.weekday() == weekly.day_of_week:
                            weekly_start = datetime.combine(cursor_date, weekly.start_time)
                            weekly_end_date = (
                                cursor_date + timedelta(days=1)
                                if weekly.crosses_midnight
                                else cursor_date
                            )
                            weekly_end = datetime.combine(weekly_end_date, weekly.end_time)
                            if self._overlap(
                                dated_segment[0],
                                dated_segment[1],
                                weekly_start,
                                weekly_end,
                            ):
                                conflicts.append(
                                    ScheduleConflict(
                                        candidate,
                                        existing,
                                        "La regla semanal coincide con el horario de fecha específica.",
                                    )
                                )
                                break
                        cursor_date += timedelta(days=1)""",
)

replace_once(
    "src/spotify_scheduler_pro/autostart.py",
    "from pathlib import Path\n\n\nAPP_NAME",
    "from pathlib import Path\n\nAPP_NAME",
)
replace_once(
    "src/spotify_scheduler_pro/autostart.py",
    """    else:
        python = Path(sys.executable)
        command = (
            f'@cd /d "{Path.cwd()}"\\r\\n'
            f'@start "" "{python}" -m spotify_scheduler_pro --minimized\\r\\n'
        )""",
    """    else:
        python = Path(sys.executable)
        pythonw = python.with_name("pythonw.exe")
        if pythonw.exists():
            python = pythonw
        command = f'@start "" "{python}" -m spotify_scheduler_pro --minimized\\r\\n'""",
)

replace_once(
    "src/spotify_scheduler_pro/controller.py",
    "import threading\nimport time\n",
    "import threading\n",
)

replace_once(
    "src/spotify_scheduler_pro/gui/main_window.py",
    """import logging
import queue
import threading
import tkinter as tk""",
    """import logging
import queue
import threading
import tkinter as tk
from collections.abc import Callable""",
)
replace_once(
    "src/spotify_scheduler_pro/gui/main_window.py",
    "from typing import Any, Callable",
    "from typing import Any",
)
replace_once(
    "src/spotify_scheduler_pro/gui/main_window.py",
    """        self._closing = False
        self._ui_queue:""",
    """        self._closing = False
        self._dashboard_refresh_inflight = False
        self._ui_queue:""",
)
replace_once(
    "src/spotify_scheduler_pro/gui/main_window.py",
    """        if self.spotify.connected:
            self.run_async(
                self.spotify.current_playback,
                on_success=self._apply_current_playback,
                on_error=lambda _exc: None,
                description="estado actual",
                show_busy=False,
            )""",
    """        if self.spotify.connected and not self._dashboard_refresh_inflight:
            self._dashboard_refresh_inflight = True

            def apply_playback(playback: dict[str, Any] | None) -> None:
                self._dashboard_refresh_inflight = False
                self._apply_current_playback(playback)

            def ignore_playback_error(_error: Exception) -> None:
                self._dashboard_refresh_inflight = False

            self.run_async(
                self.spotify.current_playback,
                on_success=apply_playback,
                on_error=ignore_playback_error,
                description="estado actual",
                show_busy=False,
            )""",
)

replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """from pathlib import Path
from typing import Any, Iterable

import requests
import spotipy
from PIL import Image
from spotipy.oauth2 import SpotifyOAuth""",
    """from pathlib import Path
from typing import Any

import keyring
import requests
import spotipy
from keyring.errors import KeyringError
from PIL import Image
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyOAuth""",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    '        "playlist-modify-public",\n',
    "",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """class SpotifyPremiumRequiredError(RuntimeError):
    pass


class SpotifyService:""",
    """class SpotifyPremiumRequiredError(RuntimeError):
    pass


class KeyringTokenCache(CacheHandler):
    SERVICE_NAME = "SpotifySchedulerProOAuth"

    def __init__(self, client_id: str):
        self.username = f"token:{client_id}"

    def get_cached_token(self) -> dict[str, Any] | None:
        try:
            raw = keyring.get_password(self.SERVICE_NAME, self.username)
        except KeyringError:
            return None

        if not raw:
            return None
        try:
            token = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return token if isinstance(token, dict) else None

    def save_token_to_cache(self, token_info: dict[str, Any]) -> None:
        try:
            keyring.set_password(
                self.SERVICE_NAME,
                self.username,
                json.dumps(token_info),
            )
        except KeyringError as exc:
            raise RuntimeError(
                "No fue posible guardar el token OAuth en el almacén seguro."
            ) from exc

    def clear(self) -> None:
        try:
            keyring.delete_password(self.SERVICE_NAME, self.username)
        except KeyringError:
            pass


class SpotifyService:""",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """        self._lock = threading.RLock()
        self._profile: dict[str, Any] | None = None""",
    """        self._lock = threading.RLock()
        self._profile: dict[str, Any] | None = None
        self._token_cache: KeyringTokenCache | None = None""",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """    @property
    def connected(self) -> bool:
        return self._client is not None""",
    """    @property
    def connected(self) -> bool:
        with self._lock:
            return self._client is not None""",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """        with self._lock:
            auth_manager = SpotifyOAuth(
                client_id=config.client_id.strip(),
                client_secret=client_secret.strip(),
                redirect_uri=config.redirect_uri.strip(),
                scope=SPOTIFY_SCOPES,
                cache_path=str(self.paths.oauth_cache),
                open_browser=True,
                show_dialog=force_dialog,
                requests_timeout=10,
            )
            self._client = spotipy.Spotify(
                auth_manager=auth_manager,
                requests_timeout=10,
                retries=2,
                status_retries=2,
                backoff_factor=0.5,
            )
            self._profile = self._client.current_user()

        if str(self._profile.get("product", "")).lower() != "premium":
            self._client = None
            raise SpotifyPremiumRequiredError(
                "Spotify Premium es necesario para controlar la reproducción."
            )

        LOGGER.info(
            "Spotify conectado como %s (%s)",
            self._profile.get("display_name") or self._profile.get("id"),
            self._profile.get("id"),
        )
        return dict(self._profile)""",
    """        token_cache = KeyringTokenCache(config.client_id.strip())
        if force_dialog:
            token_cache.clear()

        auth_manager = SpotifyOAuth(
            client_id=config.client_id.strip(),
            client_secret=client_secret.strip(),
            redirect_uri=config.redirect_uri.strip(),
            scope=SPOTIFY_SCOPES,
            cache_handler=token_cache,
            open_browser=True,
            show_dialog=force_dialog,
            requests_timeout=10,
        )
        client = spotipy.Spotify(
            auth_manager=auth_manager,
            requests_timeout=10,
            retries=2,
            status_retries=2,
            backoff_factor=0.5,
        )
        profile = client.current_user()

        if str(profile.get("product", "")).lower() != "premium":
            raise SpotifyPremiumRequiredError(
                "Spotify Premium es necesario para controlar la reproducción."
            )

        with self._lock:
            self._client = client
            self._profile = profile
            self._token_cache = token_cache

        LOGGER.info(
            "Spotify conectado como %s (%s)",
            profile.get("display_name") or profile.get("id"),
            profile.get("id"),
        )
        return dict(profile)""",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """    def disconnect(self, *, delete_cache: bool = False) -> None:
        with self._lock:
            self._client = None
            self._profile = None
            if delete_cache:
                try:
                    self.paths.oauth_cache.unlink(missing_ok=True)
                except OSError:
                    LOGGER.exception("No se pudo eliminar la caché OAuth.")

    def current_profile(self) -> dict[str, Any]:
        if self._profile is None:
            self._profile = self.client.current_user()
        return dict(self._profile)""",
    """    def disconnect(self, *, delete_cache: bool = False) -> None:
        with self._lock:
            token_cache = self._token_cache
            self._client = None
            self._profile = None
            self._token_cache = None

        if delete_cache:
            if token_cache is not None:
                token_cache.clear()
            try:
                self.paths.oauth_cache.unlink(missing_ok=True)
            except OSError:
                LOGGER.exception("No se pudo eliminar la caché OAuth heredada.")

    def current_profile(self) -> dict[str, Any]:
        with self._lock:
            if self._profile is None:
                self._profile = self._api_call("current_user")
            return dict(self._profile)

    def _api_call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            method = getattr(self.client, method_name)
            return method(*args, **kwargs)""",
)

spotify_path = "src/spotify_scheduler_pro/spotify_client.py"
spotify_text = read(spotify_path)
spotify_text = re.sub(
    r"self\.client\.([A-Za-z_][A-Za-z0-9_]*)\(",
    lambda match: f'self._api_call("{match.group(1)}", ',
    spotify_text,
)
spotify_text = "\n".join(line.rstrip() for line in spotify_text.splitlines()) + "\n"
spotify_text = re.sub(
    r'self\._api_call\("([A-Za-z_][A-Za-z0-9_]*)",\s*\)',
    lambda match: f'self._api_call("{match.group(1)}")',
    spotify_text,
)
write(spotify_path, spotify_text)

replace_once(
    "tests/test_random_queue.py",
    """    assert len(uris) == 3
    assert "spotify:local:bad" not in uris
    assert len(set(uris)) == len(uris)""",
    """    assert len(uris) == 2
    assert "spotify:local:bad" not in uris
    assert "spotify:track:3" not in uris
    assert len(set(uris)) == len(uris)""",
)

with (ROOT / "tests" / "test_scheduler.py").open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(
        """

def test_detects_weekly_overlap_with_seconds() -> None:
    first = ScheduleEntry(
        id=1,
        name="Segundos A",
        day_of_week=0,
        start_time=time(8, 0, 10),
        end_time=time(8, 0, 20),
        playlist_id="a",
    )
    second = ScheduleEntry(
        name="Segundos B",
        day_of_week=0,
        start_time=time(8, 0, 15),
        end_time=time(8, 0, 25),
        playlist_id="b",
    )
    assert len(SchedulerEngine([first]).conflicts_for(second)) == 1


def test_detects_mixed_overlap_with_seconds() -> None:
    weekly = ScheduleEntry(
        id=1,
        name="Semanal",
        day_of_week=0,
        start_time=time(8, 0, 10),
        end_time=time(8, 0, 20),
        playlist_id="a",
    )
    dated = ScheduleEntry(
        name="Fecha",
        kind=ScheduleKind.DATE,
        specific_date=date(2026, 7, 13),
        day_of_week=None,
        start_time=time(8, 0, 15),
        end_time=time(8, 0, 25),
        playlist_id="b",
    )
    assert len(SchedulerEngine([weekly]).conflicts_for(dated)) == 1


def test_rejects_equal_start_and_end() -> None:
    entry = ScheduleEntry(
        name="Inválido",
        day_of_week=0,
        start_time=time(8, 0),
        end_time=time(8, 0),
        playlist_id="a",
    )
    assert "La hora inicial y final no pueden ser iguales." in entry.validate()
"""
    )

with (ROOT / "tests" / "test_storage.py").open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(
        """

def test_foreign_key_is_enabled_for_every_connection(tmp_path) -> None:
    from spotify_scheduler_pro.models import PlaybackEvent

    storage = Storage(tmp_path / "scheduler.db")
    entry = storage.save_schedule(
        ScheduleEntry(
            name="Con FK",
            day_of_week=1,
            start_time=time(10, 0),
            end_time=time(11, 0),
            playlist_id="playlist-fk",
        )
    )
    storage.add_event(PlaybackEvent(event_type="play", schedule_id=entry.id))
    storage.delete_schedule(entry.id)

    [event] = storage.list_events()
    assert event.schedule_id is None
"""
    )

write(
    "tests/test_config.py",
    """import json

from spotify_scheduler_pro.config import AppConfig, ConfigManager


def test_non_object_config_falls_back_to_defaults(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps([]), encoding="utf-8")

    assert ConfigManager(path).load() == AppConfig()
""",
)

write(
    "tests/test_spotify_client.py",
    """from types import SimpleNamespace

import pytest

from spotify_scheduler_pro.config import AppConfig
from spotify_scheduler_pro.spotify_client import SpotifyService


def test_failed_connection_does_not_publish_client(monkeypatch) -> None:
    class FailingClient:
        def current_user(self):
            raise RuntimeError("oauth failed")

    manager = SimpleNamespace(get_client_secret=lambda: "secret")
    paths = SimpleNamespace(oauth_cache=SimpleNamespace(unlink=lambda **_kwargs: None))
    storage = SimpleNamespace()

    monkeypatch.setattr(
        "spotify_scheduler_pro.spotify_client.SpotifyOAuth",
        lambda **_kwargs: object(),
    )
    monkeypatch.setattr(
        "spotify_scheduler_pro.spotify_client.spotipy.Spotify",
        lambda **_kwargs: FailingClient(),
    )

    service = SpotifyService(manager, paths, storage)
    with pytest.raises(RuntimeError, match="oauth failed"):
        service.connect(AppConfig(client_id="client"))

    assert not service.connected
""",
)

readme = read("README.md")
marker = "## Qué incorpora\n"
notice = """## Uso permitido y limitaciones

Esta aplicación es exclusivamente para uso personal y no comercial. Spotify no
permite reproducir su servicio públicamente en restaurantes, colegios, bares,
tiendas u otros negocios, incluso con una cuenta Premium. Consulta la política
de uso público/comercial de Spotify y su Developer Policy.

Este proyecto no está afiliado, patrocinado ni aprobado por Spotify.

"""
if readme.count(marker) != 1:
    raise RuntimeError("README.md: no se encontró el punto de inserción")
readme = readme.replace(marker, notice + marker, 1)
bt = chr(96)
readme = readme.replace("- " + bt + "spotify_cache.json" + bt + "\n", "")
readme += """

## Automatización en GitHub

Los workflows incluidos ejecutan Ruff y pytest en GitHub Actions y permiten
construir el ejecutable Windows manualmente desde la pestaña Actions, sin
instalar dependencias en el equipo usado para administrar el repositorio.

Los tokens OAuth y el Client Secret se guardan con keyring. Al cerrar sesión se
elimina también cualquier caché OAuth heredada.
"""
write("README.md", readme)

write(
    "PRIVACY.md",
    """# Privacidad

Spotify Scheduler Pro es una aplicación de escritorio para uso personal y no
comercial. No mantiene un servidor propio ni envía telemetría.

La configuración no sensible, los horarios, el historial de automatización y
los logs se guardan localmente en la carpeta de datos de la aplicación. El
Client Secret y los tokens OAuth se almacenan mediante keyring en el almacén de
credenciales del sistema.

Cerrar la sesión OAuth elimina los tokens y cualquier caché heredada. Para
eliminar todos los datos, cierra la aplicación y borra su carpeta local de
datos. Las solicitudes musicales se envían directamente a la API de Spotify
según los permisos autorizados por el usuario.
""",
)

write(
    ".github/workflows/ci.yml",
    """name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install --upgrade pip
      - run: python -m pip install -e ".[dev]"
      - run: python -m ruff check .
      - run: python -m pytest -q
""",
)

write(
    ".github/workflows/build-windows.yml",
    """name: Build Windows EXE

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Build executable
        shell: pwsh
        run: .\\build_exe.ps1
      - uses: actions/upload-artifact@v4
        with:
          name: SpotifySchedulerPro-Windows
          path: dist/SpotifySchedulerPro
          if-no-files-found: error
""",
)

write(
    ".github/dependabot.yml",
    """version: 2
updates:
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
""",
)

changelog = read("CHANGELOG.md")
changelog += """

## Correcciones previas a publicación

- Exclusión real de canciones recientes en Random Queue.
- Detección de conflictos con precisión de segundos.
- Claves foráneas SQLite habilitadas en cada conexión.
- Estado OAuth atómico, tokens en keyring y llamadas API serializadas.
- Refrescos del dashboard sin solapamiento.
- CI y compilación Windows mediante GitHub Actions.
"""
write("CHANGELOG.md", changelog)

for generated_workflow in (
    ROOT / ".github" / "workflows" / "ci.yml",
    ROOT / ".github" / "workflows" / "build-windows.yml",
):
    generated_workflow.unlink(missing_ok=True)

subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
subprocess.run(
    ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
    check=True,
)
subprocess.run(
    ["git", "commit", "-m", "add modular Spotify Scheduler Pro rewrite"],
    check=True,
)
subprocess.run(["git", "push", "origin", "HEAD:agent/spotify-scheduler-pro"], check=True)
from __future__ import annotations

import base64
import io
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path.cwd()
PAYLOAD = ROOT / ".github" / "bootstrap" / "spotify-scheduler-pro.zip.b64"
PREFIX = "spotify-scheduler-pro/"

payload_bytes = base64.b64decode(PAYLOAD.read_text(encoding="utf-8").strip(), validate=True)
code_of_conduct = (ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")

subprocess.run(["git", "rm", "-rf", "--", "."], check=True)

with zipfile.ZipFile(io.BytesIO(payload_bytes)) as archive:
    bad_member = archive.testzip()
    if bad_member is not None:
        raise RuntimeError(f"ZIP corrupto: {bad_member}")

    for info in archive.infolist():
        if info.is_dir() or not info.filename.startswith(PREFIX):
            continue
        relative = info.filename[len(PREFIX):]
        if not relative or relative == "CODIGO_COMPLETO.txt":
            continue
        target = (ROOT / relative).resolve()
        if ROOT.resolve() not in target.parents:
            raise RuntimeError(f"Ruta insegura en ZIP: {info.filename}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(info.filename))

(ROOT / "CODE_OF_CONDUCT.md").write_text(code_of_conduct, encoding="utf-8")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: se esperaba una coincidencia y se encontraron {count}")
    write(path, text.replace(old, new, 1))


replace_once(
    "pyproject.toml",
    """authors = [
  {name = "Szymon Andrzejewski", email = "upstream-author@example.invalid"},
  {name = "Modified educational edition"}
]""",
    """authors = [
  {name = "Szymon Andrzejewski"},
  {name = "Spotify Scheduler Pro contributors"}
]""",
)

for script in ("run_windows.ps1", "build_exe.ps1"):
    replace_once(
        script,
        '$ErrorActionPreference = "Stop"\n\n',
        '$ErrorActionPreference = "Stop"\nSet-Location -LiteralPath $PSScriptRoot\n\n',
    )

replace_once(
    "src/spotify_scheduler_pro/config.py",
    """        try:
            raw: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}

        defaults = asdict(AppConfig())""",
    """        try:
            loaded: Any = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}

        raw: dict[str, Any] = loaded if isinstance(loaded, dict) else {}
        defaults = asdict(AppConfig())""",
)

replace_once(
    "src/spotify_scheduler_pro/models.py",
    "        return self.end_time <= self.start_time",
    "        return self.end_time < self.start_time",
)
replace_once(
    "src/spotify_scheduler_pro/models.py",
    """        if not self.playlist_id.strip():
            errors.append("Debes ingresar una playlist.")
        if self.kind == ScheduleKind.WEEKLY""",
    """        if not self.playlist_id.strip():
            errors.append("Debes ingresar una playlist.")
        if self.start_time == self.end_time:
            errors.append("La hora inicial y final no pueden ser iguales.")
        if self.kind == ScheduleKind.WEEKLY""",
)
replace_once(
    "src/spotify_scheduler_pro/models.py",
    '    def copy_with(self, **changes: Any) -> "ScheduleEntry":',
    "    def copy_with(self, **changes: Any) -> ScheduleEntry:",
)
replace_once(
    "src/spotify_scheduler_pro/paths.py",
    '    def create(cls) -> "AppPaths":',
    "    def create(cls) -> AppPaths:",
)

replace_once(
    "src/spotify_scheduler_pro/storage.py",
    "from typing import Iterator",
    "from collections.abc import Iterator",
)
replace_once(
    "src/spotify_scheduler_pro/storage.py",
    """            conn = sqlite3.connect(self.database_path)
            conn.row_factory = sqlite3.Row""",
    """            conn = sqlite3.connect(self.database_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 5000")""",
)

replace_once(
    "src/spotify_scheduler_pro/random_queue.py",
    "from collections import deque\nfrom typing import Iterable",
    "from collections import deque\nfrom collections.abc import Iterable",
)
replace_once(
    "src/spotify_scheduler_pro/random_queue.py",
    "    - postpones recently played tracks,",
    "    - excludes recently played tracks,",
)
replace_once(
    "src/spotify_scheduler_pro/random_queue.py",
    """    preferred = [track for uri, track in unique.items() if uri not in recent_uris]
    deferred = [track for uri, track in unique.items() if uri in recent_uris]
    rng.shuffle(preferred)
    rng.shuffle(deferred)

    pool = deque(preferred + deferred)""",
    """    eligible = [track for uri, track in unique.items() if uri not in recent_uris]
    rng.shuffle(eligible)

    pool = deque(eligible)""",
)

replace_once(
    "src/spotify_scheduler_pro/scheduler.py",
    "from .models import ScheduleEntry, ScheduleKind\n\n\nDAY_NAMES_ES",
    "from .models import ScheduleEntry, ScheduleKind\n\nDAY_NAMES_ES",
)
replace_once(
    "src/spotify_scheduler_pro/scheduler.py",
    """    @staticmethod
    def _weekly_segments(entry: ScheduleEntry) -> list[tuple[int, int]]:
        if entry.day_of_week is None:
            return []

        start = entry.day_of_week * 24 * 60 + entry.start_time.hour * 60 + entry.start_time.minute
        end = entry.day_of_week * 24 * 60 + entry.end_time.hour * 60 + entry.end_time.minute

        if not entry.crosses_midnight:
            return [(start, end)]

        week_minutes = 7 * 24 * 60
        end = ((entry.day_of_week + 1) % 7) * 24 * 60 + entry.end_time.hour * 60 + entry.end_time.minute
        if end > start:
            return [(start, end)]
        return [(start, week_minutes), (0, end)]""",
    """    @staticmethod
    def _seconds_of_day(value: time) -> int:
        return value.hour * 3600 + value.minute * 60 + value.second

    @classmethod
    def _weekly_segments(cls, entry: ScheduleEntry) -> list[tuple[int, int]]:
        if entry.day_of_week is None:
            return []

        day_seconds = 24 * 3600
        week_seconds = 7 * day_seconds
        start = entry.day_of_week * day_seconds + cls._seconds_of_day(entry.start_time)
        end = entry.day_of_week * day_seconds + cls._seconds_of_day(entry.end_time)

        if not entry.crosses_midnight:
            return [(start, end)]

        end = ((entry.day_of_week + 1) % 7) * day_seconds + cls._seconds_of_day(
            entry.end_time
        )
        if end > start:
            return [(start, end)]
        return [(start, week_seconds), (0, end)]""",
)
replace_once(
    "src/spotify_scheduler_pro/scheduler.py",
    """                if dated_segment:
                    cursor = dated_segment[0]
                    while cursor < dated_segment[1]:
                        if weekly.matches(cursor):
                            conflicts.append(
                                ScheduleConflict(
                                    candidate,
                                    existing,
                                    "La regla semanal coincide con el horario de fecha específica.",
                                )
                            )
                            break
                        cursor += timedelta(minutes=1)""",
    """                if dated_segment and weekly.day_of_week is not None:
                    cursor_date = dated_segment[0].date() - timedelta(days=1)
                    final_date = dated_segment[1].date()

                    while cursor_date <= final_date:
                        if cursor_date.weekday() == weekly.day_of_week:
                            weekly_start = datetime.combine(cursor_date, weekly.start_time)
                            weekly_end_date = (
                                cursor_date + timedelta(days=1)
                                if weekly.crosses_midnight
                                else cursor_date
                            )
                            weekly_end = datetime.combine(weekly_end_date, weekly.end_time)
                            if self._overlap(
                                dated_segment[0],
                                dated_segment[1],
                                weekly_start,
                                weekly_end,
                            ):
                                conflicts.append(
                                    ScheduleConflict(
                                        candidate,
                                        existing,
                                        "La regla semanal coincide con el horario de fecha específica.",
                                    )
                                )
                                break
                        cursor_date += timedelta(days=1)""",
)

replace_once(
    "src/spotify_scheduler_pro/autostart.py",
    "from pathlib import Path\n\n\nAPP_NAME",
    "from pathlib import Path\n\nAPP_NAME",
)
replace_once(
    "src/spotify_scheduler_pro/autostart.py",
    """    else:
        python = Path(sys.executable)
        command = (
            f'@cd /d "{Path.cwd()}"\\r\\n'
            f'@start "" "{python}" -m spotify_scheduler_pro --minimized\\r\\n'
        )""",
    """    else:
        python = Path(sys.executable)
        pythonw = python.with_name("pythonw.exe")
        if pythonw.exists():
            python = pythonw
        command = f'@start "" "{python}" -m spotify_scheduler_pro --minimized\\r\\n'""",
)

replace_once(
    "src/spotify_scheduler_pro/controller.py",
    "import threading\nimport time\n",
    "import threading\n",
)

replace_once(
    "src/spotify_scheduler_pro/gui/main_window.py",
    """import logging
import queue
import threading
import tkinter as tk""",
    """import logging
import queue
import threading
import tkinter as tk
from collections.abc import Callable""",
)
replace_once(
    "src/spotify_scheduler_pro/gui/main_window.py",
    "from typing import Any, Callable",
    "from typing import Any",
)
replace_once(
    "src/spotify_scheduler_pro/gui/main_window.py",
    """        self._closing = False
        self._ui_queue:""",
    """        self._closing = False
        self._dashboard_refresh_inflight = False
        self._ui_queue:""",
)
replace_once(
    "src/spotify_scheduler_pro/gui/main_window.py",
    """        if self.spotify.connected:
            self.run_async(
                self.spotify.current_playback,
                on_success=self._apply_current_playback,
                on_error=lambda _exc: None,
                description="estado actual",
                show_busy=False,
            )""",
    """        if self.spotify.connected and not self._dashboard_refresh_inflight:
            self._dashboard_refresh_inflight = True

            def apply_playback(playback: dict[str, Any] | None) -> None:
                self._dashboard_refresh_inflight = False
                self._apply_current_playback(playback)

            def ignore_playback_error(_error: Exception) -> None:
                self._dashboard_refresh_inflight = False

            self.run_async(
                self.spotify.current_playback,
                on_success=apply_playback,
                on_error=ignore_playback_error,
                description="estado actual",
                show_busy=False,
            )""",
)

replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """from pathlib import Path
from typing import Any, Iterable

import requests
import spotipy
from PIL import Image
from spotipy.oauth2 import SpotifyOAuth""",
    """from pathlib import Path
from typing import Any

import keyring
import requests
import spotipy
from keyring.errors import KeyringError
from PIL import Image
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyOAuth""",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    '        "playlist-modify-public",\n',
    "",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """class SpotifyPremiumRequiredError(RuntimeError):
    pass


class SpotifyService:""",
    """class SpotifyPremiumRequiredError(RuntimeError):
    pass


class KeyringTokenCache(CacheHandler):
    SERVICE_NAME = "SpotifySchedulerProOAuth"

    def __init__(self, client_id: str):
        self.username = f"token:{client_id}"

    def get_cached_token(self) -> dict[str, Any] | None:
        try:
            raw = keyring.get_password(self.SERVICE_NAME, self.username)
        except KeyringError:
            return None

        if not raw:
            return None
        try:
            token = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return token if isinstance(token, dict) else None

    def save_token_to_cache(self, token_info: dict[str, Any]) -> None:
        try:
            keyring.set_password(
                self.SERVICE_NAME,
                self.username,
                json.dumps(token_info),
            )
        except KeyringError as exc:
            raise RuntimeError(
                "No fue posible guardar el token OAuth en el almacén seguro."
            ) from exc

    def clear(self) -> None:
        try:
            keyring.delete_password(self.SERVICE_NAME, self.username)
        except KeyringError:
            pass


class SpotifyService:""",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """        self._lock = threading.RLock()
        self._profile: dict[str, Any] | None = None""",
    """        self._lock = threading.RLock()
        self._profile: dict[str, Any] | None = None
        self._token_cache: KeyringTokenCache | None = None""",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """    @property
    def connected(self) -> bool:
        return self._client is not None""",
    """    @property
    def connected(self) -> bool:
        with self._lock:
            return self._client is not None""",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """        with self._lock:
            auth_manager = SpotifyOAuth(
                client_id=config.client_id.strip(),
                client_secret=client_secret.strip(),
                redirect_uri=config.redirect_uri.strip(),
                scope=SPOTIFY_SCOPES,
                cache_path=str(self.paths.oauth_cache),
                open_browser=True,
                show_dialog=force_dialog,
                requests_timeout=10,
            )
            self._client = spotipy.Spotify(
                auth_manager=auth_manager,
                requests_timeout=10,
                retries=2,
                status_retries=2,
                backoff_factor=0.5,
            )
            self._profile = self._client.current_user()

        if str(self._profile.get("product", "")).lower() != "premium":
            self._client = None
            raise SpotifyPremiumRequiredError(
                "Spotify Premium es necesario para controlar la reproducción."
            )

        LOGGER.info(
            "Spotify conectado como %s (%s)",
            self._profile.get("display_name") or self._profile.get("id"),
            self._profile.get("id"),
        )
        return dict(self._profile)""",
    """        token_cache = KeyringTokenCache(config.client_id.strip())
        if force_dialog:
            token_cache.clear()

        auth_manager = SpotifyOAuth(
            client_id=config.client_id.strip(),
            client_secret=client_secret.strip(),
            redirect_uri=config.redirect_uri.strip(),
            scope=SPOTIFY_SCOPES,
            cache_handler=token_cache,
            open_browser=True,
            show_dialog=force_dialog,
            requests_timeout=10,
        )
        client = spotipy.Spotify(
            auth_manager=auth_manager,
            requests_timeout=10,
            retries=2,
            status_retries=2,
            backoff_factor=0.5,
        )
        profile = client.current_user()

        if str(profile.get("product", "")).lower() != "premium":
            raise SpotifyPremiumRequiredError(
                "Spotify Premium es necesario para controlar la reproducción."
            )

        with self._lock:
            self._client = client
            self._profile = profile
            self._token_cache = token_cache

        LOGGER.info(
            "Spotify conectado como %s (%s)",
            profile.get("display_name") or profile.get("id"),
            profile.get("id"),
        )
        return dict(profile)""",
)
replace_once(
    "src/spotify_scheduler_pro/spotify_client.py",
    """    def disconnect(self, *, delete_cache: bool = False) -> None:
        with self._lock:
            self._client = None
            self._profile = None
            if delete_cache:
                try:
                    self.paths.oauth_cache.unlink(missing_ok=True)
                except OSError:
                    LOGGER.exception("No se pudo eliminar la caché OAuth.")

    def current_profile(self) -> dict[str, Any]:
        if self._profile is None:
            self._profile = self.client.current_user()
        return dict(self._profile)""",
    """    def disconnect(self, *, delete_cache: bool = False) -> None:
        with self._lock:
            token_cache = self._token_cache
            self._client = None
            self._profile = None
            self._token_cache = None

        if delete_cache:
            if token_cache is not None:
                token_cache.clear()
            try:
                self.paths.oauth_cache.unlink(missing_ok=True)
            except OSError:
                LOGGER.exception("No se pudo eliminar la caché OAuth heredada.")

    def current_profile(self) -> dict[str, Any]:
        with self._lock:
            if self._profile is None:
                self._profile = self._api_call("current_user")
            return dict(self._profile)

    def _api_call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            method = getattr(self.client, method_name)
            return method(*args, **kwargs)""",
)

spotify_path = "src/spotify_scheduler_pro/spotify_client.py"
spotify_text = read(spotify_path)
spotify_text = re.sub(
    r"self\.client\.([A-Za-z_][A-Za-z0-9_]*)\(",
    lambda match: f'self._api_call("{match.group(1)}", ',
    spotify_text,
)
spotify_text = "\n".join(line.rstrip() for line in spotify_text.splitlines()) + "\n"
spotify_text = re.sub(
    r'self\._api_call\("([A-Za-z_][A-Za-z0-9_]*)",\s*\)',
    lambda match: f'self._api_call("{match.group(1)}")',
    spotify_text,
)
write(spotify_path, spotify_text)

replace_once(
    "tests/test_random_queue.py",
    """    assert len(uris) == 3
    assert "spotify:local:bad" not in uris
    assert len(set(uris)) == len(uris)""",
    """    assert len(uris) == 2
    assert "spotify:local:bad" not in uris
    assert "spotify:track:3" not in uris
    assert len(set(uris)) == len(uris)""",
)

with (ROOT / "tests" / "test_scheduler.py").open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(
        """

def test_detects_weekly_overlap_with_seconds() -> None:
    first = ScheduleEntry(
        id=1,
        name="Segundos A",
        day_of_week=0,
        start_time=time(8, 0, 10),
        end_time=time(8, 0, 20),
        playlist_id="a",
    )
    second = ScheduleEntry(
        name="Segundos B",
        day_of_week=0,
        start_time=time(8, 0, 15),
        end_time=time(8, 0, 25),
        playlist_id="b",
    )
    assert len(SchedulerEngine([first]).conflicts_for(second)) == 1


def test_detects_mixed_overlap_with_seconds() -> None:
    weekly = ScheduleEntry(
        id=1,
        name="Semanal",
        day_of_week=0,
        start_time=time(8, 0, 10),
        end_time=time(8, 0, 20),
        playlist_id="a",
    )
    dated = ScheduleEntry(
        name="Fecha",
        kind=ScheduleKind.DATE,
        specific_date=date(2026, 7, 13),
        day_of_week=None,
        start_time=time(8, 0, 15),
        end_time=time(8, 0, 25),
        playlist_id="b",
    )
    assert len(SchedulerEngine([weekly]).conflicts_for(dated)) == 1


def test_rejects_equal_start_and_end() -> None:
    entry = ScheduleEntry(
        name="Inválido",
        day_of_week=0,
        start_time=time(8, 0),
        end_time=time(8, 0),
        playlist_id="a",
    )
    assert "La hora inicial y final no pueden ser iguales." in entry.validate()
"""
    )

with (ROOT / "tests" / "test_storage.py").open("a", encoding="utf-8", newline="\n") as handle:
    handle.write(
        """

def test_foreign_key_is_enabled_for_every_connection(tmp_path) -> None:
    from spotify_scheduler_pro.models import PlaybackEvent

    storage = Storage(tmp_path / "scheduler.db")
    entry = storage.save_schedule(
        ScheduleEntry(
            name="Con FK",
            day_of_week=1,
            start_time=time(10, 0),
            end_time=time(11, 0),
            playlist_id="playlist-fk",
        )
    )
    storage.add_event(PlaybackEvent(event_type="play", schedule_id=entry.id))
    storage.delete_schedule(entry.id)

    [event] = storage.list_events()
    assert event.schedule_id is None
"""
    )

write(
    "tests/test_config.py",
    """import json

from spotify_scheduler_pro.config import AppConfig, ConfigManager


def test_non_object_config_falls_back_to_defaults(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps([]), encoding="utf-8")

    assert ConfigManager(path).load() == AppConfig()
""",
)

write(
    "tests/test_spotify_client.py",
    """from types import SimpleNamespace

import pytest

from spotify_scheduler_pro.config import AppConfig
from spotify_scheduler_pro.spotify_client import SpotifyService


def test_failed_connection_does_not_publish_client(monkeypatch) -> None:
    class FailingClient:
        def current_user(self):
            raise RuntimeError("oauth failed")

    manager = SimpleNamespace(get_client_secret=lambda: "secret")
    paths = SimpleNamespace(oauth_cache=SimpleNamespace(unlink=lambda **_kwargs: None))
    storage = SimpleNamespace()

    monkeypatch.setattr(
        "spotify_scheduler_pro.spotify_client.SpotifyOAuth",
        lambda **_kwargs: object(),
    )
    monkeypatch.setattr(
        "spotify_scheduler_pro.spotify_client.spotipy.Spotify",
        lambda **_kwargs: FailingClient(),
    )

    service = SpotifyService(manager, paths, storage)
    with pytest.raises(RuntimeError, match="oauth failed"):
        service.connect(AppConfig(client_id="client"))

    assert not service.connected
""",
)

readme = read("README.md")
marker = "## Qué incorpora\n"
notice = """## Uso permitido y limitaciones

Esta aplicación es exclusivamente para uso personal y no comercial. Spotify no
permite reproducir su servicio públicamente en restaurantes, colegios, bares,
tiendas u otros negocios, incluso con una cuenta Premium. Consulta la política
de uso público/comercial de Spotify y su Developer Policy.

Este proyecto no está afiliado, patrocinado ni aprobado por Spotify.

"""
if readme.count(marker) != 1:
    raise RuntimeError("README.md: no se encontró el punto de inserción")
readme = readme.replace(marker, notice + marker, 1)
bt = chr(96)
readme = readme.replace("- " + bt + "spotify_cache.json" + bt + "\n", "")
readme += """

## Automatización en GitHub

Los workflows incluidos ejecutan Ruff y pytest en GitHub Actions y permiten
construir el ejecutable Windows manualmente desde la pestaña Actions, sin
instalar dependencias en el equipo usado para administrar el repositorio.

Los tokens OAuth y el Client Secret se guardan con keyring. Al cerrar sesión se
elimina también cualquier caché OAuth heredada.
"""
write("README.md", readme)

write(
    "PRIVACY.md",
    """# Privacidad

Spotify Scheduler Pro es una aplicación de escritorio para uso personal y no
comercial. No mantiene un servidor propio ni envía telemetría.

La configuración no sensible, los horarios, el historial de automatización y
los logs se guardan localmente en la carpeta de datos de la aplicación. El
Client Secret y los tokens OAuth se almacenan mediante keyring en el almacén de
credenciales del sistema.

Cerrar la sesión OAuth elimina los tokens y cualquier caché heredada. Para
eliminar todos los datos, cierra la aplicación y borra su carpeta local de
datos. Las solicitudes musicales se envían directamente a la API de Spotify
según los permisos autorizados por el usuario.
""",
)

write(
    ".github/workflows/ci.yml",
    """name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install --upgrade pip
      - run: python -m pip install -e ".[dev]"
      - run: python -m ruff check .
      - run: python -m pytest -q
""",
)

write(
    ".github/workflows/build-windows.yml",
    """name: Build Windows EXE

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Build executable
        shell: pwsh
        run: .\\build_exe.ps1
      - uses: actions/upload-artifact@v4
        with:
          name: SpotifySchedulerPro-Windows
          path: dist/SpotifySchedulerPro
          if-no-files-found: error
""",
)

write(
    ".github/dependabot.yml",
    """version: 2
updates:
  - package-ecosystem: pip
    directory: /
    schedule:
      interval: weekly
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
""",
)

changelog = read("CHANGELOG.md")
changelog += """

## Correcciones previas a publicación

- Exclusión real de canciones recientes en Random Queue.
- Detección de conflictos con precisión de segundos.
- Claves foráneas SQLite habilitadas en cada conexión.
- Estado OAuth atómico, tokens en keyring y llamadas API serializadas.
- Refrescos del dashboard sin solapamiento.
- CI y compilación Windows mediante GitHub Actions.
"""
write("CHANGELOG.md", changelog)

subprocess.run(["git", "add", "-A"], check=True)
subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
subprocess.run(
    ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
    check=True,
)
subprocess.run(
    ["git", "commit", "-m", "add modular Spotify Scheduler Pro rewrite"],
    check=True,
)
subprocess.run(["git", "push", "origin", "HEAD:agent/spotify-scheduler-pro"], check=True)
