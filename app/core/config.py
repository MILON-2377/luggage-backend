from datetime import timedelta
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.modules.media.enums import StorageProvider


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
    BREVO_API_URL: str = "https://api.brevo.com/v3/smtp/email"
    EMAIL_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    EMAIL_REQUEST_TIMEOUT: float = Field(default=10.0, gt=0, le=60)
    EMAIL_RETRY_BACKOFF_SECONDS: tuple[float, ...] = (0.5, 1.0, 2.0)
    EMAIL_MAX_RETRY_AFTER_SECONDS: float

    # WebAuthn / Passkeys
    WEBAUTHN_RP_ID: str
    WEBAUTHN_RP_NAME: str
    WEBAUTHN_EXPECTED_ORIGIN: str
    WEBAUTHN_CHALLENGE_EXPIRE_SECONDS: int = Field(default=300, gt=0)

    # Invitations
    INVITATION_EXPIRE_HOURS: int = Field(default=24, ge=1, le=24 * 14)
    INVITATION_MAX_ATTEMPTS: int = Field(default=5, ge=1, le=20)

    # Password reset
    PASSWORD_RESET_PATH: str = "/reset-password"
    PASSWORD_RESET_EXPIRE_MINUTES: int = Field(
        default=15,
        ge=5,
        le=60,
    )
    PASSWORD_RESET_MAX_ATTEMPTS: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    # Authentication
    FRONTEND_BASE_URL: str
    INVITATION_ACCEPTANCE_PATH: str = "/accept-invitation"

    # Authentication session
    AUTH_SESSION_EXPIRE_DAYS: int = Field(default=7, gt=0, le=90)

    # Refresh token
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, gt=0, le=90)

    # Authentication cookies
    ACCESS_TOKEN_COOKIE_NAME: str = "__Host-access_token"
    REFRESH_TOKEN_COOKIE_NAME: str = "__Host-refresh_token"

    AUTH_COOKIE_HTTPONLY: bool = True
    AUTH_COOKIE_SECURE: bool = True
    AUTH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    AUTH_COOKIE_PATH: str = "/"

    # Login
    ADMIN_LOGIN_MAX_FAILED_ATTEMPTS: int = Field(default=5, ge=1, le=20)
    ADMIN_LOGIN_LOCKOUT_MINUTES: int = Field(default=15, ge=1, le=1440)

    # Initial MFA enrollment
    MFA_ENROLLMENT_SESSION_TTL: timedelta = Field(
        default=timedelta(minutes=10),
    )
    MFA_ENROLLMENT_MAX_ATTEMPTS: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    # Email worker
    EMAIL_WORKER_RECOVERY_INTERVAL_SECONDS: float = Field(
        default=60.0,
        gt=0,
        le=3600,
    )
    EMAIL_WORKER_BATCH_SIZE: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    # Media
    MEDIA_UPLOAD_EXPIRES_SECONDS: int = 900
    MEDIA_PROVIDER: StorageProvider = StorageProvider.CLOUDINARY
    MEDIA_PENDING_UPLOAD_TTL_SECONDS: int = 86400
    MEDIA_DELETION_RETRY_AFTER_SECONDS: int = 300
    MEDIA_CLEANUP_BATCH_SIZE: int = 100

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: SecretStr
    CLOUDINARY_UPLOAD_PRESET: str


settings = Settings()
