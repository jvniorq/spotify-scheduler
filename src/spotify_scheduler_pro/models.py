from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import Any


class ScheduleKind(StrEnum):
    WEEKLY = "weekly"
    DATE = "date"


@dataclass(slots=True)
class ScheduleEntry:
    id: int | None = None
    name: str = ""
    kind: ScheduleKind = ScheduleKind.WEEKLY
    day_of_week: int | None = 0
    specific_date: date | None = None
    start_time: time = time(8, 0)
    end_time: time = time(9, 0)
    playlist_id: str = ""
    playlist_name: str = ""
    device_name: str = ""
    random_queue: bool = False
    skip_explicit: bool = False
    enabled: bool = True
    priority: int = 0

    @property
    def crosses_midnight(self) -> bool:
        return self.end_time < self.start_time

    @property
    def time_range(self) -> str:
        return f"{self.start_time.strftime('%H:%M:%S')}–{self.end_time.strftime('%H:%M:%S')}"

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not self.name.strip():
            errors.append("El horario necesita un nombre.")
        if not self.playlist_id.strip():
            errors.append("Debes ingresar una playlist.")
        if self.start_time == self.end_time:
            errors.append("La hora inicial y final no pueden ser iguales.")
        if self.kind == ScheduleKind.WEEKLY and self.day_of_week not in range(7):
            errors.append("El día semanal no es válido.")
        if self.kind == ScheduleKind.DATE and self.specific_date is None:
            errors.append("Debes seleccionar una fecha.")
        if not -100 <= self.priority <= 100:
            errors.append("La prioridad debe estar entre -100 y 100.")

        return errors

    def matches(self, moment: datetime) -> bool:
        if not self.enabled:
            return False

        current_time = moment.time().replace(microsecond=0)

        if self.kind == ScheduleKind.DATE:
            if self.specific_date is None:
                return False
            if not self.crosses_midnight:
                return (
                    moment.date() == self.specific_date
                    and self.start_time <= current_time < self.end_time
                )
            return (
                moment.date() == self.specific_date
                and current_time >= self.start_time
            ) or (
                moment.date() == self.specific_date + timedelta(days=1)
                and current_time < self.end_time
            )

        if self.day_of_week is None:
            return False

        if not self.crosses_midnight:
            return (
                moment.weekday() == self.day_of_week
                and self.start_time <= current_time < self.end_time
            )

        next_day = (self.day_of_week + 1) % 7
        return (
            moment.weekday() == self.day_of_week
            and current_time >= self.start_time
        ) or (
            moment.weekday() == next_day
            and current_time < self.end_time
        )

    def next_start_after(self, moment: datetime) -> datetime | None:
        if not self.enabled:
            return None

        if self.kind == ScheduleKind.DATE:
            if self.specific_date is None:
                return None
            candidate = datetime.combine(self.specific_date, self.start_time)
            return candidate if candidate >= moment else None

        if self.day_of_week is None:
            return None

        days_ahead = (self.day_of_week - moment.weekday()) % 7
        candidate = datetime.combine(moment.date() + timedelta(days=days_ahead), self.start_time)
        if candidate < moment:
            candidate += timedelta(days=7)
        return candidate

    def end_datetime_for(self, moment: datetime) -> datetime | None:
        if not self.matches(moment):
            return None

        if self.kind == ScheduleKind.DATE:
            assert self.specific_date is not None
            end_date = self.specific_date
            if self.crosses_midnight:
                end_date += timedelta(days=1)
            return datetime.combine(end_date, self.end_time)

        if self.day_of_week is None:
            return None

        if self.crosses_midnight and moment.weekday() == self.day_of_week:
            end_date = moment.date() + timedelta(days=1)
        else:
            end_date = moment.date()
        return datetime.combine(end_date, self.end_time)

    def copy_with(self, **changes: Any) -> ScheduleEntry:
        return replace(self, **changes)


@dataclass(slots=True)
class PlaybackEvent:
    id: int | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    event_type: str = ""
    schedule_id: int | None = None
    playlist_id: str = ""
    playlist_name: str = ""
    device_name: str = ""
    details: str = ""


@dataclass(slots=True)
class SpotifyDevice:
    id: str
    name: str
    type: str
    is_active: bool
    volume_percent: int | None
    is_restricted: bool


@dataclass(slots=True)
class SpotifyPlaylist:
    id: str
    name: str
    owner: str
    tracks_total: int
    image_url: str = ""
