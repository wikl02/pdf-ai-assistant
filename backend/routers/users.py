from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.core.audit import audit_event
from backend.dependencies.auth import AdminUser
from backend.schemas.user import UserCreate, UserResponse
from backend.services.user_service import create_user, list_users


router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


@router.get("", response_model=list[UserResponse])
def get_users(
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[UserResponse]:
    return [UserResponse.model_validate(user) for user in list_users(db)]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def add_user(
    payload: UserCreate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    user = create_user(db, payload)
    audit_event(
        "user_created",
        actor_id=current_user.id,
        actor_name=current_user.username,
        target_user_id=user.id,
        target_role=user.role,
    )
    return UserResponse.model_validate(user)
