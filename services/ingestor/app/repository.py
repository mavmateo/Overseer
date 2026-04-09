"""Database access for the Kafka ingestor."""

from __future__ import annotations

from typing import Iterable

import psycopg

from .config import Settings
from .processors import DbOperation


class DatabaseWriter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._conn: psycopg.Connection | None = None

    def _connection(self) -> psycopg.Connection:
        if self._conn is None or self._conn.closed:
            self._conn = psycopg.connect(self._settings.database_url)
        return self._conn

    def apply(self, operations: Iterable[DbOperation]) -> None:
        conn = self._connection()
        try:
            with conn.transaction(), conn.cursor() as cur:
                for operation in operations:
                    cur.execute(operation.sql, operation.params)
        except Exception:
            conn.rollback()
            raise

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()

