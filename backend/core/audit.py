import logging
from typing import Any


logger = logging.getLogger("pdf_ai_assistant.audit")


def _safe(value: Any) -> str:
    return str(value).replace("\r", " ").replace("\n", " ")[:500]


def audit_event(
    event: str,
    *,
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
