from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime, time
from pathlib import Path
from collections.abc import Iterator

from .models import PlaybackEvent, ScheduleEntry, ScheduleKind


class Storage:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            conn = sqlite3.connect(self.database_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 5000")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('weekly', 'date')),
                    day_of_week INTEGER,
                    specific_date TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    playlist_id TEXT NOT NULL,
                    playlist_name TEXT NOT NULL DEFAULT '',
                    device_name TEXT NOT NULL DEFAULT '',
                    random_queue INTEGER NOT NULL DEFAULT 0,
                    skip_explicit INTEGER NOT NULL DEFAULT 0,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    priority INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_schedules_enabled
                    ON schedules(enabled, kind, day_of_week, specific_date);

                CREATE TABLE IF NOT EXISTS playback_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    schedule_id INTEGER,
                    playlist_id TEXT NOT NULL DEFAULT '',
                    playlist_name TEXT NOT NULL DEFAULT '',
                    device_name TEXT NOT NULL DEFAULT '',
                    details TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(schedule_id) REFERENCES schedules(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_playback_events_timestamp
                    ON playback_events(timestamp DESC);

                CREATE TABLE IF NOT EXISTS temporary_playlists (
                    playlist_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    source_playlist_id TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                """
            )

    @staticmethod
    def _parse_time(value: str) -> time:
        return time.fromisoformat(value)

    @staticmethod
    def _row_to_schedule(row: sqlite3.Row) -> ScheduleEntry:
        return ScheduleEntry(
            id=row["id"],
            name=row["name"],
            kind=ScheduleKind(row["kind"]),
            day_of_week=row["day_of_week"],
            specific_date=date.fromisoformat(row["specific_date"]) if row["specific_date"] else None,
            start_time=Storage._parse_time(row["start_time"]),
            end_time=Storage._parse_time(row["end_time"]),
            playlist_id=row["playlist_id"],
            playlist_name=row["playlist_name"],
            device_name=row["device_name"],
            random_queue=bool(row["random_queue"]),
            skip_explicit=bool(row["skip_explicit"]),
            enabled=bool(row["enabled"]),
            priority=row["priority"],
        )

    def list_schedules(self, enabled_only: bool = False) -> list[ScheduleEntry]:
        query = "SELECT * FROM schedules"
        params: tuple[object, ...] = ()
        if enabled_only:
            query += " WHERE enabled = ?"
            params = (1,)
        query += """
            ORDER BY
                enabled DESC,
                CASE kind WHEN 'weekly' THEN 0 ELSE 1 END,
                COALESCE(day_of_week, 8),
                COALESCE(specific_date, '9999-12-31'),
                start_time,
                priority DESC
        """

        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_schedule(row) for row in rows]

    def get_schedule(self, schedule_id: int) -> ScheduleEntry | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM schedules WHERE id = ?",
                (schedule_id,),
            ).fetchone()
        return self._row_to_schedule(row) if row else None

    def save_schedule(self, entry: ScheduleEntry) -> ScheduleEntry:
        errors = entry.validate()
        if errors:
            raise ValueError(" ".join(errors))

        now = datetime.now().isoformat(timespec="seconds")
        values = (
            entry.name.strip(),
            entry.kind.value,
            entry.day_of_week,
            entry.specific_date.isoformat() if entry.specific_date else None,
            entry.start_time.isoformat(timespec="seconds"),
            entry.end_time.isoformat(timespec="seconds"),
            entry.playlist_id.strip(),
            entry.playlist_name.strip(),
            entry.device_name.strip(),
            int(entry.random_queue),
            int(entry.skip_explicit),
            int(entry.enabled),
            int(entry.priority),
            now,
        )

        with self.connection() as conn:
            if entry.id is None:
                cursor = conn.execute(
                    """
                    INSERT INTO schedules (
                        name, kind, day_of_week, specific_date,
                        start_time, end_time, playlist_id, playlist_name,
                        device_name, random_queue, skip_explicit,
                        enabled, priority, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (*values[:-1], now, values[-1]),
                )
                entry.id = int(cursor.lastrowid)
            else:
                conn.execute(
                    """
                    UPDATE schedules
                    SET name = ?, kind = ?, day_of_week = ?, specific_date = ?,
                        start_time = ?, end_time = ?, playlist_id = ?, playlist_name = ?,
                        device_name = ?, random_queue = ?, skip_explicit = ?,
                        enabled = ?, priority = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (*values, entry.id),
                )
        return entry

    def delete_schedule(self, schedule_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))

    def set_schedule_enabled(self, schedule_id: int, enabled: bool) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE schedules SET enabled = ?, updated_at = ? WHERE id = ?",
                (int(enabled), datetime.now().isoformat(timespec="seconds"), schedule_id),
            )

    def add_event(self, event: PlaybackEvent) -> PlaybackEvent:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO playback_events (
                    timestamp, event_type, schedule_id, playlist_id,
                    playlist_name, device_name, details
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.timestamp.isoformat(timespec="seconds"),
                    event.event_type,
                    event.schedule_id,
                    event.playlist_id,
                    event.playlist_name,
                    event.device_name,
                    event.details,
                ),
            )
            event.id = int(cursor.lastrowid)
        return event

    def list_events(self, limit: int = 200) -> list[PlaybackEvent]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM playback_events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            PlaybackEvent(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                event_type=row["event_type"],
                schedule_id=row["schedule_id"],
                playlist_id=row["playlist_id"],
                playlist_name=row["playlist_name"],
                device_name=row["device_name"],
                details=row["details"],
            )
            for row in rows
        ]

    def remember_temporary_playlist(
        self,
        playlist_id: str,
        source_playlist_id: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO temporary_playlists (
                    playlist_id, created_at, source_playlist_id, metadata_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    playlist_id,
                    datetime.now().isoformat(timespec="seconds"),
                    source_playlist_id,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )

    def list_temporary_playlists(self) -> list[dict[str, object]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM temporary_playlists ORDER BY created_at DESC"
            ).fetchall()
        return [
            {
                "playlist_id": row["playlist_id"],
                "created_at": datetime.fromisoformat(row["created_at"]),
                "source_playlist_id": row["source_playlist_id"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }
            for row in rows
        ]

    def forget_temporary_playlist(self, playlist_id: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM temporary_playlists WHERE playlist_id = ?",
                (playlist_id,),
            )
