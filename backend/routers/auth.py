"""登录和当前用户接口。"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.core.security import create_access_token
from backend.core.audit import audit_event
from backend.database import get_db
from backend.dependencies.auth import CurrentUser
from backend.schemas.auth import LoginRequest, LoginResponse
from backend.schemas.user import UserResponse
from backend.services.auth_service import authenticate_user


logger = logging.getLogger("pdf_ai_assistant.auth")
router = APIRouter(tags=["auth"])


@router.post("/api/auth/login", response_model=LoginResponse)
@router.post("/login", response_model=LoginResponse, include_in_schema=False)
def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    client_ip = request.client.host if request.client else None
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        audit_event(
            "login",
            db=db,
            outcome="failed",
            actor_name=payload.username.strip(),
            client_ip=client_ip,
        )
        raise HTTPException(status_code=401, detail="用户名或密码不正确")
    # 登录成功后签发 JWT，后续请求无需重复提交用户名和密码。
    token, expires_in = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
    )
    audit_event(
        "login",
        db=db,
        actor_id=user.id,
        actor_name=user.username,
        client_ip=client_ip,
        role=user.role,
    )
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: CurrentUser) -> UserResponse:
    # /me 同时用于刷新页面后恢复前端登录状态，并确认账号仍处于启用状态。
    return UserResponse.model_validate(current_user)
