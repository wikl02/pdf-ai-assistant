from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models.access import PermissionLevel


class PermissionSubjectType(StrEnum):
    USER = "user"
    ROLE = "role"
    DEPARTMENT = "department"


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")

    @field_validator("name", "code")
    @classmethod
    def strip_values(cls, value: str) -> str:
        return value.strip()


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(
        default=None, min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$"
    )
    is_active: bool | None = None

    @field_validator("name", "code")
    @classmethod
    def strip_optional_values(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserDepartmentsUpdate(BaseModel):
    department_ids: list[int] = Field(default_factory=list)


class PermissionUpdate(BaseModel):
    permission: PermissionLevel


class PermissionGrantResponse(BaseModel):
    id: int
    subject_type: PermissionSubjectType
    subject_id: int | None = None
    subject_name: str
    permission: PermissionLevel


class KnowledgeBasePermissionsResponse(BaseModel):
    knowledge_base_id: int
    grants: list[PermissionGrantResponse]
