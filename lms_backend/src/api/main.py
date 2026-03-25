from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings

from src.api.routers.admin import router as admin_router
from src.api.routers.auth import router as auth_router
from src.api.routers.courses import router as courses_router
from src.api.routers.enrollment import router as enrollment_router
from src.api.routers.quizzes import router as quizzes_router

openapi_tags = [
    {"name": "auth", "description": "Authentication endpoints (register/login/me)."},
    {"name": "courses", "description": "Course catalog and instructor CRUD for courses/lessons."},
    {"name": "enrollment", "description": "Enrollment and lesson progress tracking."},
    {"name": "quizzes", "description": "Optional quizzes: questions and submissions."},
    {"name": "admin", "description": "Admin-only user and role management."},
]

app = FastAPI(
    title="Simple LMS Backend API",
    description=(
        "FastAPI backend for a simple Learning Management System (LMS). "
        "Provides JWT auth, role-based access control (RBAC), course/lesson management, "
        "enrollment, progress tracking, quizzes, and admin endpoints."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["auth"])
def health_check():
    """Health check endpoint.

    Returns:
        A JSON message confirming the server is running.
    """
    return {"message": "Healthy"}


app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(enrollment_router)
app.include_router(quizzes_router)
app.include_router(admin_router)
