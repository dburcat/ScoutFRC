from pydantic_settings import BaseSettings
from pathlib import Path


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

    model_config = {
        "env_file": str(Path(__file__).parent.parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


settings = Settings()  # type: ignore