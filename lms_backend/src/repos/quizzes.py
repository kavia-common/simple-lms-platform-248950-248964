from __future__ import annotations

import sqlite3
from typing import Optional


def list_quizzes_for_course(conn: sqlite3.Connection, course_id: int) -> list[sqlite3.Row]:
    cur = conn.execute(
        "SELECT * FROM quizzes WHERE course_id = ? AND is_published = 1 ORDER BY id ASC",
        (course_id,),
    )
    return cur.fetchall()


def get_quiz(conn: sqlite3.Connection, quiz_id: int) -> Optional[sqlite3.Row]:
    cur = conn.execute("SELECT * FROM quizzes WHERE id = ? AND is_published = 1", (quiz_id,))
    return cur.fetchone()


def get_questions(conn: sqlite3.Connection, quiz_id: int) -> list[sqlite3.Row]:
    cur = conn.execute(
        "SELECT * FROM quiz_questions WHERE quiz_id = ? ORDER BY sort_order ASC, id ASC",
        (quiz_id,),
    )
    return cur.fetchall()


def get_options_for_question(conn: sqlite3.Connection, question_id: int) -> list[sqlite3.Row]:
    cur = conn.execute(
        "SELECT id, option_text, sort_order FROM quiz_options WHERE question_id = ? ORDER BY sort_order ASC, id ASC",
        (question_id,),
    )
    return cur.fetchall()


def get_correct_option_ids(conn: sqlite3.Connection, question_id: int) -> set[int]:
    cur = conn.execute(
        "SELECT id FROM quiz_options WHERE question_id = ? AND is_correct = 1",
        (question_id,),
    )
    return {int(r[0]) for r in cur.fetchall()}


def get_next_attempt(conn: sqlite3.Connection, quiz_id: int, user_id: int) -> int:
    cur = conn.execute(
        "SELECT COALESCE(MAX(attempt), 0) FROM quiz_submissions WHERE quiz_id = ? AND user_id = ?",
        (quiz_id, user_id),
    )
    return int(cur.fetchone()[0]) + 1


def create_submission(
    conn: sqlite3.Connection,
    quiz_id: int,
    user_id: int,
    attempt: int,
    score_percent: int,
    passed: bool,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO quiz_submissions (quiz_id, user_id, attempt, score_percent, passed)
        VALUES (?, ?, ?, ?, ?)
        """,
        (quiz_id, user_id, attempt, score_percent, 1 if passed else 0),
    )
    conn.commit()
    return int(cur.lastrowid)


def add_answer(
    conn: sqlite3.Connection,
    submission_id: int,
    question_id: int,
    selected_option_id: Optional[int],
    free_text_answer: Optional[str],
    is_correct: Optional[bool],
) -> None:
    conn.execute(
        """
        INSERT INTO quiz_answers (submission_id, question_id, selected_option_id, free_text_answer, is_correct)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            submission_id,
            question_id,
            selected_option_id,
            free_text_answer,
            None if is_correct is None else (1 if is_correct else 0),
        ),
    )
    conn.commit()
