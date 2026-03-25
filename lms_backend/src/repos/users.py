from __future__ import annotations

import sqlite3
from typing import Optional

from src.core.security import hash_password


def _row_to_user_public(row: sqlite3.Row, roles: list[str]) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "username": row["username"],
        "full_name": row["full_name"],
        "is_active": bool(row["is_active"]),
        "roles": roles,
    }


def get_user_by_email(conn: sqlite3.Connection, email: str) -> Optional[sqlite3.Row]:
    cur = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
    return cur.fetchone()


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    cur = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cur.fetchone()


def get_user_roles(conn: sqlite3.Connection, user_id: int) -> list[str]:
    cur = conn.execute(
        """
        SELECT r.name
        FROM user_roles ur
        JOIN roles r ON r.id = ur.role_id
        WHERE ur.user_id = ?
        ORDER BY r.name
        """,
        (user_id,),
    )
    return [r[0] for r in cur.fetchall()]


def create_user(
    conn: sqlite3.Connection,
    email: str,
    username: str,
    full_name: Optional[str],
    password: str,
) -> int:
    password_hash = hash_password(password)
    cur = conn.execute(
        """
        INSERT INTO users (email, username, full_name, password_hash, is_active)
        VALUES (?, ?, ?, ?, 1)
        """,
        (email, username, full_name, password_hash),
    )
    conn.commit()
    return int(cur.lastrowid)


def assign_role(conn: sqlite3.Connection, user_id: int, role_name: str) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO user_roles (user_id, role_id)
        VALUES (?, (SELECT id FROM roles WHERE name = ?))
        """,
        (user_id, role_name),
    )
    conn.commit()


def list_users(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.execute("SELECT * FROM users ORDER BY id ASC")
    rows = cur.fetchall()
    out: list[dict] = []
    for row in rows:
        roles = get_user_roles(conn, int(row["id"]))
        out.append(_row_to_user_public(row, roles))
    return out


def set_user_active(conn: sqlite3.Connection, user_id: int, is_active: bool) -> None:
    conn.execute(
        "UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (1 if is_active else 0, user_id),
    )
    conn.commit()


def set_user_roles(conn: sqlite3.Connection, user_id: int, roles: list[str]) -> None:
    conn.execute("DELETE FROM user_roles WHERE user_id = ?", (user_id,))
    for r in roles:
        assign_role(conn, user_id, r)
    conn.commit()
