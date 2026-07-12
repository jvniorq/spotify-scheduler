from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime
from typing import Any

from .config import AppConfig
from .models import PlaybackEvent, ScheduleEntry
from .scheduler import SchedulerEngine
from .spotify_client import SpotifyService
from .storage import Storage
from .system_control import launch_spotify, spotify_process_running

LOGGER = logging.getLogger("spotify_scheduler_pro.controller")


StatusCallback = Callable[[str, dict[str, Any] | None], None]


class AutomationController:
    def __init__(
        self,
        storage: Storage,
        spotify: SpotifyService,
        config_provider: Callable[[], AppConfig],
        status_callback: StatusCallback | None = None,
    ):
        self.storage = storage
        self.spotify = spotify
        self.config_provider = config_provider
        self.status_callback = status_callback

        self._stop_event = threading.Event()
        self._paused_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_schedule_id: int | None = None
        self._started_by_automation = False
        self._last_temporary_playlist_id: str | None = None
        self._last_status = ""

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def paused(self) -> bool:
        return self._paused_event.is_set()

    def start(self) -> None:
        if self.running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="SpotifyAutomation",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def pause_automation(self) -> None:
        self._paused_event.set()
        self._emit("Automatización pausada.")

    def resume_automation(self) -> None:
        self._paused_event.clear()
        self._emit("Automatización reanudada.")

    def toggle_pause(self) -> bool:
        if self.paused:
            self.resume_automation()
        else:
            self.pause_automation()
        return self.paused

    def refresh(self) -> None:
        self._last_schedule_id = None

    def _emit(self, message: str, payload: dict[str, Any] | None = None) -> None:
        if message != self._last_status:
            LOGGER.info(message)
            self._last_status = message
        if self.status_callback:
            try:
                self.status_callback(message, payload)
            except Exception:
                LOGGER.exception("Falló el callback de estado.")

    def _log_event(
        self,
        event_type: str,
        entry: ScheduleEntry | None = None,
        *,
        playlist_id: str = "",
        playlist_name: str = "",
        device_name: str = "",
        details: str = "",
    ) -> None:
        self.storage.add_event(
            PlaybackEvent(
                timestamp=datetime.now(),
                event_type=event_type,
                schedule_id=entry.id if entry else None,
                playlist_id=playlist_id or (entry.playlist_id if entry else ""),
                playlist_name=playlist_name or (entry.playlist_name if entry else ""),
                device_name=device_name or (entry.device_name if entry else ""),
                details=details,
            )
        )

    def _run(self) -> None:
        LOGGER.info("Motor de automatización iniciado.")
        while not self._stop_event.is_set():
            config = self.config_provider()
            try:
                self._tick(config)
            except Exception as exc:
                LOGGER.exception("Error durante el ciclo de automatización.")
                self._emit(f"Error de automatización: {exc}")
                self._log_event("error", details=str(exc))
            self._stop_event.wait(max(1.0, float(config.polling_seconds)))
        LOGGER.info("Motor de automatización detenido.")

    def _tick(self, config: AppConfig) -> None:
        if self.paused:
            self._emit("Automatización pausada.")
            return

        if not self.spotify.connected:
            self._emit("Spotify no está conectado.")
            return

        entries = self.storage.list_schedules(enabled_only=True)
        engine = SchedulerEngine(entries)
        now = datetime.now()
        active = engine.active_entry(now)

        if active is None:
            next_info = engine.next_entry(now)
            if (
                config.pause_outside_schedule
                and self._started_by_automation
            ):
                try:
                    self.spotify.pause()
                    self._log_event("pause_outside_schedule", details="Fuera de horario.")
                except Exception:
                    LOGGER.exception("No se pudo pausar fuera del horario.")
                self._started_by_automation = False
                self._last_schedule_id = None

            if next_info:
                entry, start = next_info
                self._emit(
                    f"Sin horario activo. Próximo: {entry.name} a las {start:%Y-%m-%d %H:%M:%S}."
                )
            else:
                self._emit("Sin horario activo ni próximos horarios.")
            return

        if config.launch_spotify_if_missing and not spotify_process_running():
            launch_spotify()

        device_name = active.device_name or config.default_device_name
        device = self.spotify.find_device(preferred_name=device_name)

        if device is None:
            self._emit(
                "No se encontró un dispositivo Spotify Connect utilizable.",
                {"schedule_id": active.id},
            )
            return

        playback = self.spotify.current_playback() or {}
        current_context = playback.get("context") or {}
        current_playlist_id = str(current_context.get("uri") or "").split(":")[-1]
        currently_playing = bool(playback.get("is_playing"))
        active_device = playback.get("device") or {}
        active_device_id = str(active_device.get("id") or "")

        schedule_changed = active.id != self._last_schedule_id
        device_changed = active_device_id != device.id
        playlist_changed = current_playlist_id not in {
            active.playlist_id,
            self._last_temporary_playlist_id or "",
        }

        should_start = (
            schedule_changed
            or not currently_playing
            or device_changed
            or playlist_changed
        )

        if should_start:
            playlist_id = active.playlist_id
            playlist_name = active.playlist_name

            if active.random_queue:
                temporary_id, temporary_name, track_count = self.spotify.create_random_queue(
                    active.playlist_id,
                    max_tracks=config.random_queue_limit,
                    avoid_recent_count=config.avoid_recent_tracks,
                    skip_explicit=active.skip_explicit or config.skip_explicit,
                )
                playlist_id = temporary_id
                playlist_name = temporary_name
                self._last_temporary_playlist_id = temporary_id
                self._log_event(
                    "random_queue_created",
                    active,
                    playlist_id=temporary_id,
                    playlist_name=temporary_name,
                    device_name=device.name,
                    details=f"{track_count} canciones.",
                )
            else:
                self._last_temporary_playlist_id = None

            self.spotify.start_playlist(playlist_id, device_id=device.id)
            self._last_schedule_id = active.id
            self._started_by_automation = True

            self._log_event(
                "play",
                active,
                playlist_id=playlist_id,
                playlist_name=playlist_name,
                device_name=device.name,
            )
            self._emit(
                f"Reproduciendo “{playlist_name or active.playlist_id}” en {device.name}.",
                {"schedule_id": active.id, "playlist_id": playlist_id},
            )
            return

        if active.skip_explicit or config.skip_explicit:
            item = playback.get("item") or {}
            if item.get("explicit"):
                self.spotify.next_track(device_id=device.id)
                self._log_event(
                    "skip_explicit",
                    active,
                    device_name=device.name,
                    details=f"{item.get('name', '')}",
                )

        end = active.end_datetime_for(now)
        suffix = f" hasta {end:%H:%M:%S}" if end else ""
        self._emit(f"Horario activo: {active.name}{suffix}.")
