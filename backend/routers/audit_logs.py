"""Administrator-only audit search and aggregate usage APIs."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies.auth import AdminUser
from backend.schemas.audit import (
    AuditLogListResponse,
    AuditLogResponse,
    UsageSummaryResponse,
)
from backend.services.audit_service import list_audit_logs, usage_summary


router = APIRouter(prefix="/api/admin/audit-logs", tags=["admin-audit"])


@router.get("/summary", response_model=UsageSummaryResponse)
def get_usage_summary(
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> UsageSummaryResponse:
    return UsageSummaryResponse.model_validate(usage_summary(db))


@router.get("", response_model=AuditLogListResponse)
def get_audit_logs(
    _: AdminUser,
    db: Annotated[Session, Depends(get_db)],
    event: str | None = None,
    outcome: str | None = None,
    actor_id: int | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 30,
) -> AuditLogListResponse:
    items, total = list_audit_logs(
        db,
        event=event,
        outcome=outcome,
        actor_id=actor_id,
        created_from=created_from,
        created_to=created_to,
        page=page,
        page_size=page_size,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
