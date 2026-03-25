from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import require_roles
from src.api.schemas import EnrollmentOut, ProgressOut, ProgressUpdate, UserPublic
from src.db.connection import get_db
from src.repos.courses import get_course_by_id, get_lesson_by_id
from src.repos.enrollment import (
    enroll_user,
    get_enrollment,
    get_progress_for_course,
    list_enrollments_for_user,
    set_progress,
)

router = APIRouter(prefix="/api", tags=["enrollment"])


def _enrollment_out(row) -> EnrollmentOut:
    return EnrollmentOut(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        course_id=int(row["course_id"]),
        status=row["status"],
        enrolled_at=datetime.fromisoformat(row["enrolled_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"])
        if row["completed_at"]
        else None,
    )


def _progress_out(row) -> ProgressOut:
    return ProgressOut(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        course_id=int(row["course_id"]),
        lesson_id=int(row["lesson_id"]),
        status=row["status"],
        progress_percent=int(row["progress_percent"]),
        started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
        completed_at=datetime.fromisoformat(row["completed_at"])
        if row["completed_at"]
        else None,
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


@router.post(
    "/courses/{course_id}/enroll",
    response_model=EnrollmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll in a course (student/instructor/admin)",
)
def enroll(
    course_id: int,
    user: Annotated[UserPublic, Depends(require_roles("admin", "instructor", "student"))],
) -> EnrollmentOut:
    """Enroll the current user in a course."""
    with get_db() as conn:
        course = get_course_by_id(conn, course_id)
        if not course or not bool(course["is_published"]):
            raise HTTPException(status_code=404, detail="Course not found")
        enroll_user(conn, user.id, course_id)
        row = get_enrollment(conn, user.id, course_id)
        if not row:
            raise HTTPException(status_code=500, detail="Failed to enroll")
        return _enrollment_out(row)


@router.get(
    "/me/enrollments",
    response_model=list[EnrollmentOut],
    summary="List my enrollments",
)
def my_enrollments(
    user: Annotated[UserPublic, Depends(require_roles("admin", "instructor", "student"))],
) -> list[EnrollmentOut]:
    """List enrollments for the current user."""
    with get_db() as conn:
        rows = list_enrollments_for_user(conn, user.id)
        return [_enrollment_out(r) for r in rows]


@router.get(
    "/courses/{course_id}/progress",
    response_model=list[ProgressOut],
    summary="Get my progress for a course",
)
def my_progress_for_course(
    course_id: int,
    user: Annotated[UserPublic, Depends(require_roles("admin", "instructor", "student"))],
) -> list[ProgressOut]:
    """Return lesson progress for the current user in a given course."""
    with get_db() as conn:
        course = get_course_by_id(conn, course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        enr = get_enrollment(conn, user.id, course_id)
        if not enr:
            raise HTTPException(status_code=403, detail="Not enrolled")

        rows = get_progress_for_course(conn, user.id, course_id)
        return [_progress_out(r) for r in rows]


@router.put(
    "/lessons/{lesson_id}/progress",
    response_model=ProgressOut,
    summary="Update my lesson progress",
)
def update_my_lesson_progress(
    lesson_id: int,
    payload: ProgressUpdate,
    user: Annotated[UserPublic, Depends(require_roles("admin", "instructor", "student"))],
) -> ProgressOut:
    """Upsert progress for a lesson (requires enrollment in the lesson's course)."""
    with get_db() as conn:
        lesson = get_lesson_by_id(conn, lesson_id)
        if not lesson or not bool(lesson["is_published"]):
            raise HTTPException(status_code=404, detail="Lesson not found")

        course_id = int(lesson["course_id"])
        enr = get_enrollment(conn, user.id, course_id)
        if not enr:
            raise HTTPException(status_code=403, detail="Not enrolled")

        row = set_progress(
            conn,
            user_id=user.id,
            course_id=course_id,
            lesson_id=lesson_id,
            status=payload.status,
            progress_percent=payload.progress_percent,
        )
        return _progress_out(row)
