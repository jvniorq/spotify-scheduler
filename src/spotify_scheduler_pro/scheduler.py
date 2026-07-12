from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .models import ScheduleEntry, ScheduleKind

DAY_NAMES_ES = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]


@dataclass(slots=True)
class ScheduleConflict:
    first: ScheduleEntry
    second: ScheduleEntry
    reason: str


class SchedulerEngine:
    def __init__(self, entries: list[ScheduleEntry] | None = None):
        self._entries = entries or []

    @property
    def entries(self) -> list[ScheduleEntry]:
        return list(self._entries)

    def replace_entries(self, entries: list[ScheduleEntry]) -> None:
        self._entries = list(entries)

    def active_entries(self, moment: datetime | None = None) -> list[ScheduleEntry]:
        moment = moment or datetime.now()
        active = [entry for entry in self._entries if entry.matches(moment)]
        return sorted(
            active,
            key=lambda item: (
                item.priority,
                item.start_time.hour,
                item.start_time.minute,
                item.start_time.second,
                -(item.id or 0),
            ),
            reverse=True,
        )

    def active_entry(self, moment: datetime | None = None) -> ScheduleEntry | None:
        active = self.active_entries(moment)
        return active[0] if active else None

    def next_entry(
        self,
        moment: datetime | None = None,
    ) -> tuple[ScheduleEntry, datetime] | None:
        moment = moment or datetime.now()
        candidates: list[tuple[ScheduleEntry, datetime]] = []

        for entry in self._entries:
            next_start = entry.next_start_after(moment)
            if next_start is not None:
                candidates.append((entry, next_start))

        if not candidates:
            return None
        return min(candidates, key=lambda item: (item[1], -item[0].priority))

    @staticmethod
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
        return [(start, week_seconds), (0, end)]

    @staticmethod
    def _date_segment(entry: ScheduleEntry) -> tuple[datetime, datetime] | None:
        if entry.specific_date is None:
            return None
        start = datetime.combine(entry.specific_date, entry.start_time)
        end_date = entry.specific_date + timedelta(days=1) if entry.crosses_midnight else entry.specific_date
        end = datetime.combine(end_date, entry.end_time)
        return start, end

    @staticmethod
    def _overlap(a_start: object, a_end: object, b_start: object, b_end: object) -> bool:
        return a_start < b_end and b_start < a_end

    def conflicts_for(self, candidate: ScheduleEntry) -> list[ScheduleConflict]:
        conflicts: list[ScheduleConflict] = []

        for existing in self._entries:
            if existing.id is not None and candidate.id == existing.id:
                continue
            if not existing.enabled or not candidate.enabled:
                continue

            if candidate.kind == ScheduleKind.WEEKLY and existing.kind == ScheduleKind.WEEKLY:
                for a_start, a_end in self._weekly_segments(candidate):
                    for b_start, b_end in self._weekly_segments(existing):
                        if self._overlap(a_start, a_end, b_start, b_end):
                            conflicts.append(
                                ScheduleConflict(
                                    candidate,
                                    existing,
                                    "Los intervalos semanales se superponen.",
                                )
                            )
                            break
                    else:
                        continue
                    break

            elif candidate.kind == ScheduleKind.DATE and existing.kind == ScheduleKind.DATE:
                a = self._date_segment(candidate)
                b = self._date_segment(existing)
                if a and b and self._overlap(a[0], a[1], b[0], b[1]):
                    conflicts.append(
                        ScheduleConflict(
                            candidate,
                            existing,
                            "Los intervalos de fecha específica se superponen.",
                        )
                    )

            else:
                weekly = candidate if candidate.kind == ScheduleKind.WEEKLY else existing
                dated = candidate if candidate.kind == ScheduleKind.DATE else existing
                dated_segment = self._date_segment(dated)
                if dated_segment and weekly.day_of_week is not None:
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
                        cursor_date += timedelta(days=1)

        return conflicts

    def describe_entry(self, entry: ScheduleEntry) -> str:
        if entry.kind == ScheduleKind.WEEKLY:
            when = DAY_NAMES_ES[entry.day_of_week or 0]
        else:
            when = entry.specific_date.isoformat() if entry.specific_date else "Sin fecha"
        overnight = " (cruza medianoche)" if entry.crosses_midnight else ""
        return f"{when} · {entry.time_range}{overnight} · {entry.playlist_name or entry.playlist_id}"

    def status(self, moment: datetime | None = None) -> str:
        moment = moment or datetime.now()
        active = self.active_entry(moment)
        if active:
            end = active.end_datetime_for(moment)
            suffix = f" hasta {end.strftime('%Y-%m-%d %H:%M:%S')}" if end else ""
            return f"Activo: {self.describe_entry(active)}{suffix}"

        upcoming = self.next_entry(moment)
        if not upcoming:
            return "No hay próximos horarios habilitados."
        entry, start = upcoming
        return f"Próximo: {self.describe_entry(entry)} · {start.strftime('%Y-%m-%d %H:%M:%S')}"


def parse_time(value: str) -> time:
    cleaned = value.strip()
    formats = ("%H:%M:%S", "%H:%M")
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).time()
        except ValueError:
            continue
    raise ValueError("La hora debe tener formato HH:MM o HH:MM:SS.")


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError("La fecha debe tener formato AAAA-MM-DD.") from exc
