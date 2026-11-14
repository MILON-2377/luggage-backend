from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "B2B Manufacturer Platform"
    APP_ENV: Literal["development", "testing", "staging", "production"] = (
        "development"
    )
    DEBUG: bool = False

    API_V1_PREFIX: str = "/api/v1"

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    TRUSTED_PROXY_IPS: list[str] = []

    # Redis
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 20
    REDIS_SOCKET_CONNECT_TIMEOUT: float = 10.0
    REDIS_SOCKET_TIMEOUT: float = 10.0


settings = Settings()