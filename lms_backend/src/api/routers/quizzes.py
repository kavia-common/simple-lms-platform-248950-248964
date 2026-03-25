from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import require_roles
from src.api.schemas import (
    QuizOut,
    QuizQuestionOut,
    QuizQuestionOption,
    QuizSubmissionOut,
    QuizSubmissionRequest,
    UserPublic,
)
from src.db.connection import get_db
from src.repos.enrollment import get_enrollment
from src.repos.quizzes import (
    add_answer,
    create_submission,
    get_correct_option_ids,
    get_next_attempt,
    get_options_for_question,
    get_questions,
    get_quiz,
    list_quizzes_for_course,
)

router = APIRouter(prefix="/api", tags=["quizzes"])


def _quiz_out(row) -> QuizOut:
    return QuizOut(
        id=int(row["id"]),
        course_id=int(row["course_id"]),
        lesson_id=int(row["lesson_id"]) if row["lesson_id"] else None,
        title=row["title"],
        description=row["description"],
        passing_score=int(row["passing_score"]),
        is_published=bool(row["is_published"]),
    )


@router.get(
    "/courses/{course_id}/quizzes",
    response_model=list[QuizOut],
    summary="List quizzes for a course",
)
def list_quizzes(course_id: int) -> list[QuizOut]:
    """List published quizzes for a course."""
    with get_db() as conn:
        rows = list_quizzes_for_course(conn, course_id)
        return [_quiz_out(r) for r in rows]


@router.get(
    "/quizzes/{quiz_id}",
    response_model=QuizOut,
    summary="Get a quiz",
)
def get_quiz_route(quiz_id: int) -> QuizOut:
    """Return a quiz by ID (published only)."""
    with get_db() as conn:
        row = get_quiz(conn, quiz_id)
        if not row:
            raise HTTPException(status_code=404, detail="Quiz not found")
        return _quiz_out(row)


@router.get(
    "/quizzes/{quiz_id}/questions",
    response_model=list[QuizQuestionOut],
    summary="Get quiz questions (with options)",
)
def get_quiz_questions(quiz_id: int) -> list[QuizQuestionOut]:
    """Return questions and options (excluding correctness flags)."""
    with get_db() as conn:
        quiz = get_quiz(conn, quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        questions = get_questions(conn, quiz_id)
        out: list[QuizQuestionOut] = []
        for q in questions:
            opts = get_options_for_question(conn, int(q["id"]))
            out.append(
                QuizQuestionOut(
                    id=int(q["id"]),
                    quiz_id=int(q["quiz_id"]),
                    prompt=q["prompt"],
                    question_type=q["question_type"],
                    sort_order=int(q["sort_order"]),
                    options=[
                        QuizQuestionOption(
                            id=int(o["id"]),
                            option_text=o["option_text"],
                            sort_order=int(o["sort_order"]),
                        )
                        for o in opts
                    ],
                )
            )
        return out


@router.post(
    "/quizzes/{quiz_id}/submit",
    response_model=QuizSubmissionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a quiz attempt",
    description="Requires enrollment in the quiz's course. Auto-grades single-choice questions.",
)
def submit_quiz(
    quiz_id: int,
    payload: QuizSubmissionRequest,
    user: Annotated[UserPublic, Depends(require_roles("admin", "instructor", "student"))],
) -> QuizSubmissionOut:
    """Submit answers, calculate score, persist submission and answers."""
    with get_db() as conn:
        quiz = get_quiz(conn, quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        course_id = int(quiz["course_id"])
        enr = get_enrollment(conn, user.id, course_id)
        if not enr:
            raise HTTPException(status_code=403, detail="Not enrolled")

        questions = get_questions(conn, quiz_id)
        if not questions:
            raise HTTPException(status_code=400, detail="Quiz has no questions")

        correct_count = 0
        graded_count = 0

        # Evaluate
        for q in questions:
            qid = int(q["id"])
            qtype = q["question_type"]
            ans = payload.answers.get(qid)

            is_correct: bool | None = None
            selected_option_id: int | None = None
            free_text: str | None = None

            if qtype == "single_choice":
                graded_count += 1
                if isinstance(ans, int):
                    selected_option_id = ans
                    correct_ids = get_correct_option_ids(conn, qid)
                    is_correct = ans in correct_ids
                else:
                    is_correct = False
            elif qtype == "free_text":
                # Not auto-graded in this simple implementation
                free_text = ans if isinstance(ans, str) else None
                is_correct = None
            else:
                # For now treat unknown as ungraded
                is_correct = None

            if is_correct is True:
                correct_count += 1

        score = int(round((correct_count / max(graded_count, 1)) * 100))
        passed = score >= int(quiz["passing_score"])

        attempt = get_next_attempt(conn, quiz_id, user.id)
        submission_id = create_submission(conn, quiz_id, user.id, attempt, score, passed)

        # Persist answers
        for q in questions:
            qid = int(q["id"])
            qtype = q["question_type"]
            ans = payload.answers.get(qid)

            selected_option_id = ans if isinstance(ans, int) else None
            free_text = ans if isinstance(ans, str) else None

            is_correct: bool | None = None
            if qtype == "single_choice":
                correct_ids = get_correct_option_ids(conn, qid)
                is_correct = bool(selected_option_id and selected_option_id in correct_ids)

            add_answer(
                conn,
                submission_id=submission_id,
                question_id=qid,
                selected_option_id=selected_option_id,
                free_text_answer=free_text,
                is_correct=is_correct,
            )

        # Return
        cur = conn.execute("SELECT * FROM quiz_submissions WHERE id = ?", (submission_id,))
        row = cur.fetchone()
        return QuizSubmissionOut(
            id=int(row["id"]),
            quiz_id=int(row["quiz_id"]),
            user_id=int(row["user_id"]),
            attempt=int(row["attempt"]),
            score_percent=int(row["score_percent"]) if row["score_percent"] is not None else None,
            passed=bool(row["passed"]) if row["passed"] is not None else None,
            submitted_at=datetime.fromisoformat(row["submitted_at"]),
        )
