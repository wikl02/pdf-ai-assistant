"""Department membership and object-level knowledge-base permissions."""

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.access import (
    Department,
    KnowledgeBaseDepartmentPermission,
    KnowledgeBaseRolePermission,
    KnowledgeBaseUserPermission,
    PermissionLevel,
    UserDepartment,
)
from backend.models.knowledge import KnowledgeBase
from backend.models.user import User, UserRole
from backend.schemas.access_control import DepartmentCreate, DepartmentUpdate


PERMISSION_RANK = {
    PermissionLevel.QUERY.value: 1,
    PermissionLevel.CONTRIBUTE.value: 2,
    PermissionLevel.MANAGE.value: 3,
}


def _knowledge_base_or_404(db: Session, knowledge_base_id: int) -> KnowledgeBase:
    knowledge_base = db.get(KnowledgeBase, knowledge_base_id)
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return knowledge_base


def _user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def _department_or_404(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")
    return department


def list_departments(db: Session) -> list[Department]:
    return list(db.scalars(select(Department).order_by(Department.name)))


def create_department(db: Session, payload: DepartmentCreate) -> Department:
    duplicate = db.scalar(
        select(Department).where(
            (Department.name == payload.name) | (Department.code == payload.code)
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="部门名称或编码已存在")
    department = Department(name=payload.name, code=payload.code, is_active=True)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


def update_department(
    db: Session, department_id: int, payload: DepartmentUpdate
) -> Department:
    department = _department_or_404(db, department_id)
    if payload.name is not None:
        department.name = payload.name
    if payload.code is not None:
        department.code = payload.code
    if payload.is_active is not None:
        department.is_active = payload.is_active
    duplicate = db.scalar(
        select(Department).where(
            Department.id != department.id,
            (Department.name == department.name) | (Department.code == department.code),
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="部门名称或编码已存在")
    db.commit()
    db.refresh(department)
    return department


def list_user_departments(db: Session, user_id: int) -> list[Department]:
    _user_or_404(db, user_id)
    return list(
        db.scalars(
            select(Department)
            .join(UserDepartment, UserDepartment.department_id == Department.id)
            .where(UserDepartment.user_id == user_id)
            .order_by(Department.name)
        )
    )


def replace_user_departments(
    db: Session, user_id: int, department_ids: list[int]
) -> list[Department]:
    _user_or_404(db, user_id)
    unique_ids = sorted(set(department_ids))
    departments = (
        list(db.scalars(select(Department).where(Department.id.in_(unique_ids))))
        if unique_ids
        else []
    )
    if len(departments) != len(unique_ids):
        raise HTTPException(status_code=400, detail="包含不存在的部门")

    for membership in db.scalars(
        select(UserDepartment).where(UserDepartment.user_id == user_id)
    ):
        db.delete(membership)
    for department_id in unique_ids:
        db.add(UserDepartment(user_id=user_id, department_id=department_id))
    db.commit()
    return sorted(departments, key=lambda item: item.name)


def accessible_knowledge_base_ids(db: Session, user: User) -> set[int] | None:
    """Return None for unrestricted administrators, otherwise authorized IDs."""

    if user.role in {UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value}:
        return None

    direct_ids = set(
        db.scalars(
            select(KnowledgeBaseUserPermission.knowledge_base_id).where(
                KnowledgeBaseUserPermission.user_id == user.id
            )
        )
    )
    role_ids = set(
        db.scalars(
            select(KnowledgeBaseRolePermission.knowledge_base_id).where(
                KnowledgeBaseRolePermission.role == user.role
            )
        )
    )
    department_ids = set(
        db.scalars(
            select(KnowledgeBaseDepartmentPermission.knowledge_base_id)
            .join(
                UserDepartment,
                UserDepartment.department_id
                == KnowledgeBaseDepartmentPermission.department_id,
            )
            .join(
                Department,
                Department.id == KnowledgeBaseDepartmentPermission.department_id,
            )
            .where(UserDepartment.user_id == user.id, Department.is_active.is_(True))
        )
    )
    return direct_ids | role_ids | department_ids


def effective_permission(
    db: Session, user: User, knowledge_base_id: int
) -> PermissionLevel | None:
    if user.role in {UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value}:
        return PermissionLevel.MANAGE

    permissions: list[str] = []
    direct = db.scalar(
        select(KnowledgeBaseUserPermission.permission).where(
            KnowledgeBaseUserPermission.knowledge_base_id == knowledge_base_id,
            KnowledgeBaseUserPermission.user_id == user.id,
        )
    )
    if direct:
        permissions.append(direct)
    role_grant = db.scalar(
        select(KnowledgeBaseRolePermission.permission).where(
            KnowledgeBaseRolePermission.knowledge_base_id == knowledge_base_id,
            KnowledgeBaseRolePermission.role == user.role,
        )
    )
    if role_grant:
        permissions.append(role_grant)
    permissions.extend(
        db.scalars(
            select(KnowledgeBaseDepartmentPermission.permission)
            .join(
                UserDepartment,
                UserDepartment.department_id
                == KnowledgeBaseDepartmentPermission.department_id,
            )
            .join(
                Department,
                Department.id == KnowledgeBaseDepartmentPermission.department_id,
            )
            .where(
                KnowledgeBaseDepartmentPermission.knowledge_base_id
                == knowledge_base_id,
                UserDepartment.user_id == user.id,
                Department.is_active.is_(True),
            )
        )
    )
    if not permissions:
        return None
    return PermissionLevel(max(permissions, key=PERMISSION_RANK.__getitem__))


def require_knowledge_base_permission(
    db: Session,
    user: User,
    knowledge_base_id: int,
    required: PermissionLevel = PermissionLevel.QUERY,
) -> KnowledgeBase:
    knowledge_base = _knowledge_base_or_404(db, knowledge_base_id)
    granted = effective_permission(db, user, knowledge_base_id)
    if not granted or PERMISSION_RANK[granted.value] < PERMISSION_RANK[required.value]:
        raise HTTPException(status_code=403, detail="当前账号没有访问该知识库的权限")
    return knowledge_base


def require_collection_permission(
    db: Session, user: User, collection_name: str
) -> KnowledgeBase:
    knowledge_base = db.scalar(
        select(KnowledgeBase).where(KnowledgeBase.collection_name == collection_name)
    )
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return require_knowledge_base_permission(db, user, knowledge_base.id)


def _upsert_permission(
    db: Session, model: type[Any], filters: tuple[Any, ...], values: dict[str, Any]
) -> Any:
    grant = db.scalar(select(model).where(*filters))
    if grant:
        grant.permission = values["permission"]
    else:
        grant = model(**values)
        db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


def set_user_permission(
    db: Session, knowledge_base_id: int, user_id: int, permission: PermissionLevel
) -> KnowledgeBaseUserPermission:
    _knowledge_base_or_404(db, knowledge_base_id)
    user = _user_or_404(db, user_id)
    if not user.is_active:
        raise HTTPException(status_code=400, detail="不能给已禁用用户授权")
    return _upsert_permission(
        db,
        KnowledgeBaseUserPermission,
        (
            KnowledgeBaseUserPermission.knowledge_base_id == knowledge_base_id,
            KnowledgeBaseUserPermission.user_id == user_id,
        ),
        {
            "knowledge_base_id": knowledge_base_id,
            "user_id": user_id,
            "permission": permission.value,
        },
    )


def set_role_permission(
    db: Session, knowledge_base_id: int, role: UserRole, permission: PermissionLevel
) -> KnowledgeBaseRolePermission:
    _knowledge_base_or_404(db, knowledge_base_id)
    return _upsert_permission(
        db,
        KnowledgeBaseRolePermission,
        (
            KnowledgeBaseRolePermission.knowledge_base_id == knowledge_base_id,
            KnowledgeBaseRolePermission.role == role.value,
        ),
        {
            "knowledge_base_id": knowledge_base_id,
            "role": role.value,
            "permission": permission.value,
        },
    )


def set_department_permission(
    db: Session,
    knowledge_base_id: int,
    department_id: int,
    permission: PermissionLevel,
) -> KnowledgeBaseDepartmentPermission:
    _knowledge_base_or_404(db, knowledge_base_id)
    department = _department_or_404(db, department_id)
    if not department.is_active:
        raise HTTPException(status_code=400, detail="不能给已停用部门授权")
    return _upsert_permission(
        db,
        KnowledgeBaseDepartmentPermission,
        (
            KnowledgeBaseDepartmentPermission.knowledge_base_id == knowledge_base_id,
            KnowledgeBaseDepartmentPermission.department_id == department_id,
        ),
        {
            "knowledge_base_id": knowledge_base_id,
            "department_id": department_id,
            "permission": permission.value,
        },
    )


def delete_permission(db: Session, model: type[Any], *filters: Any) -> None:
    grant = db.scalar(select(model).where(*filters))
    if not grant:
        raise HTTPException(status_code=404, detail="授权记录不存在")
    db.delete(grant)
    db.commit()


def list_permission_grants(db: Session, knowledge_base_id: int) -> list[dict[str, Any]]:
    _knowledge_base_or_404(db, knowledge_base_id)
    grants: list[dict[str, Any]] = []
    for grant, user in db.execute(
        select(KnowledgeBaseUserPermission, User)
        .join(User, User.id == KnowledgeBaseUserPermission.user_id)
        .where(KnowledgeBaseUserPermission.knowledge_base_id == knowledge_base_id)
    ):
        grants.append(
            {
                "id": grant.id,
                "subject_type": "user",
                "subject_id": user.id,
                "subject_name": user.display_name or user.username,
                "permission": grant.permission,
            }
        )
    for grant in db.scalars(
        select(KnowledgeBaseRolePermission).where(
            KnowledgeBaseRolePermission.knowledge_base_id == knowledge_base_id
        )
    ):
        grants.append(
            {
                "id": grant.id,
                "subject_type": "role",
                "subject_id": None,
                "subject_name": grant.role,
                "permission": grant.permission,
            }
        )
    for grant, department in db.execute(
        select(KnowledgeBaseDepartmentPermission, Department)
        .join(Department, Department.id == KnowledgeBaseDepartmentPermission.department_id)
        .where(
            KnowledgeBaseDepartmentPermission.knowledge_base_id == knowledge_base_id
        )
    ):
        grants.append(
            {
                "id": grant.id,
                "subject_type": "department",
                "subject_id": department.id,
                "subject_name": department.name,
                "permission": grant.permission,
            }
        )
    return sorted(grants, key=lambda item: (item["subject_type"], item["subject_name"]))
