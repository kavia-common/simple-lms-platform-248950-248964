from __future__ import annotations

from typing import Annotated, Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.schemas import UserPublic
from src.core.security import decode_access_token
from src.db.connection import get_db
from src.repos.users import get_user_by_id, get_user_roles

_security = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _forbidden(detail: str = "Not enough permissions") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


# PUBLIC_INTERFACE
def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_security)],
) -> UserPublic:
    """Return the currently authenticated user based on Bearer JWT."""
    if credentials is None or not credentials.credentials:
        raise _unauthorized()

    token = credentials.credentials
    try:
        sub = decode_access_token(token)
    except jwt.PyJWTError:
        raise _unauthorized("Invalid or expired token")

    user_id = sub.get("user_id")
    if not isinstance(user_id, int):
        raise _unauthorized("Invalid token payload")

    with get_db() as conn:
        user_row = get_user_by_id(conn, user_id)
        if not user_row:
            raise _unauthorized("User not found")
        roles = get_user_roles(conn, user_id)

        return UserPublic(
            id=int(user_row["id"]),
            email=user_row["email"],
            username=user_row["username"],
            full_name=user_row["full_name"],
            is_active=bool(user_row["is_active"]),
            roles=roles,
        )


# PUBLIC_INTERFACE
def require_roles(*required: str) -> Callable:
    """Dependency factory to enforce that current user has one of required roles."""

    def _dep(user: Annotated[UserPublic, Depends(get_current_user)]) -> UserPublic:
        if not user.is_active:
            raise _forbidden("User is inactive")
        if not any(r in user.roles for r in required):
            raise _forbidden()
        return user

    return _dep
