from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "B2B Manufacturer Platform"
    APP_ENV: Literal["development", "testing", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Database
    DATABASE_URL: str

    # CORS and trusted proxies
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    TRUSTED_PROXY_IPS: list[str] = []

    # Redis
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = Field(default=20, gt=0)
    REDIS_SOCKET_CONNECT_TIMEOUT: float = Field(default=10.0, gt=0)
    REDIS_SOCKET_TIMEOUT: float = Field(default=10.0, gt=0)

    # JWT
    JWT_SECRET_KEY: SecretStr = Field(min_length=64)
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    JWT_ISSUER: str = "luggage-showroom-backend"
    JWT_AUDIENCE: str = "luggage-showroom-api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10, gt=0, le=60)

    # Authentication encryption
    AUTH_ENCRYPTION_KEY: SecretStr

    # Email provider
    EMAIL_PROVIDER: Literal["brevo"] = "brevo"
    BREVO_API_KEY: SecretStr
    EMAIL_FROM_ADDRESS: str
    EMAIL_FROM_NAME: str

    # WebAuthn / Passkeys
    WEBAUTHN_RP_ID: str
    WEBAUTHN_RP_NAME: str
    WEBAUTHN_EXPECTED_ORIGIN: str
    WEBAUTHN_CHALLENGE_EXPIRE_SECONDS: int = Field(default=300, gt=0)


settings = Settings()
