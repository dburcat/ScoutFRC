from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # The Blue Alliance
    TBA_API_KEY: str = ""

    # App
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Sync — set to a specific year (e.g. 2026) to restrict all TBA syncs to
    # that year only. Useful during development to avoid pulling all historical
    # data. Leave unset (None) in production to allow syncing any year.
    SYNC_YEAR_LIMIT: Optional[int] = None

    model_config = {
        "env_file": str(Path(__file__).parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


settings = Settings()  # type: ignore