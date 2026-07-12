from datetime import time

from spotify_scheduler_pro.models import ScheduleEntry
from spotify_scheduler_pro.storage import Storage


def test_storage_round_trip(tmp_path) -> None:
    storage = Storage(tmp_path / "scheduler.db")
    entry = ScheduleEntry(
        name="Prueba",
        day_of_week=2,
        start_time=time(10, 0),
        end_time=time(11, 0),
        playlist_id="playlist123",
        playlist_name="Mi playlist",
    )
    saved = storage.save_schedule(entry)
    assert saved.id is not None

    loaded = storage.get_schedule(saved.id)
    assert loaded is not None
    assert loaded.name == "Prueba"
    assert loaded.playlist_id == "playlist123"


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
