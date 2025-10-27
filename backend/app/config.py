from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl
from typing import List, Optional
from pydantic import field_validator
from urllib.parse import urlparse, urlencode, urlunparse, parse_qsl


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
            raw = str(v)
        except Exception:
            return v
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        # normalize scheme to SQLAlchemy psycopg v3 driver
        scheme = parsed.scheme
        if scheme in ("postgres", "postgresql", ""):
            scheme = "postgresql+psycopg"
        # Treat common internal/docker hosts as non-SSL
        if host in {"localhost", "127.0.0.1", "db"} or host.endswith(".internal") or "." not in host:
            return raw
        # keep if already present
        q = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if any(k.lower() == "sslmode" for k in q.keys()):
            return raw
        q["sslmode"] = "require"
        new_query = urlencode(q)
        rebuilt = urlunparse((
            scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        ))
        return rebuilt


settings = Settings()


