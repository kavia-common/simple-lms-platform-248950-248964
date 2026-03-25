from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from src.core.config import get_settings


def _connect(db_path: str) -> sqlite3.Connection:
    """Create a SQLite connection with sensible defaults for this app."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """Yield a DB connection and ensure close."""
    settings = get_settings()
    conn = _connect(settings.sqlite_db_path)
    try:
        yield conn
    finally:
        conn.close()
