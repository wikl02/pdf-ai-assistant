import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.security import create_access_token
from backend.database import get_db
from backend.dependencies.auth import CurrentUser
from backend.schemas.auth import LoginRequest, LoginResponse
from backend.schemas.user import UserResponse
from backend.services.auth_service import authenticate_user


logger = logging.getLogger("pdf_ai_assistant.auth")
router = APIRouter(tags=["auth"])


@router.post("/api/auth/login", response_model=LoginResponse)
@router.post("/login", response_model=LoginResponse, include_in_schema=False)
def login(request: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> LoginResponse:
    user = authenticate_user(db, request.username, request.password)
    if not user:
        logger.warning("login failed username=%s", request.username)
        raise HTTPException(status_code=401, detail="用户名或密码不正确")
    token, expires_in = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    logger.info("login success username=%s", user.username)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
