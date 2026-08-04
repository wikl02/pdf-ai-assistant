"""用户登录校验服务。"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.security import verify_password
from backend.models.user import User


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.username == username.strip()))
    # 统一返回 None，不向调用方暴露“账号不存在”和“密码错误”的区别。
    if (
        not user
        or not user.is_active
        or user.deleted_at is not None
        or not verify_password(password, user.password_hash)
    ):
        return None
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user
