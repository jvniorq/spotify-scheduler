from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, time
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pwdlib import PasswordHash
from starlette.middleware.sessions import SessionMiddleware

from spotify_scheduler_pro.models import ScheduleEntry, ScheduleKind
from spotify_scheduler_pro.scheduler import SchedulerEngine
from .config import WebSettings
from .runtime import WebRuntime

STATIC_DIR = Path(__file__).with_name("static")
PASSWORD_HASH = PasswordHash.recommended()


class LoginPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=512)


class SchedulePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    kind: ScheduleKind = ScheduleKind.WEEKLY
    day_of_week: int | None = Field(default=0, ge=0, le=6)
    specific_date: date | None = None
    start_time: time
    end_time: time
    playlist_id: str = Field(min_length=1, max_length=128)
    playlist_name: str = Field(default="", max_length=250)
    device_name: str = Field(default="", max_length=250)
    random_queue: bool = False
    skip_explicit: bool = False
    enabled: bool = True
    priority: int = Field(default=0, ge=-100, le=100)

    @field_validator("name", "playlist_id", "playlist_name", "device_name", mode="before")
    @classmethod
    def trim_text(cls, value: Any) -> str:
        return str(value or "").strip()

    @model_validator(mode="after")
    def validate_schedule(self) -> SchedulePayload:
        if self.start_time == self.end_time:
            raise ValueError("La hora inicial y final no pueden ser iguales.")
        if self.kind == ScheduleKind.WEEKLY:
            if self.day_of_week is None or self.specific_date is not None:
                raise ValueError("Un horario semanal necesita día y no fecha específica.")
        elif self.specific_date is None or self.day_of_week is not None:
            raise ValueError("Un horario por fecha necesita fecha y no día semanal.")
        return self

    def to_entry(self, schedule_id: int | None = None) -> ScheduleEntry:
        return ScheduleEntry(
            id=schedule_id,
            name=self.name,
            kind=self.kind,
            day_of_week=self.day_of_week,
            specific_date=self.specific_date,
            start_time=self.start_time,
            end_time=self.end_time,
            playlist_id=self.playlist_id,
            playlist_name=self.playlist_name,
            device_name=self.device_name,
            random_queue=self.random_queue,
            skip_explicit=self.skip_explicit,
            enabled=self.enabled,
            priority=self.priority,
        )


def schedule_json(entry: ScheduleEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "name": entry.name,
        "kind": entry.kind.value,
        "day_of_week": entry.day_of_week,
        "specific_date": entry.specific_date.isoformat() if entry.specific_date else None,
        "start_time": entry.start_time.isoformat(timespec="seconds"),
        "end_time": entry.end_time.isoformat(timespec="seconds"),
        "playlist_id": entry.playlist_id,
        "playlist_name": entry.playlist_name,
        "device_name": entry.device_name,
        "random_queue": entry.random_queue,
        "skip_explicit": entry.skip_explicit,
        "enabled": entry.enabled,
        "priority": entry.priority,
    }


def get_runtime(request: Request) -> WebRuntime:
    return request.app.state.runtime


def require_auth(request: Request) -> None:
    if request.session.get("authenticated") is not True:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión requerida.")


def require_csrf(
    request: Request,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    require_auth(request)
    expected = request.session.get("csrf_token")
    if not expected or not csrf_header or not secrets.compare_digest(expected, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF inválido.")


def create_app(settings: WebSettings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = WebRuntime(settings)
        app.state.runtime = runtime
        runtime.start()
        try:
            yield
        finally:
            runtime.stop()

    app = FastAPI(
        title="Spoxu Web",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="spoxu_session",
        max_age=7 * 24 * 60 * 60,
        same_site="lax",
        https_only=settings.cookie_secure,
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' https://i.scdn.co data:; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self' "
            "https://accounts.spotify.com"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "spoxu-web"}

    @app.post("/api/login")
    def login(payload: LoginPayload, request: Request) -> JSONResponse:
        if not PASSWORD_HASH.verify(payload.password, settings.admin_password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas.")
        request.session.clear()
        request.session["authenticated"] = True
        request.session["csrf_token"] = secrets.token_urlsafe(32)
        return JSONResponse({"csrf_token": request.session["csrf_token"]})

    @app.post("/api/logout", dependencies=[Depends(require_csrf)])
    def logout(request: Request) -> Response:
        request.session.clear()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/status", dependencies=[Depends(require_auth)])
    def api_status(request: Request, runtime: Annotated[WebRuntime, Depends(get_runtime)]):
        result = runtime.status()
        result["csrf_token"] = request.session.get("csrf_token")
        entries = runtime.storage.list_schedules(enabled_only=True)
        next_info = SchedulerEngine(entries).next_entry(datetime.now())
        if next_info:
            entry, starts_at = next_info
            result["next_schedule"] = {
                "id": entry.id,
                "name": entry.name,
                "starts_at": starts_at.isoformat(timespec="seconds"),
            }
        else:
            result["next_schedule"] = None

        result["events"] = [
            {
                "id": event.id,
                "timestamp": event.timestamp.isoformat(timespec="seconds"),
                "event_type": event.event_type,
                "playlist_name": event.playlist_name,
                "device_name": event.device_name,
                "details": event.details,
            }
            for event in runtime.storage.list_events(limit=30)
        ]
        if runtime.spotify.connected:
            try:
                playback = runtime.spotify.current_playback() or {}
                item = playback.get("item") or {}
                artists = item.get("artists") or []
                result["now_playing"] = {
                    "name": item.get("name") or "",
                    "artists": [artist.get("name") for artist in artists if artist.get("name")],
                    "is_playing": bool(playback.get("is_playing")),
                    "device": (playback.get("device") or {}).get("name") or "",
                }
            except Exception as exc:
                result["playback_error"] = str(exc)
        return result

    @app.get("/api/schedules", dependencies=[Depends(require_auth)])
    def list_schedules(runtime: Annotated[WebRuntime, Depends(get_runtime)]):
        return [schedule_json(item) for item in runtime.storage.list_schedules()]

    @app.get("/api/schedules/{schedule_id}", dependencies=[Depends(require_auth)])
    def get_schedule(schedule_id: int, runtime: Annotated[WebRuntime, Depends(get_runtime)]):
        entry = runtime.storage.get_schedule(schedule_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Horario no encontrado.")
        return schedule_json(entry)

    @app.post("/api/schedules", dependencies=[Depends(require_csrf)])
    def create_schedule(
        payload: SchedulePayload,
        runtime: Annotated[WebRuntime, Depends(get_runtime)],
    ):
        entry = runtime.storage.save_schedule(payload.to_entry())
        runtime.controller.refresh()
        return JSONResponse(
            schedule_json(entry),
            status_code=status.HTTP_201_CREATED,
            headers={"Location": f"/api/schedules/{entry.id}"},
        )

    @app.put("/api/schedules/{schedule_id}", dependencies=[Depends(require_csrf)])
    def update_schedule(
        schedule_id: int,
        payload: SchedulePayload,
        runtime: Annotated[WebRuntime, Depends(get_runtime)],
    ):
        if runtime.storage.get_schedule(schedule_id) is None:
            raise HTTPException(status_code=404, detail="Horario no encontrado.")
        entry = runtime.storage.save_schedule(payload.to_entry(schedule_id))
        runtime.controller.refresh()
        return schedule_json(entry)

    @app.delete("/api/schedules/{schedule_id}", dependencies=[Depends(require_csrf)])
    def delete_schedule(
        schedule_id: int,
        runtime: Annotated[WebRuntime, Depends(get_runtime)],
    ) -> Response:
        if runtime.storage.get_schedule(schedule_id) is None:
            raise HTTPException(status_code=404, detail="Horario no encontrado.")
        runtime.storage.delete_schedule(schedule_id)
        runtime.controller.refresh()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post("/api/schedules/{schedule_id}/test", dependencies=[Depends(require_csrf)])
    def test_schedule(
        schedule_id: int,
        runtime: Annotated[WebRuntime, Depends(get_runtime)],
    ):
        entry = runtime.storage.get_schedule(schedule_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Horario no encontrado.")
        if not runtime.spotify.connected:
            raise HTTPException(status_code=409, detail="Spotify no está conectado.")
        device = runtime.spotify.find_device(preferred_name=entry.device_name)
        if device is None:
            raise HTTPException(status_code=409, detail="No hay dispositivo Spotify Connect disponible.")
        playlist_id = entry.playlist_id
        if entry.random_queue:
            playlist_id, _name, _count = runtime.spotify.create_random_queue(
                entry.playlist_id,
                max_tracks=runtime.config.random_queue_limit,
                avoid_recent_count=runtime.config.avoid_recent_tracks,
                skip_explicit=entry.skip_explicit or runtime.config.skip_explicit,
            )
        runtime.spotify.start_playlist(playlist_id, device_id=device.id)
        return {"ok": True, "device": device.name}

    @app.get("/api/conflicts", dependencies=[Depends(require_auth)])
    def conflicts(
        payload: Annotated[SchedulePayload, Depends()],
        runtime: Annotated[WebRuntime, Depends(get_runtime)],
    ):
        candidate = payload.to_entry()
        found = SchedulerEngine(runtime.storage.list_schedules()).conflicts_for(candidate)
        return [
            {"schedule_id": item.second.id, "name": item.second.name, "reason": item.reason}
            for item in found
        ]

    @app.get("/api/playlists", dependencies=[Depends(require_auth)])
    def playlists(runtime: Annotated[WebRuntime, Depends(get_runtime)]):
        if not runtime.spotify.connected:
            return []
        return [
            {
                "id": item.id,
                "name": item.name,
                "owner": item.owner,
                "tracks_total": item.tracks_total,
                "image_url": item.image_url,
            }
            for item in runtime.spotify.playlists()
        ]

    @app.get("/api/devices", dependencies=[Depends(require_auth)])
    def devices(runtime: Annotated[WebRuntime, Depends(get_runtime)]):
        if not runtime.spotify.connected:
            return []
        return [
            {
                "id": item.id,
                "name": item.name,
                "type": item.type,
                "is_active": item.is_active,
                "volume_percent": item.volume_percent,
                "is_restricted": item.is_restricted,
            }
            for item in runtime.spotify.devices()
        ]

    @app.post("/api/automation/pause", dependencies=[Depends(require_csrf)])
    def pause_automation(runtime: Annotated[WebRuntime, Depends(get_runtime)]):
        runtime.controller.pause_automation()
        return runtime.status()

    @app.post("/api/automation/resume", dependencies=[Depends(require_csrf)])
    def resume_automation(runtime: Annotated[WebRuntime, Depends(get_runtime)]):
        runtime.controller.resume_automation()
        return runtime.status()

    @app.get("/oauth/spotify/start", dependencies=[Depends(require_auth)])
    def spotify_start(request: Request, runtime: Annotated[WebRuntime, Depends(get_runtime)]):
        oauth_state = secrets.token_urlsafe(32)
        request.session["spotify_oauth_state"] = oauth_state
        return RedirectResponse(runtime.spotify.authorization_url(oauth_state))

    @app.get("/oauth/spotify/callback")
    def spotify_callback(
        request: Request,
        runtime: Annotated[WebRuntime, Depends(get_runtime)],
        code: str | None = None,
        state_value: str | None = None,
        state: str | None = None,
        error: str | None = None,
    ):
        require_auth(request)
        expected = request.session.pop("spotify_oauth_state", None)
        received = state or state_value
        if error or not code or not expected or not received or not secrets.compare_digest(expected, received):
            raise HTTPException(status_code=400, detail="Autorización de Spotify inválida.")
        runtime.spotify.complete_authorization(code)
        runtime.controller.refresh()
        return RedirectResponse("/?spotify=connected", status_code=303)

    @app.post("/api/spotify/disconnect", dependencies=[Depends(require_csrf)])
    def spotify_disconnect(runtime: Annotated[WebRuntime, Depends(get_runtime)]):
        runtime.spotify.disconnect()
        runtime.controller.refresh()
        return {"ok": True}

    return app
