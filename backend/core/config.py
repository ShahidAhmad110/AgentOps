from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "AgentOps"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:Shahid%244321@localhost:5432/agentops",
        alias="DATABASE_URL",
    )
    document_storage_path: str = Field(
        default="storage/documents",
        alias="DOCUMENT_STORAGE_PATH",
    )
    max_document_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        alias="MAX_DOCUMENT_SIZE_BYTES",
    )
    auth_secret_key: str = Field(
        default="development-agentops-secret-key-32-chars-long-minimum",
        alias="AUTH_SECRET_KEY",
    )
    access_token_lifetime_seconds: int = Field(default=3600, alias="ACCESS_TOKEN_LIFETIME_SECONDS")
    seed_admin_password: str | None = Field(default=None, alias="SEED_ADMIN_PASSWORD")
    llm_provider: str | None = Field(default=None, alias="LLM_PROVIDER")
    llm_model: str | None = Field(default=None, alias="LLM_MODEL")

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_database_url() -> str:
    return get_settings().database_url