from __future__ import annotations

import sqlite3
from typing import Optional


def get_enrollment(conn: sqlite3.Connection, user_id: int, course_id: int) -> Optional[sqlite3.Row]:
    cur = conn.execute(
        "SELECT * FROM enrollments WHERE user_id = ? AND course_id = ?",
        (user_id, course_id),
    )
    return cur.fetchone()


def enroll_user(conn: sqlite3.Connection, user_id: int, course_id: int) -> int:
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO enrollments (user_id, course_id, status)
        VALUES (?, ?, 'enrolled')
        """,
        (user_id, course_id),
    )
    conn.commit()
    if cur.lastrowid:
        return int(cur.lastrowid)
    # If ignored, return existing enrollment id
    existing = get_enrollment(conn, user_id, course_id)
    return int(existing["id"]) if existing else 0


def list_enrollments_for_user(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    cur = conn.execute(
        "SELECT * FROM enrollments WHERE user_id = ? ORDER BY enrolled_at DESC",
        (user_id,),
    )
    return cur.fetchall()


def set_progress(
    conn: sqlite3.Connection,
    user_id: int,
    course_id: int,
    lesson_id: int,
    status: str,
    progress_percent: int,
) -> sqlite3.Row:
    # Upsert-ish via INSERT OR IGNORE then UPDATE
    conn.execute(
        """
        INSERT OR IGNORE INTO lesson_progress (user_id, course_id, lesson_id, status, progress_percent, started_at)
        VALUES (?, ?, ?, 'in_progress', 0, CURRENT_TIMESTAMP)
        """,
        (user_id, course_id, lesson_id),
    )
    conn.execute(
        """
        UPDATE lesson_progress
        SET status = ?,
            progress_percent = ?,
            completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND lesson_id = ?
        """,
        (status, progress_percent, status, user_id, lesson_id),
    )
    conn.commit()
    cur = conn.execute(
        "SELECT * FROM lesson_progress WHERE user_id = ? AND lesson_id = ?",
        (user_id, lesson_id),
    )
    return cur.fetchone()


def get_progress_for_course(conn: sqlite3.Connection, user_id: int, course_id: int) -> list[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT * FROM lesson_progress
        WHERE user_id = ? AND course_id = ?
        ORDER BY lesson_id ASC
        """,
        (user_id, course_id),
    )
    return cur.fetchall()
