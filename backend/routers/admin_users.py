from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies.auth import AdminUser
from backend.schemas.admin_user import (
    UserPasswordReset,
    UserRoleUpdate,
    UserStatusUpdate,
)
from backend.schemas.management import MessageResponse
from backend.schemas.user import UserResponse
from backend.services.admin_user_service import (
    reset_user_password,
    update_user_role,
    update_user_status,
)


router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


@router.patch("/{user_id}/status", response_model=UserResponse)
def change_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    return UserResponse.model_validate(
        update_user_status(db, user_id, payload.is_active, current_user)
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
def change_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    return UserResponse.model_validate(
        update_user_role(db, user_id, payload.role, current_user)
    )


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
def change_user_password(
    user_id: int,
    payload: UserPasswordReset,
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    reset_user_password(db, user_id, payload.password)
    return MessageResponse(message="密码已重置")
