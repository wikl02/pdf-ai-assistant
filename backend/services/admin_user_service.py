from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.security import hash_password
from backend.models.user import User, UserRole


def _user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _is_super_admin(user: User) -> bool:
    return user.role == UserRole.SUPER_ADMIN.value


def _assert_can_manage(current_user: User, target_user: User) -> None:
    if _is_super_admin(current_user):
        return
    if target_user.role != UserRole.USER.value:
        raise HTTPException(status_code=403, detail="普通管理员不能操作管理员账号")


def _active_super_admin_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.role == UserRole.SUPER_ADMIN.value,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        or 0
    )


def _protect_last_super_admin(db: Session, target_user: User) -> None:
    if (
        target_user.role == UserRole.SUPER_ADMIN.value
        and target_user.is_active
        and target_user.deleted_at is None
        and _active_super_admin_count(db) <= 1
    ):
        raise HTTPException(status_code=400, detail="系统必须保留至少一个可用的超级管理员")


def update_user_status(
    db: Session, user_id: int, is_active: bool, current_user: User
) -> User:
    user = _user_or_404(db, user_id)
    _assert_can_manage(current_user, user)
    if user.deleted_at is not None:
        raise HTTPException(status_code=409, detail="已删除用户需要先恢复")
    if user.id == current_user.id and not is_active:
        raise HTTPException(status_code=400, detail="不能禁用当前登录账号")
    if not is_active:
        _protect_last_super_admin(db, user)
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def update_user_role(
    db: Session, user_id: int, role: UserRole, current_user: User
) -> User:
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="只有超级管理员可以修改用户角色")
    user = _user_or_404(db, user_id)
    if user.deleted_at is not None:
        raise HTTPException(status_code=409, detail="已删除用户需要先恢复")
    if user.id == current_user.id and role.value != user.role:
        raise HTTPException(status_code=400, detail="不能修改当前登录账号的角色")
    if user.role == UserRole.SUPER_ADMIN.value and role != UserRole.SUPER_ADMIN:
        _protect_last_super_admin(db, user)
    user.role = role.value
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(
    db: Session, user_id: int, password: str, current_user: User
) -> User:
    user = _user_or_404(db, user_id)
    _assert_can_manage(current_user, user)
    if user.deleted_at is not None:
        raise HTTPException(status_code=409, detail="不能重置已删除用户的密码")
    user.password_hash = hash_password(password)
    db.commit()
    db.refresh(user)
    return user


def soft_delete_user(db: Session, user_id: int, current_user: User) -> User:
    user = _user_or_404(db, user_id)
    _assert_can_manage(current_user, user)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    if user.deleted_at is not None:
        raise HTTPException(status_code=409, detail="用户已经被删除")
    _protect_last_super_admin(db, user)
    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)
    user.deleted_by_id = current_user.id
    db.commit()
    db.refresh(user)
    return user


def restore_user(db: Session, user_id: int, current_user: User) -> User:
    user = _user_or_404(db, user_id)
    _assert_can_manage(current_user, user)
    if user.deleted_at is None:
        raise HTTPException(status_code=409, detail="用户未被删除")
    user.deleted_at = None
    user.deleted_by_id = None
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user
