from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_base_url: str = "http://localhost:8000"
    database_path: str = "data/social-studio.db"
    artifact_dir: str = "artifacts"
    encryption_key: str = ""
    webhook_secret: str = "development-webhook-secret"
    fake_platform_base_url: str = "http://localhost:8000/fake"
    worker_poll_seconds: float = 1.0
    enable_worker: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

