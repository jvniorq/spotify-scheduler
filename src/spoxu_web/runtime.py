from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import spotipy
from cryptography.fernet import Fernet, InvalidToken
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyOAuth

from spotify_scheduler_pro.config import AppConfig
from spotify_scheduler_pro.controller import AutomationController
from spotify_scheduler_pro.models import SpotifyDevice, SpotifyPlaylist
from spotify_scheduler_pro.random_queue import build_random_queue
from spotify_scheduler_pro.storage import Storage

from .config import WebSettings

LOGGER = logging.getLogger("spoxu_web")

SPOTIFY_SCOPES = " ".join(
    [
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        "user-read-recently-played",
        "user-read-private",
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-private",
    ]
)


class EncryptedFileCache(CacheHandler):
    def __init__(self, path: Path, encryption_key: str):
        self.path = path
        self.fernet = Fernet(encryption_key.encode("ascii"))
        self._lock = threading.RLock()

    def get_cached_token(self) -> dict[str, Any] | None:
        with self._lock:
            if not self.path.exists():
                return None
            try:
                decrypted = self.fernet.decrypt(self.path.read_bytes())
                payload = json.loads(decrypted.decode("utf-8"))
            except (OSError, InvalidToken, UnicodeDecodeError, json.JSONDecodeError):
                LOGGER.exception("No se pudo leer el token cifrado de Spotify.")
                return None
            return payload if isinstance(payload, dict) else None

    def save_token_to_cache(self, token_info: dict[str, Any]) -> None:
        encoded = json.dumps(token_info, separators=(",", ":")).encode("utf-8")
        encrypted = self.fernet.encrypt(encoded)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with self._lock:
            temporary.write_bytes(encrypted)
            temporary.replace(self.path)

    def clear(self) -> None:
        with self._lock:
            self.path.unlink(missing_ok=True)


class ServerSpotifyService:
    def __init__(self, settings: WebSettings, storage: Storage):
        self.settings = settings
        self.storage = storage
        self.cache = EncryptedFileCache(
            settings.token_path,
            settings.token_encryption_key,
        )
        self.auth = SpotifyOAuth(
            client_id=settings.spotify_client_id,
            client_secret=settings.spotify_client_secret,
            redirect_uri=settings.spotify_redirect_uri,
            scope=SPOTIFY_SCOPES,
            cache_handler=self.cache,
            open_browser=False,
            requests_timeout=10,
        )
        self._client: spotipy.Spotify | None = None
        self._profile: dict[str, Any] | None = None
        self._lock = threading.RLock()

    @property
    def connected(self) -> bool:
        with self._lock:
            return self._client is not None

    @property
    def client(self) -> spotipy.Spotify:
        with self._lock:
            if self._client is None:
                raise RuntimeError("Spotify no está conectado.")
            return self._client

    def _new_client(self) -> spotipy.Spotify:
        return spotipy.Spotify(
            auth_manager=self.auth,
            requests_timeout=10,
            retries=2,
            status_retries=2,
            backoff_factor=0.5,
        )

    def connect_cached(self) -> bool:
        if not self.cache.get_cached_token():
            return False
        try:
            client = self._new_client()
            profile = client.current_user()
        except Exception:
            LOGGER.exception("El token de Spotify requiere una nueva autorización.")
            return False
        with self._lock:
            self._client = client
            self._profile = dict(profile)
        return True

    def authorization_url(self, state: str) -> str:
        return self.auth.get_authorize_url(state=state)

    def complete_authorization(self, code: str) -> dict[str, Any]:
        self.auth.get_access_token(code, check_cache=False)
        client = self._new_client()
        profile = client.current_user()
        with self._lock:
            self._client = client
            self._profile = dict(profile)
        return dict(profile)

    def disconnect(self) -> None:
        with self._lock:
            self._client = None
            self._profile = None
        self.cache.clear()

    def _api(self, method: str, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            return getattr(self.client, method)(*args, **kwargs)

    def current_profile(self) -> dict[str, Any]:
        with self._lock:
            if self._profile is None:
                self._profile = dict(self._api("current_user"))
            return dict(self._profile)

    def devices(self) -> list[SpotifyDevice]:
        response = self._api("devices") or {}
        return [
            SpotifyDevice(
                id=str(item.get("id") or ""),
                name=str(item.get("name") or "Dispositivo sin nombre"),
                type=str(item.get("type") or ""),
                is_active=bool(item.get("is_active")),
                volume_percent=item.get("volume_percent"),
                is_restricted=bool(item.get("is_restricted")),
            )
            for item in response.get("devices", [])
        ]

    def find_device(
        self,
        *,
        preferred_name: str = "",
        require_usable: bool = True,
    ) -> SpotifyDevice | None:
        devices = self.devices()
        if require_usable:
            devices = [item for item in devices if item.id and not item.is_restricted]
        preferred = preferred_name.casefold().strip()
        if preferred:
            exact = [item for item in devices if item.name.casefold() == preferred]
            if exact:
                return exact[0]
            partial = [item for item in devices if preferred in item.name.casefold()]
            if partial:
                return partial[0]
        active = [item for item in devices if item.is_active]
        return active[0] if active else (devices[0] if devices else None)

    def playlists(self) -> list[SpotifyPlaylist]:
        result: list[SpotifyPlaylist] = []
        offset = 0
        while True:
            page = self._api("current_user_playlists", limit=50, offset=offset)
            items = page.get("items", [])
            for item in items:
                if not item:
                    continue
                owner = item.get("owner") or {}
                tracks = item.get("tracks") or item.get("items") or {}
                images = item.get("images") or []
                result.append(
                    SpotifyPlaylist(
                        id=str(item.get("id") or ""),
                        name=str(item.get("name") or ""),
                        owner=str(owner.get("display_name") or owner.get("id") or ""),
                        tracks_total=int(tracks.get("total") or 0),
                        image_url=str(images[0].get("url") or "") if images else "",
                    )
                )
            if len(items) < 50:
                break
            offset += 50
        return result

    def playlist(self, playlist_id: str) -> SpotifyPlaylist:
        item = self._api("playlist", playlist_id)
        owner = item.get("owner") or {}
        tracks = item.get("tracks") or item.get("items") or {}
        images = item.get("images") or []
        return SpotifyPlaylist(
            id=str(item.get("id") or playlist_id),
            name=str(item.get("name") or ""),
            owner=str(owner.get("display_name") or owner.get("id") or ""),
            tracks_total=int(tracks.get("total") or 0),
            image_url=str(images[0].get("url") or "") if images else "",
        )

    def playlist_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = self._api(
                "playlist_items",
                playlist_id,
                limit=100,
                offset=offset,
                additional_types=("track",),
            )
            items = page.get("items", [])
            for wrapper in items:
                track = wrapper.get("track") or wrapper.get("item")
                if track and track.get("type", "track") == "track":
                    result.append(track)
            if len(items) < 100:
                break
            offset += 100
        return result

    def recently_played(self, limit: int = 50) -> list[dict[str, Any]]:
        response = self._api("current_user_recently_played", limit=max(1, min(limit, 50)))
        return [
            item.get("track") or {}
            for item in response.get("items", [])
            if item.get("track")
        ]

    def recent_uris(self, limit: int = 50) -> set[str]:
        return {
            str(track.get("uri"))
            for track in self.recently_played(limit)
            if track.get("uri")
        }

    def current_playback(self) -> dict[str, Any] | None:
        return self._api("current_playback")

    def start_playlist(self, playlist_id: str, *, device_id: str, position_ms: int = 0) -> None:
        self._api(
            "start_playback",
            device_id=device_id,
            context_uri=f"spotify:playlist:{playlist_id}",
            position_ms=position_ms,
        )

    def pause(self, *, device_id: str | None = None) -> None:
        self._api("pause_playback", device_id=device_id)

    def next_track(self, *, device_id: str | None = None) -> None:
        self._api("next_track", device_id=device_id)

    def create_random_queue(
        self,
        source_playlist_id: str,
        *,
        max_tracks: int = 100,
        avoid_recent_count: int = 30,
        skip_explicit: bool = False,
    ) -> tuple[str, str, int]:
        source = self.playlist(source_playlist_id)
        tracks = self.playlist_tracks(source_playlist_id)
        if skip_explicit:
            tracks = [track for track in tracks if not track.get("explicit")]
        recent = self.recent_uris(min(avoid_recent_count, 50)) if avoid_recent_count else set()
        queue = build_random_queue(
            tracks,
            recent_uris=recent,
            max_tracks=max_tracks,
            avoid_same_artist=True,
        )
        uris = [str(track.get("uri")) for track in queue if track.get("uri")]
        if not uris:
            raise RuntimeError("No se encontraron canciones reproducibles para la cola aleatoria.")

        profile = self.current_profile()
        name = f"{source.name} · Cola temporal {datetime.now():%Y-%m-%d %H:%M}"
        created = self._api(
            "user_playlist_create",
            user=str(profile["id"]),
            name=name,
            public=False,
            collaborative=False,
            description="Generada automáticamente por Spoxu.",
        )
        temporary_id = str(created["id"])
        for index in range(0, len(uris), 100):
            self._api("playlist_add_items", temporary_id, uris[index : index + 100])
        self.storage.remember_temporary_playlist(
            temporary_id,
            source_playlist_id,
            {"name": name, "track_count": len(uris)},
        )
        return temporary_id, name, len(uris)


class WebRuntime:
    def __init__(self, settings: WebSettings):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.settings = settings
        self.storage = Storage(settings.database_path)
        self.spotify = ServerSpotifyService(settings, self.storage)
        self.config = AppConfig(
            polling_seconds=3.0,
            launch_spotify_if_missing=False,
            pause_outside_schedule=True,
            random_queue_limit=100,
            avoid_recent_tracks=30,
        )
        self._status_lock = threading.RLock()
        self._message = "Motor preparado."
        self.controller = AutomationController(
            self.storage,
            self.spotify,
            lambda: self.config,
            self._on_status,
        )

    def _on_status(self, message: str, payload: dict[str, Any] | None = None) -> None:
        with self._status_lock:
            self._message = message

    def start(self) -> None:
        if not self.settings.automation_enabled:
            return
        self.spotify.connect_cached()
        self.controller.start()

    def stop(self) -> None:
        self.controller.stop()

    def status(self) -> dict[str, Any]:
        with self._status_lock:
            message = self._message
        return {
            "message": message,
            "spotify_connected": self.spotify.connected,
            "automation_paused": self.controller.paused,
            "automation_running": self.controller.running,
        }
