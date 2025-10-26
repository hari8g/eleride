from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl
from typing import List
from pydantic import field_validator


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me"

    database_url: str = "postgresql+psycopg://ev:evpass@db:5432/evdb"

    cors_origins: List[AnyHttpUrl] | List[str] = ["http://localhost:5173"]

    model_dir: str = "/models"
    etl_input_path: str = "/data/sample_jobs.csv"

    # Pydantic v2 settings
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        protected_namespaces=("settings_",),
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


settings = Settings()


