from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "BrokeButThriving API"
    api_prefix: str = "/api/v1"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'bbt.db'}"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_prefix="BBT_", env_file=".env", extra="ignore")


settings = Settings()

