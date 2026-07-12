from datetime import date, datetime, time

from spotify_scheduler_pro.models import ScheduleEntry, ScheduleKind
from spotify_scheduler_pro.scheduler import SchedulerEngine


def test_weekly_schedule_matches_inside_range() -> None:
    entry = ScheduleEntry(
        name="Mañana",
        kind=ScheduleKind.WEEKLY,
        day_of_week=0,
        start_time=time(8, 0),
        end_time=time(9, 0),
        playlist_id="abc",
    )
    assert entry.matches(datetime(2026, 7, 13, 8, 30))
    assert not entry.matches(datetime(2026, 7, 13, 9, 0))


def test_weekly_overnight_schedule_matches_next_day() -> None:
    entry = ScheduleEntry(
        name="Noche",
        kind=ScheduleKind.WEEKLY,
        day_of_week=4,
        start_time=time(22, 0),
        end_time=time(2, 0),
        playlist_id="abc",
    )
    assert entry.matches(datetime(2026, 7, 10, 23, 0))
    assert entry.matches(datetime(2026, 7, 11, 1, 30))
    assert not entry.matches(datetime(2026, 7, 11, 2, 0))


def test_date_overnight_schedule_matches_next_date() -> None:
    entry = ScheduleEntry(
        name="Evento",
        kind=ScheduleKind.DATE,
        specific_date=date(2026, 7, 20),
        day_of_week=None,
        start_time=time(21, 0),
        end_time=time(1, 0),
        playlist_id="abc",
    )
    assert entry.matches(datetime(2026, 7, 20, 23, 59))
    assert entry.matches(datetime(2026, 7, 21, 0, 30))
    assert not entry.matches(datetime(2026, 7, 21, 1, 0))


def test_priority_selects_dominant_schedule() -> None:
    low = ScheduleEntry(
        id=1,
        name="Baja",
        day_of_week=0,
        start_time=time(8, 0),
        end_time=time(10, 0),
        playlist_id="low",
        priority=0,
    )
    high = ScheduleEntry(
        id=2,
        name="Alta",
        day_of_week=0,
        start_time=time(8, 30),
        end_time=time(9, 30),
        playlist_id="high",
        priority=10,
    )
    engine = SchedulerEngine([low, high])
    assert engine.active_entry(datetime(2026, 7, 13, 9, 0)) == high


def test_detects_weekly_overlap() -> None:
    first = ScheduleEntry(
        id=1,
        name="Uno",
        day_of_week=0,
        start_time=time(8, 0),
        end_time=time(10, 0),
        playlist_id="a",
    )
    second = ScheduleEntry(
        name="Dos",
        day_of_week=0,
        start_time=time(9, 0),
        end_time=time(11, 0),
        playlist_id="b",
    )
    engine = SchedulerEngine([first])
    assert len(engine.conflicts_for(second)) == 1


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
