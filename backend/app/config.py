from pathlib import Path
import os
from typing import Literal
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = "postgresql+psycopg2://teledesk@localhost:5432/teledesk"


class Settings(BaseSettings):
    APP_ENV: Literal["development", "test", "production"] = "development"

    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        extra="ignore",
    )

    DATABASE_URL: str = DEFAULT_DATABASE_URL
    REDIS_URL: str = "redis://localhost:6379/0"

    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "teledesk"

    GEMINI_API_KEY: str = ""
    GEMINI_CHAT_MODEL: str = "gemini-3.8-flash"
    GEMINI_EMBED_MODEL: str = "gemini-embedding-001"
    EMBED_DIM: int = 768

    ENCRYPTION_KEY: str = ""
    JWT_SECRET: str = "change-me"
    PUBLIC_BASE_URL: str = ""

    @model_validator(mode="after")
    def validate_runtime_configuration(self):
        if self.APP_ENV == "development":
            return self

        problems = []
        if self.JWT_SECRET == "change-me":
            problems.append("JWT_SECRET must be changed")
        if not self.ENCRYPTION_KEY:
            problems.append("ENCRYPTION_KEY is required")
        else:
            try:
                Fernet(self.ENCRYPTION_KEY.encode())
            except (TypeError, ValueError):
                problems.append("ENCRYPTION_KEY is invalid")

        database = urlsplit(self.DATABASE_URL)
        default_database = self.DATABASE_URL == DEFAULT_DATABASE_URL
        local_development_database = (
            database.hostname in {"localhost", "127.0.0.1"}
            and database.username == "teledesk"
            and database.path == "/teledesk"
        )
        development_database_credentials = (
            database.username == "teledesk"
            and database.password == "teledesk"
        )
        if (
            default_database
            or local_development_database
            or development_database_credentials
        ):
            problems.append("DATABASE_URL must not use development settings")

        defaults = type(self).model_fields
        if (
            self.MINIO_ACCESS_KEY == defaults["MINIO_ACCESS_KEY"].default
            or self.MINIO_SECRET_KEY == defaults["MINIO_SECRET_KEY"].default
        ):
            problems.append("storage credentials must not use development defaults")

        if problems:
            raise ValueError("; ".join(problems))

        return self


settings = Settings(
    _env_file=None if os.environ.get("APP_ENV") == "test" else ROOT / ".env"
)  # type: ignore[call-arg]

FRONTEND_DIR = ROOT / "frontend"


