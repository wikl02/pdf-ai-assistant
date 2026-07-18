from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.core.security import hash_password
from backend.models.user import User, UserRole


def _user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def update_user_status(
    db: Session, user_id: int, is_active: bool, current_user: User
) -> User:
    user = _user_or_404(db, user_id)
    if user.id == current_user.id and not is_active:
        raise HTTPException(status_code=400, detail="不能禁用当前登录账号")
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def update_user_role(
    db: Session, user_id: int, role: UserRole, current_user: User
) -> User:
    user = _user_or_404(db, user_id)
    if user.id == current_user.id and role != UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="不能降低当前管理员账号的角色")
    user.role = role.value
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(db: Session, user_id: int, password: str) -> User:
    user = _user_or_404(db, user_id)
    user.password_hash = hash_password(password)
    db.commit()
    db.refresh(user)
    return user
