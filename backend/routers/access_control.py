"""Administrative APIs for departments and knowledge-base grants."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.core.audit import audit_event
from backend.database import get_db
from backend.dependencies.auth import AdminUser
from backend.models.access import (
    KnowledgeBaseDepartmentPermission,
    KnowledgeBaseRolePermission,
    KnowledgeBaseUserPermission,
)
from backend.models.user import UserRole
from backend.schemas.access_control import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    KnowledgeBasePermissionsResponse,
    PermissionGrantResponse,
    PermissionUpdate,
    UserDepartmentsUpdate,
)
from backend.schemas.management import MessageResponse
from backend.services.access_control_service import (
    create_department,
    delete_permission,
    list_departments,
    list_permission_grants,
    list_user_departments,
    replace_user_departments,
    set_department_permission,
    set_role_permission,
    set_user_permission,
    update_department,
)


router = APIRouter(prefix="/api/admin", tags=["admin-access-control"])


def _grant_response(grant: dict) -> PermissionGrantResponse:
    return PermissionGrantResponse.model_validate(grant)


@router.get("/departments", response_model=list[DepartmentResponse])
def get_departments(
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[DepartmentResponse]:
    return [DepartmentResponse.model_validate(item) for item in list_departments(db)]


@router.post(
    "/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_department(
    payload: DepartmentCreate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> DepartmentResponse:
    department = create_department(db, payload)
    audit_event(
        "department_created",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        department_id=department.id,
        department_code=department.code,
    )
    return DepartmentResponse.model_validate(department)


@router.patch("/departments/{department_id}", response_model=DepartmentResponse)
def change_department(
    department_id: int,
    payload: DepartmentUpdate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> DepartmentResponse:
    department = update_department(db, department_id, payload)
    audit_event(
        "department_updated",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        department_id=department.id,
        is_active=department.is_active,
    )
    return DepartmentResponse.model_validate(department)


@router.get(
    "/users/{user_id}/departments", response_model=list[DepartmentResponse]
)
def get_user_department_memberships(
    user_id: int,
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[DepartmentResponse]:
    return [
        DepartmentResponse.model_validate(item)
        for item in list_user_departments(db, user_id)
    ]


@router.put(
    "/users/{user_id}/departments", response_model=list[DepartmentResponse]
)
def change_user_department_memberships(
    user_id: int,
    payload: UserDepartmentsUpdate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[DepartmentResponse]:
    departments = replace_user_departments(db, user_id, payload.department_ids)
    audit_event(
        "user_departments_changed",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        target_user_id=user_id,
        department_ids=",".join(str(item.id) for item in departments),
    )
    return [DepartmentResponse.model_validate(item) for item in departments]


@router.get(
    "/knowledge-bases/{knowledge_base_id}/permissions",
    response_model=KnowledgeBasePermissionsResponse,
)
def get_knowledge_base_permissions(
    knowledge_base_id: int,
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> KnowledgeBasePermissionsResponse:
    grants = list_permission_grants(db, knowledge_base_id)
    return KnowledgeBasePermissionsResponse(
        knowledge_base_id=knowledge_base_id,
        grants=[_grant_response(item) for item in grants],
    )


def _current_grant(db: Session, knowledge_base_id: int, subject_type: str, name: str):
    grants = list_permission_grants(db, knowledge_base_id)
    return _grant_response(
        next(
            item
            for item in grants
            if item["subject_type"] == subject_type
            and str(item["subject_id"] if item["subject_id"] is not None else item["subject_name"])
            == name
        )
    )


@router.put(
    "/knowledge-bases/{knowledge_base_id}/permissions/users/{user_id}",
    response_model=PermissionGrantResponse,
)
def grant_user_permission(
    knowledge_base_id: int,
    user_id: int,
    payload: PermissionUpdate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> PermissionGrantResponse:
    set_user_permission(db, knowledge_base_id, user_id, payload.permission)
    audit_event(
        "knowledge_base_permission_granted",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        knowledge_base_id=knowledge_base_id,
        subject_type="user",
        subject_id=user_id,
        permission=payload.permission.value,
    )
    return _current_grant(db, knowledge_base_id, "user", str(user_id))


@router.delete(
    "/knowledge-bases/{knowledge_base_id}/permissions/users/{user_id}",
    response_model=MessageResponse,
)
def revoke_user_permission(
    knowledge_base_id: int,
    user_id: int,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    delete_permission(
        db,
        KnowledgeBaseUserPermission,
        KnowledgeBaseUserPermission.knowledge_base_id == knowledge_base_id,
        KnowledgeBaseUserPermission.user_id == user_id,
    )
    audit_event(
        "knowledge_base_permission_revoked",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        knowledge_base_id=knowledge_base_id,
        subject_type="user",
        subject_id=user_id,
    )
    return MessageResponse(message="用户授权已移除")


@router.put(
    "/knowledge-bases/{knowledge_base_id}/permissions/departments/{department_id}",
    response_model=PermissionGrantResponse,
)
def grant_department_permission(
    knowledge_base_id: int,
    department_id: int,
    payload: PermissionUpdate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> PermissionGrantResponse:
    set_department_permission(db, knowledge_base_id, department_id, payload.permission)
    audit_event(
        "knowledge_base_permission_granted",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        knowledge_base_id=knowledge_base_id,
        subject_type="department",
        subject_id=department_id,
        permission=payload.permission.value,
    )
    return _current_grant(db, knowledge_base_id, "department", str(department_id))


@router.delete(
    "/knowledge-bases/{knowledge_base_id}/permissions/departments/{department_id}",
    response_model=MessageResponse,
)
def revoke_department_permission(
    knowledge_base_id: int,
    department_id: int,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    delete_permission(
        db,
        KnowledgeBaseDepartmentPermission,
        KnowledgeBaseDepartmentPermission.knowledge_base_id == knowledge_base_id,
        KnowledgeBaseDepartmentPermission.department_id == department_id,
    )
    audit_event(
        "knowledge_base_permission_revoked",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        knowledge_base_id=knowledge_base_id,
        subject_type="department",
        subject_id=department_id,
    )
    return MessageResponse(message="部门授权已移除")


@router.put(
    "/knowledge-bases/{knowledge_base_id}/permissions/roles/{role}",
    response_model=PermissionGrantResponse,
)
def grant_role_permission(
    knowledge_base_id: int,
    role: UserRole,
    payload: PermissionUpdate,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> PermissionGrantResponse:
    set_role_permission(db, knowledge_base_id, role, payload.permission)
    audit_event(
        "knowledge_base_permission_granted",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        knowledge_base_id=knowledge_base_id,
        subject_type="role",
        subject_name=role.value,
        permission=payload.permission.value,
    )
    return _current_grant(db, knowledge_base_id, "role", role.value)


@router.delete(
    "/knowledge-bases/{knowledge_base_id}/permissions/roles/{role}",
    response_model=MessageResponse,
)
def revoke_role_permission(
    knowledge_base_id: int,
    role: UserRole,
    current_user: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    delete_permission(
        db,
        KnowledgeBaseRolePermission,
        KnowledgeBaseRolePermission.knowledge_base_id == knowledge_base_id,
        KnowledgeBaseRolePermission.role == role.value,
    )
    audit_event(
        "knowledge_base_permission_revoked",
        db=db,
        actor_id=current_user.id,
        actor_name=current_user.username,
        knowledge_base_id=knowledge_base_id,
        subject_type="role",
        subject_name=role.value,
    )
    return MessageResponse(message="角色授权已移除")
