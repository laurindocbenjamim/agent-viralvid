# -*- coding: utf-8 -*-
"""Core application settings loaded from environment variables via Pydantic."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration schema.

    All fields are loaded from the .env file. Unknown keys are silently ignored
    so additional project variables in .env do not cause validation errors.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # tolerate extra .env keys from other services
        case_sensitive=False,
    )

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Redis — supports both local and Upstash (redis:// or rediss:// URLs)
    REDIS_URL: str = "redis://localhost:6379/0"
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""

    GROQ_API_KEY: str = ""
    LLMMODEL: str = "llama-3.3-70b-specdec"
    LLMPROVIDER: str = "groq"
    GROQ_STT_MODEL: str = "whisper-large-v3"
    SECURE_COOKIE: bool = False


settings = Settings()
