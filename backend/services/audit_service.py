"""Queries for structured audit logs and aggregate product usage."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.activity import AuditLog, ChatConversation, ChatMessage


def list_audit_logs(
    db: Session,
    *,
    event: str | None = None,
    outcome: str | None = None,
    actor_id: int | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    page: int = 1,
    page_size: int = 30,
) -> tuple[list[AuditLog], int]:
    filters = []
    if event:
        filters.append(AuditLog.event == event)
    if outcome:
        filters.append(AuditLog.outcome == outcome)
    if actor_id is not None:
        filters.append(AuditLog.actor_id == actor_id)
    if created_from:
        filters.append(AuditLog.created_at >= created_from)
    if created_to:
        filters.append(AuditLog.created_at <= created_to)

    total = db.scalar(select(func.count(AuditLog.id)).where(*filters)) or 0
    items = list(
        db.scalars(
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def usage_summary(db: Session) -> dict[str, int]:
    return {
        "audit_event_count": db.scalar(select(func.count(AuditLog.id))) or 0,
        "question_count": db.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.event == "question_answered",
                AuditLog.outcome == "success",
            )
        )
        or 0,
        "failed_event_count": db.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.outcome == "failed")
        )
        or 0,
        "active_user_count": db.scalar(
            select(func.count(func.distinct(AuditLog.actor_id))).where(
                AuditLog.actor_id.is_not(None)
            )
        )
        or 0,
        "conversation_count": db.scalar(select(func.count(ChatConversation.id))) or 0,
        "message_count": db.scalar(select(func.count(ChatMessage.id))) or 0,
    }
