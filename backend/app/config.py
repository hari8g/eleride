from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl
from typing import List, Optional
from pydantic import field_validator


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me"

    database_url: str = "postgresql+psycopg://ev:evpass@db:5432/evdb"

    cors_origins: List[AnyHttpUrl] | List[str] = ["http://localhost:5173"]
    cors_origin_regex: Optional[str] = None

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

    @field_validator("database_url", mode="before")
    @classmethod
    def ensure_ssl(cls, v: str) -> str:
        try:
            url = str(v)
        except Exception:
            return v
        lower = url.lower()
        if "localhost" in lower or "127.0.0.1" in lower:
            return url
        if "sslmode=" not in lower:
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}sslmode=require"
        return url


settings = Settings()


