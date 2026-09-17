from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AgentOps"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://agentops:agentops@localhost:5432/agentops"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()