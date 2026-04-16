"""SQLite-backed spool for store-and-forward durability."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class BufferedRecord:
    row_id: int
    kafka_topic: str
    key: str
    payload: str


class SpoolBuffer:
    def __init__(self, db_path: str) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._db.execute("PRAGMA busy_timeout = 5000")
            self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS spool (
                    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kafka_topic TEXT NOT NULL,
                    message_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    sent_at TEXT
                )
                """
            )
            self._db.execute("CREATE INDEX IF NOT EXISTS idx_spool_status ON spool (status, row_id)")
            self._db.commit()

    def enqueue(self, kafka_topic: str, message_key: str, payload: str) -> int:
        with self._lock:
            cursor = self._db.execute(
                """
                INSERT INTO spool (kafka_topic, message_key, payload, status, created_at)
                VALUES (?, ?, ?, 'pending', ?)
                """,
                (kafka_topic, message_key, payload, datetime.now(UTC).isoformat()),
            )
            self._db.commit()
            return int(cursor.lastrowid)

    def pending(self, limit: int) -> list[BufferedRecord]:
        with self._lock:
            cursor = self._db.execute(
                """
                SELECT row_id, kafka_topic, message_key, payload
                FROM spool
                WHERE status = 'pending'
                ORDER BY row_id
                LIMIT ?
                """,
                (limit,),
            )
            return [
                BufferedRecord(
                    row_id=int(row["row_id"]),
                    kafka_topic=str(row["kafka_topic"]),
                    key=str(row["message_key"]),
                    payload=str(row["payload"]),
                )
                for row in cursor.fetchall()
            ]

    def mark_sent(self, row_id: int) -> None:
        with self._lock:
            self._db.execute(
                """
                UPDATE spool
                SET status = 'sent', sent_at = ?, attempts = attempts + 1
                WHERE row_id = ?
                """,
                (datetime.now(UTC).isoformat(), row_id),
            )
            self._db.commit()

    def mark_failed(self, row_id: int, error: str) -> None:
        with self._lock:
            self._db.execute(
                """
                UPDATE spool
                SET attempts = attempts + 1, last_error = ?
                WHERE row_id = ?
                """,
                (error[:400], row_id),
            )
            self._db.commit()

    def depth(self) -> int:
        with self._lock:
            row = self._db.execute("SELECT COUNT(*) AS count FROM spool WHERE status = 'pending'").fetchone()
            return int(row["count"])
