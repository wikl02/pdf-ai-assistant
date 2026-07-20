import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from backend.database import engine
from vector_store import get_chroma_client


router = APIRouter(tags=["system"])
logger = logging.getLogger("pdf_ai_assistant.health")


@router.get("/health/live")
def liveness_check() -> dict[str, str]:
    return {"status": "ok"}


def _database_status() -> str:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return "ok"


def _chroma_status() -> str:
    get_chroma_client().heartbeat()
    return "ok"


@router.get("/health")
@router.get("/health/ready")
@router.get("/api/health", include_in_schema=False)
def readiness_check(response: Response) -> dict[str, object]:
    components: dict[str, str] = {}
    for name, check in (("database", _database_status), ("chroma", _chroma_status)):
        try:
            components[name] = check()
        except Exception:
            components[name] = "error"
            logger.exception("readiness check failed component=%s", name)

    ready = all(value == "ok" for value in components.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if ready else "degraded", "components": components}
