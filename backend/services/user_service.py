import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.security import hash_password
from backend.models.user import User, UserRole
from backend.schemas.user import UserCreate


logger = logging.getLogger("pdf_ai_assistant.users")


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


def create_user(db: Session, payload: UserCreate) -> User:
    username = payload.username.strip()
    if db.scalar(select(User).where(User.username == username)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip() if payload.display_name else None,
        role=payload.role.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_bootstrap_admin(db: Session) -> None:
    username = settings.bootstrap_admin_username
    password = settings.bootstrap_admin_password
    if not username or not password:
        logger.warning("APP_USERNAME or APP_PASSWORD missing; bootstrap administrator was not created")
        return
    existing = db.scalar(select(User).where(User.username == username.strip()))
    if existing:
        if existing.role != UserRole.ADMIN.value:
            existing.role = UserRole.ADMIN.value
            db.commit()
        return
    admin = User(
        username=username.strip(),
        password_hash=hash_password(password),
        display_name="系统管理员",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    logger.info("bootstrap administrator created username=%s", admin.username)
