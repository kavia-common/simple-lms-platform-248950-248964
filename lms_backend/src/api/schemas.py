from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")


class Role(BaseModel):
    name: str = Field(..., description="Role name (admin|instructor|student)")
    description: Optional[str] = Field(None, description="Role description")


class UserPublic(BaseModel):
    id: int = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    username: str = Field(..., description="Username")
    full_name: Optional[str] = Field(None, description="Full name")
    is_active: bool = Field(..., description="Whether the user is active")
    roles: list[str] = Field(default_factory=list, description="Role names")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Email for the account")
    username: str = Field(..., min_length=3, max_length=64, description="Username")
    full_name: Optional[str] = Field(None, description="Full name")
    password: str = Field(..., min_length=6, max_length=256, description="Password")
    role: Literal["student", "instructor"] = Field(
        "student",
        description="Requested initial role; admin can promote/demote later",
    )


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., description="Password")


class CourseBase(BaseModel):
    slug: str = Field(..., min_length=3, max_length=128, description="Course slug")
    title: str = Field(..., min_length=1, max_length=200, description="Course title")
    description: Optional[str] = Field(None, description="Course description")
    level: Optional[str] = Field(None, description="Course level")
    is_published: bool = Field(True, description="Published flag")


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Course title")
    description: Optional[str] = Field(None, description="Course description")
    level: Optional[str] = Field(None, description="Course level")
    is_published: Optional[bool] = Field(None, description="Published flag")


class CourseOut(CourseBase):
    id: int = Field(..., description="Course ID")
    created_by_user_id: Optional[int] = Field(None, description="Owner instructor user id")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")


class LessonBase(BaseModel):
    slug: str = Field(..., min_length=1, max_length=128, description="Lesson slug")
    title: str = Field(..., min_length=1, max_length=200, description="Lesson title")
    content_type: Literal["text", "video", "link"] = Field(
        "text", description="Lesson content type"
    )
    content_text: Optional[str] = Field(None, description="Text content (if content_type=text)")
    video_url: Optional[str] = Field(None, description="Video URL (if content_type=video)")
    resource_url: Optional[str] = Field(None, description="Resource URL (if content_type=link)")
    sort_order: int = Field(0, description="Ordering within course")
    estimated_minutes: Optional[int] = Field(None, description="Estimated minutes")
    is_published: bool = Field(True, description="Published flag")


class LessonCreate(LessonBase):
    pass


class LessonUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Lesson title")
    content_type: Optional[Literal["text", "video", "link"]] = Field(
        None, description="Lesson content type"
    )
    content_text: Optional[str] = Field(None, description="Text content")
    video_url: Optional[str] = Field(None, description="Video URL")
    resource_url: Optional[str] = Field(None, description="Resource URL")
    sort_order: Optional[int] = Field(None, description="Ordering")
    estimated_minutes: Optional[int] = Field(None, description="Estimated minutes")
    is_published: Optional[bool] = Field(None, description="Published flag")


class LessonOut(LessonBase):
    id: int = Field(..., description="Lesson ID")
    course_id: int = Field(..., description="Course ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")


class EnrollmentOut(BaseModel):
    id: int = Field(..., description="Enrollment ID")
    user_id: int = Field(..., description="User ID")
    course_id: int = Field(..., description="Course ID")
    status: str = Field(..., description="Enrollment status")
    enrolled_at: datetime = Field(..., description="Enrolled at")
    completed_at: Optional[datetime] = Field(None, description="Completed at")


class ProgressUpdate(BaseModel):
    status: Literal["not_started", "in_progress", "completed"] = Field(
        ..., description="Lesson progress status"
    )
    progress_percent: int = Field(..., ge=0, le=100, description="Progress percent 0..100")


class ProgressOut(BaseModel):
    id: int = Field(..., description="Progress record ID")
    user_id: int = Field(..., description="User ID")
    course_id: int = Field(..., description="Course ID")
    lesson_id: int = Field(..., description="Lesson ID")
    status: str = Field(..., description="Status")
    progress_percent: int = Field(..., description="Percent")
    started_at: Optional[datetime] = Field(None, description="Started at")
    completed_at: Optional[datetime] = Field(None, description="Completed at")
    updated_at: datetime = Field(..., description="Updated at")


class QuizOut(BaseModel):
    id: int = Field(..., description="Quiz ID")
    course_id: int = Field(..., description="Course ID")
    lesson_id: Optional[int] = Field(None, description="Lesson ID (optional)")
    title: str = Field(..., description="Quiz title")
    description: Optional[str] = Field(None, description="Quiz description")
    passing_score: int = Field(..., description="Passing score percent")
    is_published: bool = Field(..., description="Published flag")


class QuizQuestionOption(BaseModel):
    id: int = Field(..., description="Option ID")
    option_text: str = Field(..., description="Option text")
    sort_order: int = Field(..., description="Option sort order")


class QuizQuestionOut(BaseModel):
    id: int = Field(..., description="Question ID")
    quiz_id: int = Field(..., description="Quiz ID")
    prompt: str = Field(..., description="Prompt")
    question_type: str = Field(..., description="Question type")
    sort_order: int = Field(..., description="Sort order")
    options: list[QuizQuestionOption] = Field(default_factory=list, description="Options")


class QuizSubmissionRequest(BaseModel):
    answers: dict[int, int | str | None] = Field(
        ...,
        description=(
            "Mapping of question_id -> selected_option_id (int) for choice questions, "
            "or free_text (str) for free text. Null allowed."
        ),
    )


class QuizSubmissionOut(BaseModel):
    id: int = Field(..., description="Submission ID")
    quiz_id: int = Field(..., description="Quiz ID")
    user_id: int = Field(..., description="User ID")
    attempt: int = Field(..., description="Attempt number")
    score_percent: Optional[int] = Field(None, description="Score percent")
    passed: Optional[bool] = Field(None, description="Whether passed")
    submitted_at: datetime = Field(..., description="Submitted at")
