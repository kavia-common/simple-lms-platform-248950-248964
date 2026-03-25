from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.api.deps import require_roles
from src.api.schemas import UserPublic
from src.db.connection import get_db
from src.repos.users import get_user_by_id, list_users, set_user_active, set_user_roles

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserRolesUpdate(BaseModel):
    roles: list[str] = Field(..., description="Role names to set for user")


class UserActiveUpdate(BaseModel):
    is_active: bool = Field(..., description="Whether the user is active")


@router.get(
    "/users",
    response_model=list[UserPublic],
    summary="List users (admin)",
)
def admin_list_users(
    _: Annotated[UserPublic, Depends(require_roles("admin"))],
) -> list[UserPublic]:
    """List all users."""
    with get_db() as conn:
        rows = list_users(conn)
        return [UserPublic(**r) for r in rows]


@router.put(
    "/users/{user_id}/roles",
    response_model=UserPublic,
    summary="Set user roles (admin)",
)
def admin_set_user_roles(
    user_id: int,
    payload: UserRolesUpdate,
    _: Annotated[UserPublic, Depends(require_roles("admin"))],
) -> UserPublic:
    """Replace user's roles with provided roles."""
    for r in payload.roles:
        if r not in {"admin", "instructor", "student"}:
            raise HTTPException(status_code=400, detail=f"Invalid role: {r}")

    with get_db() as conn:
        if not get_user_by_id(conn, user_id):
            raise HTTPException(status_code=404, detail="User not found")
        set_user_roles(conn, user_id, payload.roles)
        # list_users already computes roles; simplest reuse:
        users = {u["id"]: u for u in list_users(conn)}
        return UserPublic(**users[user_id])


@router.put(
    "/users/{user_id}/active",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Activate/deactivate user (admin)",
)
def admin_set_user_active(
    user_id: int,
    payload: UserActiveUpdate,
    _: Annotated[UserPublic, Depends(require_roles("admin"))],
) -> None:
    """Set user's active flag."""
    with get_db() as conn:
        if not get_user_by_id(conn, user_id):
            raise HTTPException(status_code=404, detail="User not found")
        set_user_active(conn, user_id, payload.is_active)
    return None
