from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event: str
    outcome: str
    actor_id: int | None
    actor_name: str | None
    client_ip: str | None
    details: dict[str, Any] | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


class UsageSummaryResponse(BaseModel):
    audit_event_count: int
    question_count: int
    failed_event_count: int
    active_user_count: int
    conversation_count: int
    message_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
