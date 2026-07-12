from __future__ import annotations

import base64
import json
import logging
import threading
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import keyring
import requests
import spotipy
from keyring.errors import KeyringError
from PIL import Image
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyOAuth

from .config import AppConfig, ConfigManager
from .models import SpotifyDevice, SpotifyPlaylist
from .paths import AppPaths
from .random_queue import build_random_queue
from .storage import Storage

LOGGER = logging.getLogger("spotify_scheduler_pro.spotify")

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
        "ugc-image-upload",
    ]
)


class SpotifyNotConfiguredError(RuntimeError):
    pass


class SpotifyPremiumRequiredError(RuntimeError):
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


class SpotifyService:
    def __init__(
        self,
        config_manager: ConfigManager,
        paths: AppPaths,
        storage: Storage,
    ):
        self.config_manager = config_manager
        self.paths = paths
        self.storage = storage
        self._client: spotipy.Spotify | None = None
        self._lock = threading.RLock()
        self._profile: dict[str, Any] | None = None
        self._token_cache: KeyringTokenCache | None = None

    @property
    def connected(self) -> bool:
        with self._lock:
            return self._client is not None

    @property
    def client(self) -> spotipy.Spotify:
        if self._client is None:
            raise SpotifyNotConfiguredError(
                "Spotify no está conectado. Configura Client ID y Client Secret."
            )
        return self._client

    def connect(self, config: AppConfig, *, force_dialog: bool = False) -> dict[str, Any]:
        client_secret = self.config_manager.get_client_secret()
        if not config.client_id.strip() or not client_secret.strip():
            raise SpotifyNotConfiguredError(
                "Debes configurar Client ID y Client Secret antes de autorizar."
            )

        token_cache = KeyringTokenCache(config.client_id.strip())
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
        return dict(profile)

    def disconnect(self, *, delete_cache: bool = False) -> None:
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
            return method(*args, **kwargs)

    def devices(self) -> list[SpotifyDevice]:
        response = self._api_call("devices") or {}
        devices: list[SpotifyDevice] = []
        for raw in response.get("devices", []):
            devices.append(
                SpotifyDevice(
                    id=str(raw.get("id") or ""),
                    name=str(raw.get("name") or "Dispositivo sin nombre"),
                    type=str(raw.get("type") or ""),
                    is_active=bool(raw.get("is_active")),
                    volume_percent=raw.get("volume_percent"),
                    is_restricted=bool(raw.get("is_restricted")),
                )
            )
        return devices

    def find_device(
        self,
        *,
        preferred_name: str = "",
        require_usable: bool = True,
    ) -> SpotifyDevice | None:
        devices = self.devices()
        if require_usable:
            devices = [device for device in devices if device.id and not device.is_restricted]

        preferred = preferred_name.casefold().strip()
        if preferred:
            exact = [device for device in devices if device.name.casefold() == preferred]
            if exact:
                return exact[0]
            partial = [device for device in devices if preferred in device.name.casefold()]
            if partial:
                return partial[0]

        active = [device for device in devices if device.is_active]
        return active[0] if active else (devices[0] if devices else None)

    def playlists(self) -> list[SpotifyPlaylist]:
        result: list[SpotifyPlaylist] = []
        offset = 0
        limit = 50

        while True:
            page = self._api_call("current_user_playlists", limit=limit, offset=offset)
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
            if len(items) < limit:
                break
            offset += limit

        return result

    def playlist(self, playlist_id: str) -> SpotifyPlaylist:
        raw = self._api_call("playlist", playlist_id)
        owner = raw.get("owner") or {}
        tracks = raw.get("tracks") or raw.get("items") or {}
        images = raw.get("images") or []
        return SpotifyPlaylist(
            id=str(raw.get("id") or playlist_id),
            name=str(raw.get("name") or ""),
            owner=str(owner.get("display_name") or owner.get("id") or ""),
            tracks_total=int(tracks.get("total") or 0),
            image_url=str(images[0].get("url") or "") if images else "",
        )

    def playlist_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        tracks: list[dict[str, Any]] = []
        offset = 0
        limit = 100

        while True:
            response = self._api_call("playlist_items",
                playlist_id,
                limit=limit,
                offset=offset,
                additional_types=("track",),
            )
            items = response.get("items", [])
            for wrapper in items:
                track = wrapper.get("track") or wrapper.get("item")
                if track and track.get("type", "track") == "track":
                    tracks.append(track)
            if len(items) < limit:
                break
            offset += limit

        return tracks

    def recently_played(self, limit: int = 50) -> list[dict[str, Any]]:
        response = self._api_call("current_user_recently_played", limit=max(1, min(limit, 50)))
        result: list[dict[str, Any]] = []

        for item in response.get("items", []):
            track = item.get("track") or {}
            artists = track.get("artists") or []
            result.append(
                {
                    "played_at": item.get("played_at"),
                    "uri": track.get("uri"),
                    "name": track.get("name"),
                    "artists": ", ".join(
                        str(artist.get("name") or "")
                        for artist in artists
                        if isinstance(artist, dict)
                    ),
                    "explicit": bool(track.get("explicit")),
                }
            )
        return result

    def recent_uris(self, limit: int = 50) -> set[str]:
        return {
            str(item.get("uri"))
            for item in self.recently_played(limit)
            if item.get("uri")
        }

    def current_playback(self) -> dict[str, Any] | None:
        return self._api_call("current_playback")

    def start_playlist(
        self,
        playlist_id: str,
        *,
        device_id: str,
        position_ms: int = 0,
    ) -> None:
        self._api_call("start_playback",
            device_id=device_id,
            context_uri=f"spotify:playlist:{playlist_id}",
            position_ms=position_ms,
        )

    def pause(self, *, device_id: str | None = None) -> None:
        self._api_call("pause_playback", device_id=device_id)

    def next_track(self, *, device_id: str | None = None) -> None:
        self._api_call("next_track", device_id=device_id)

    def transfer_playback(self, device_id: str, *, force_play: bool = False) -> None:
        self._api_call("transfer_playback", device_id=device_id, force_play=force_play)

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
        user_id = str(profile["id"])
        name = f"{source.name} · Cola temporal {datetime.now():%Y-%m-%d %H:%M}"

        created = self._api_call("user_playlist_create",
            user=user_id,
            name=name,
            public=False,
            collaborative=False,
            description="Generada automáticamente por Spotify Scheduler Pro.",
        )
        temporary_id = str(created["id"])

        for index in range(0, len(uris), 100):
            self._api_call("playlist_add_items", temporary_id, uris[index : index + 100])

        self.storage.remember_temporary_playlist(
            temporary_id,
            source_playlist_id,
            {
                "name": name,
                "track_count": len(uris),
            },
        )
        LOGGER.info(
            "Cola temporal creada: %s desde %s con %s canciones.",
            temporary_id,
            source_playlist_id,
            len(uris),
        )
        return temporary_id, name, len(uris)

    def cleanup_temporary_playlists(self, *, older_than_hours: int = 24) -> int:
        from datetime import timedelta

        threshold = datetime.now() - timedelta(hours=older_than_hours)
        removed = 0

        for record in self.storage.list_temporary_playlists():
            created_at = record["created_at"]
            if not isinstance(created_at, datetime) or created_at >= threshold:
                continue

            playlist_id = str(record["playlist_id"])
            try:
                self._api_call("current_user_unfollow_playlist", playlist_id)
            except Exception:
                LOGGER.exception("No se pudo eliminar la playlist temporal %s.", playlist_id)
                continue

            self.storage.forget_temporary_playlist(playlist_id)
            removed += 1

        return removed

    def export_playlist(self, playlist_id: str, target: Path) -> Path:
        playlist = self.playlist(playlist_id)
        tracks = self.playlist_tracks(playlist_id)
        image_b64 = ""

        if playlist.image_url:
            try:
                response = requests.get(playlist.image_url, timeout=10)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
                if image.format == "JPEG" and len(response.content) <= 256 * 1024:
                    image_b64 = base64.b64encode(response.content).decode("ascii")
            except Exception:
                LOGGER.exception("No se pudo incluir la portada al exportar.")

        payload = {
            "format": "spotify-scheduler-pro-playlist-v1",
            "metadata": {
                "name": playlist.name,
                "owner": playlist.owner,
                "source_playlist_id": playlist.id,
                "exported_at": datetime.now().isoformat(timespec="seconds"),
                "image_b64": image_b64,
            },
            "tracks": [
                {
                    "uri": track.get("uri"),
                    "name": track.get("name"),
                    "artists": [
                        artist.get("name")
                        for artist in track.get("artists", [])
                        if isinstance(artist, dict)
                    ],
                }
                for track in tracks
                if track.get("uri") and ":local:" not in str(track.get("uri"))
            ],
        }

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    def import_playlist(self, source: Path, *, new_name: str | None = None) -> SpotifyPlaylist:
        payload = json.loads(source.read_text(encoding="utf-8"))
        if payload.get("format") != "spotify-scheduler-pro-playlist-v1":
            raise ValueError("El archivo no pertenece al formato Spotify Scheduler Pro.")

        metadata = payload.get("metadata") or {}
        tracks = payload.get("tracks") or []
        uris = [
            str(track.get("uri"))
            for track in tracks
            if isinstance(track, dict) and track.get("uri")
        ]
        if not uris:
            raise ValueError("El archivo no contiene canciones válidas.")

        profile = self.current_profile()
        playlist_name = new_name or str(metadata.get("name") or "Playlist importada")
        created = self._api_call("user_playlist_create",
            user=str(profile["id"]),
            name=playlist_name,
            public=False,
            description=f"Importada por Spotify Scheduler Pro el {datetime.now():%Y-%m-%d}.",
        )
        playlist_id = str(created["id"])

        for index in range(0, len(uris), 100):
            self._api_call("playlist_add_items", playlist_id, uris[index : index + 100])

        image_b64 = str(metadata.get("image_b64") or "")
        if image_b64:
            try:
                raw = base64.b64decode(image_b64)
                image = Image.open(BytesIO(raw))
                if image.format == "JPEG" and len(raw) <= 256 * 1024:
                    self._api_call("playlist_upload_cover_image", playlist_id, image_b64)
            except Exception:
                LOGGER.exception("La portada importada no pudo cargarse.")

        return self.playlist(playlist_id)
