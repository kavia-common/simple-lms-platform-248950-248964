from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from src.api.deps import get_current_user
from src.api.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)
from src.core.security import create_access_token, verify_password
from src.db.connection import get_db
from src.repos.users import (
    assign_role,
    create_user,
    get_user_by_email,
    get_user_roles,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account. Default role is student (or instructor if requested).",
)
def register(payload: RegisterRequest) -> UserPublic:
    """Register a user and return the public user profile."""
    with get_db() as conn:
        existing = get_user_by_email(conn, payload.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user_id = create_user(
            conn,
            email=str(payload.email),
            username=payload.username,
            full_name=payload.full_name,
            password=payload.password,
        )
        assign_role(conn, user_id, payload.role)

        user_row = get_user_by_email(conn, payload.email)
        roles = get_user_roles(conn, user_id)

        return UserPublic(
            id=int(user_row["id"]),
            email=user_row["email"],
            username=user_row["username"],
            full_name=user_row["full_name"],
            is_active=bool(user_row["is_active"]),
            roles=roles,
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate user and return JWT access token.",
)
def login(payload: LoginRequest) -> TokenResponse:
    """Authenticate via email/password and return access token."""
    with get_db() as conn:
        user_row = get_user_by_email(conn, str(payload.email))
        if not user_row:
            raise HTTPException(status_code=400, detail="Invalid credentials")
        if not bool(user_row["is_active"]):
            raise HTTPException(status_code=403, detail="User is inactive")

        password_hash = user_row["password_hash"] or ""
        if not password_hash or not verify_password(payload.password, password_hash):
            raise HTTPException(status_code=400, detail="Invalid credentials")

        roles = get_user_roles(conn, int(user_row["id"]))
        token = create_access_token(
            {
                "user_id": int(user_row["id"]),
                "email": user_row["email"],
                "roles": roles,
            }
        )
        return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Get current user",
    description="Return the current authenticated user profile.",
)
def me(user: UserPublic = get_current_user) -> UserPublic:  # type: ignore[assignment]
    """Return current user."""
    return user
