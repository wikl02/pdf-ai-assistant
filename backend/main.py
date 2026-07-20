import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.core.config import settings
from backend.database import init_database, session_scope
from backend.routers import admin_users, auth, catalog, health, knowledge, management, users
from backend.services.user_service import ensure_bootstrap_admin


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

logger = logging.getLogger("pdf_ai_assistant.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    with session_scope() as db:
        ensure_bootstrap_admin(db)
    logger.info("application startup complete")
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="企业知识库智能助手 API",
        version="0.4.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.api_docs_enabled else None,
        redoc_url="/redoc" if settings.api_docs_enabled else None,
        openapi_url="/openapi.json" if settings.api_docs_enabled else None,
    )
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts or ["*"],
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )
    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(users.router)
    application.include_router(admin_users.router)
    application.include_router(management.router)
    application.include_router(management.compatibility_router)
    application.include_router(catalog.router)
    application.include_router(knowledge.router)
    return application


app = create_app()
