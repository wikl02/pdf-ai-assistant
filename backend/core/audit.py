import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


logger = logging.getLogger("pdf_ai_assistant.audit")


def _safe(value: Any) -> str:
    return str(value).replace("\r", " ").replace("\n", " ")[:500]


def audit_event(
    event: str,
    *,
    db: "Session | None" = None,
    outcome: str = "success",
    actor_id: int | None = None,
    actor_name: str | None = None,
    client_ip: str | None = None,
    **details: Any,
) -> None:
    fields = {
        "event": event,
        "outcome": outcome,
        "actor_id": actor_id,
        "actor_name": actor_name,
        "client_ip": client_ip,
        **details,
    }
    message = " ".join(
        f"{key}={_safe(value)}"
        for key, value in fields.items()
        if value is not None
    )
    log = logger.warning if outcome == "failed" else logger.info
    log(message)
    if db is None:
        return
    try:
        from backend.models.activity import AuditLog

        safe_details = json.loads(json.dumps(details, default=str)) if details else None
        db.add(
            AuditLog(
                event=event,
                outcome=outcome,
                actor_id=actor_id,
                actor_name=actor_name,
                client_ip=client_ip,
                details=safe_details,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("failed to persist audit event=%s", event)
