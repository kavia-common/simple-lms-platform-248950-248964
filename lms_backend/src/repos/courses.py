from __future__ import annotations

import sqlite3
from typing import Optional


def list_courses(conn: sqlite3.Connection, include_unpublished: bool) -> list[sqlite3.Row]:
    if include_unpublished:
        cur = conn.execute("SELECT * FROM courses ORDER BY created_at DESC")
    else:
        cur = conn.execute(
            "SELECT * FROM courses WHERE is_published = 1 ORDER BY created_at DESC"
        )
    return cur.fetchall()


def get_course_by_id(conn: sqlite3.Connection, course_id: int) -> Optional[sqlite3.Row]:
    cur = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    return cur.fetchone()


def get_course_by_slug(conn: sqlite3.Connection, slug: str) -> Optional[sqlite3.Row]:
    cur = conn.execute("SELECT * FROM courses WHERE slug = ?", (slug,))
    return cur.fetchone()


def create_course(
    conn: sqlite3.Connection,
    slug: str,
    title: str,
    description: Optional[str],
    level: Optional[str],
    is_published: bool,
    created_by_user_id: int,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO courses (slug, title, description, level, is_published, created_by_user_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (slug, title, description, level, 1 if is_published else 0, created_by_user_id),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_course(
    conn: sqlite3.Connection,
    course_id: int,
    title: Optional[str],
    description: Optional[str],
    level: Optional[str],
    is_published: Optional[bool],
) -> None:
    # Build dynamic update to avoid overwriting unspecified fields.
    fields = []
    values: list = []
    if title is not None:
        fields.append("title = ?")
        values.append(title)
    if description is not None:
        fields.append("description = ?")
        values.append(description)
    if level is not None:
        fields.append("level = ?")
        values.append(level)
    if is_published is not None:
        fields.append("is_published = ?")
        values.append(1 if is_published else 0)

    if not fields:
        return

    values.append(course_id)
    conn.execute(
        f"UPDATE courses SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        tuple(values),
    )
    conn.commit()


def delete_course(conn: sqlite3.Connection, course_id: int) -> None:
    conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    conn.commit()


def list_lessons(conn: sqlite3.Connection, course_id: int, include_unpublished: bool) -> list[sqlite3.Row]:
    if include_unpublished:
        cur = conn.execute(
            """
            SELECT * FROM course_lessons
            WHERE course_id = ?
            ORDER BY sort_order ASC, id ASC
            """,
            (course_id,),
        )
    else:
        cur = conn.execute(
            """
            SELECT * FROM course_lessons
            WHERE course_id = ? AND is_published = 1
            ORDER BY sort_order ASC, id ASC
            """,
            (course_id,),
        )
    return cur.fetchall()


def get_lesson_by_id(conn: sqlite3.Connection, lesson_id: int) -> Optional[sqlite3.Row]:
    cur = conn.execute("SELECT * FROM course_lessons WHERE id = ?", (lesson_id,))
    return cur.fetchone()


def create_lesson(
    conn: sqlite3.Connection,
    course_id: int,
    slug: str,
    title: str,
    content_type: str,
    content_text: Optional[str],
    video_url: Optional[str],
    resource_url: Optional[str],
    sort_order: int,
    estimated_minutes: Optional[int],
    is_published: bool,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO course_lessons (
            course_id, slug, title, content_type, content_text, video_url, resource_url,
            sort_order, estimated_minutes, is_published
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            course_id,
            slug,
            title,
            content_type,
            content_text,
            video_url,
            resource_url,
            sort_order,
            estimated_minutes,
            1 if is_published else 0,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_lesson(
    conn: sqlite3.Connection,
    lesson_id: int,
    **kwargs,
) -> None:
    allowed = {
        "title",
        "content_type",
        "content_text",
        "video_url",
        "resource_url",
        "sort_order",
        "estimated_minutes",
        "is_published",
    }
    fields = []
    values: list = []
    for k, v in kwargs.items():
        if k not in allowed or v is None:
            continue
        if k == "is_published":
            fields.append("is_published = ?")
            values.append(1 if v else 0)
        else:
            fields.append(f"{k} = ?")
            values.append(v)

    if not fields:
        return

    values.append(lesson_id)
    conn.execute(
        f"UPDATE course_lessons SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        tuple(values),
    )
    conn.commit()


def delete_lesson(conn: sqlite3.Connection, lesson_id: int) -> None:
    conn.execute("DELETE FROM course_lessons WHERE id = ?", (lesson_id,))
    conn.commit()
