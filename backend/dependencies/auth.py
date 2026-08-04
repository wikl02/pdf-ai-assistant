"""FastAPI 登录认证和角色权限依赖。

路由通过 CurrentUser、AdminUser 或 KnowledgeUser 声明自己的访问边界。
"""

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.security import decode_access_token
from backend.database import get_db
from backend.models.user import User, UserRole
from backend.services.user_service import get_user_by_id


security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态无效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # 前端把 JWT 放在 Authorization: Bearer <token> 请求头中。
    if not credentials:
        raise unauthorized
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise unauthorized from None
    # 每次请求都重新读取用户，确保禁用账号后旧 JWT 也会立即失效。
    user = get_user_by_id(db, user_id)
    if not user or not user.is_active or user.deleted_at is not None:
        raise unauthorized
    return user


def require_roles(*allowed_roles: UserRole) -> Callable:
    """生成一个可复用的角色校验依赖。"""

    allowed_values = {role.value for role in allowed_roles}

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed_values:
            raise HTTPException(status_code=403, detail="当前账号没有执行此操作的权限")
        return current_user

    return dependency


# 路由参数使用这些别名即可同时获得认证后的 User 对象和权限校验。
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[
    User, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN))
]
SuperAdminUser = Annotated[User, Depends(require_roles(UserRole.SUPER_ADMIN))]
KnowledgeUser = Annotated[
    User,
    Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.USER)),
]
