from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import get_current_user, require_roles
from src.api.schemas import (
    CourseCreate,
    CourseOut,
    CourseUpdate,
    LessonCreate,
    LessonOut,
    LessonUpdate,
    UserPublic,
)
from src.db.connection import get_db
from src.repos.courses import (
    create_course,
    create_lesson,
    delete_course,
    delete_lesson,
    get_course_by_id,
    get_course_by_slug,
    get_lesson_by_id,
    list_courses,
    list_lessons,
    update_course,
    update_lesson,
)

router = APIRouter(prefix="/api/courses", tags=["courses"])


def _course_row_to_out(row) -> CourseOut:
    return CourseOut(
        id=int(row["id"]),
        slug=row["slug"],
        title=row["title"],
        description=row["description"],
        level=row["level"],
        is_published=bool(row["is_published"]),
        created_by_user_id=row["created_by_user_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _lesson_row_to_out(row) -> LessonOut:
    return LessonOut(
        id=int(row["id"]),
        course_id=int(row["course_id"]),
        slug=row["slug"],
        title=row["title"],
        content_type=row["content_type"],
        content_text=row["content_text"],
        video_url=row["video_url"],
        resource_url=row["resource_url"],
        sort_order=int(row["sort_order"]),
        estimated_minutes=row["estimated_minutes"],
        is_published=bool(row["is_published"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


@router.get(
    "",
    response_model=list[CourseOut],
    summary="List courses",
    description="List published courses for students. Admin/instructor can include unpublished via role.",
)
def get_courses(user: Annotated[UserPublic | None, Depends(get_current_user)] = None) -> list[CourseOut]:
    """List courses. If authenticated and role is instructor/admin, include unpublished."""
    include_unpublished = False
    if user and any(r in user.roles for r in ["admin", "instructor"]):
        include_unpublished = True

    with get_db() as conn:
        rows = list_courses(conn, include_unpublished=include_unpublished)
        return [_course_row_to_out(r) for r in rows]


@router.get(
    "/{course_slug}",
    response_model=CourseOut,
    summary="Get course by slug",
)
def get_course(course_slug: str) -> CourseOut:
    """Fetch a course by slug."""
    with get_db() as conn:
        row = get_course_by_slug(conn, course_slug)
        if not row:
            raise HTTPException(status_code=404, detail="Course not found")
        if not bool(row["is_published"]):
            raise HTTPException(status_code=404, detail="Course not found")
        return _course_row_to_out(row)


@router.post(
    "",
    response_model=CourseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create course (instructor/admin)",
)
def create_course_route(
    payload: CourseCreate,
    user: Annotated[UserPublic, Depends(require_roles("admin", "instructor"))],
) -> CourseOut:
    """Create a new course owned by the current instructor/admin."""
    with get_db() as conn:
        if get_course_by_slug(conn, payload.slug):
            raise HTTPException(status_code=400, detail="Course slug already exists")
        course_id = create_course(
            conn,
            slug=payload.slug,
            title=payload.title,
            description=payload.description,
            level=payload.level,
            is_published=payload.is_published,
            created_by_user_id=user.id,
        )
        row = get_course_by_id(conn, course_id)
        return _course_row_to_out(row)


@router.patch(
    "/{course_id}",
    response_model=CourseOut,
    summary="Update course (instructor/admin)",
)
def update_course_route(
    course_id: int,
    payload: CourseUpdate,
    user: Annotated[UserPublic, Depends(require_roles("admin", "instructor"))],
) -> CourseOut:
    """Update course; instructor can only update own course unless admin."""
    with get_db() as conn:
        row = get_course_by_id(conn, course_id)
        if not row:
            raise HTTPException(status_code=404, detail="Course not found")
        if "admin" not in user.roles and row["created_by_user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not course owner")

        update_course(
            conn,
            course_id=course_id,
            title=payload.title,
            description=payload.description,
            level=payload.level,
            is_published=payload.is_published,
        )
        updated = get_course_by_id(conn, course_id)
        return _course_row_to_out(updated)


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete course (instructor/admin)",
)
def delete_course_route(
    course_id: int,
    user: Annotated[UserPublic, Depends(require_roles("admin", "instructor"))],
) -> None:
    """Delete course; instructor can only delete own course unless admin."""
    with get_db() as conn:
        row = get_course_by_id(conn, course_id)
        if not row:
            raise HTTPException(status_code=404, detail="Course not found")
        if "admin" not in user.roles and row["created_by_user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not course owner")
        delete_course(conn, course_id)
    return None


@router.get(
    "/{course_slug}/lessons",
    response_model=list[LessonOut],
    summary="List lessons for a course",
)
def get_course_lessons(
    course_slug: str,
    user: Annotated[UserPublic | None, Depends(get_current_user)] = None,
) -> list[LessonOut]:
    """List lessons; published only unless instructor/admin."""
    include_unpublished = False
    if user and any(r in user.roles for r in ["admin", "instructor"]):
        include_unpublished = True

    with get_db() as conn:
        course = get_course_by_slug(conn, course_slug)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        if not include_unpublished and not bool(course["is_published"]):
            raise HTTPException(status_code=404, detail="Course not found")

        lessons = list_lessons(conn, int(course["id"]), include_unpublished=include_unpublished)
        return [_lesson_row_to_out(r) for r in lessons]


@router.post(
    "/{course_id}/lessons",
    response_model=LessonOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create lesson (instructor/admin)",
)
def create_lesson_route(
    course_id: int,
    payload: LessonCreate,
    user: Annotated[UserPublic, Depends(require_roles("admin", "instructor"))],
) -> LessonOut:
    """Create lesson under a course."""
    with get_db() as conn:
        course = get_course_by_id(conn, course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        if "admin" not in user.roles and course["created_by_user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not course owner")

        lesson_id = create_lesson(conn, course_id=course_id, **payload.model_dump())
        row = get_lesson_by_id(conn, lesson_id)
        return _lesson_row_to_out(row)


@router.patch(
    "/lessons/{lesson_id}",
    response_model=LessonOut,
    summary="Update lesson (instructor/admin)",
)
def update_lesson_route(
    lesson_id: int,
    payload: LessonUpdate,
    user: Annotated[UserPublic, Depends(require_roles("admin", "instructor"))],
) -> LessonOut:
    """Update lesson; instructor must own the parent course unless admin."""
    with get_db() as conn:
        lesson = get_lesson_by_id(conn, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        course = get_course_by_id(conn, int(lesson["course_id"]))
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        if "admin" not in user.roles and course["created_by_user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not course owner")

        update_lesson(conn, lesson_id, **payload.model_dump())
        updated = get_lesson_by_id(conn, lesson_id)
        return _lesson_row_to_out(updated)


@router.delete(
    "/lessons/{lesson_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lesson (instructor/admin)",
)
def delete_lesson_route(
    lesson_id: int,
    user: Annotated[UserPublic, Depends(require_roles("admin", "instructor"))],
) -> None:
    """Delete a lesson."""
    with get_db() as conn:
        lesson = get_lesson_by_id(conn, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        course = get_course_by_id(conn, int(lesson["course_id"]))
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        if "admin" not in user.roles and course["created_by_user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Not course owner")

        delete_lesson(conn, lesson_id)
    return None
