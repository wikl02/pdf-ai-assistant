import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger("pdf_ai_assistant.config")


def _cors_origins() -> list[str]:
    raw_value = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8501,http://127.0.0.1:8501",
    )
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./data/app.db")
    )
    upload_storage_dir: Path = field(
        default_factory=lambda: Path(os.getenv("UPLOAD_STORAGE_DIR", "./data/uploads"))
    )
    jwt_secret_key: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY")
        or os.getenv("APP_PASSWORD")
        or "development-only-change-this-secret"
    )
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = field(
        default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    )
    bootstrap_admin_username: str | None = field(
        default_factory=lambda: os.getenv("APP_USERNAME")
    )
    bootstrap_admin_password: str | None = field(
        default_factory=lambda: os.getenv("APP_PASSWORD")
    )
    cors_origins: list[str] = field(default_factory=_cors_origins)


settings = Settings()

if not os.getenv("JWT_SECRET_KEY"):
    logger.warning("JWT_SECRET_KEY is not set; configure it before production deployment")