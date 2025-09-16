import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    redis_url: str = "redis://localhost:6379"
    database_url: str
    unsplash_access_key: str | None = None
    unsplash_secret_key: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()