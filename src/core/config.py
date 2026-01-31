"""
Application configuration using pydantic-settings.
All environment variables are loaded and validated here.
"""

import base64
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://founderpilot:password@localhost:5432/founderpilot",
        description="PostgreSQL connection URL with asyncpg driver",
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # JWT Configuration
    jwt_private_key: str = Field(
        ...,
        description="Base64-encoded RSA private key for signing JWTs",
    )
    jwt_public_key: str = Field(
        ...,
        description="Base64-encoded RSA public key for verifying JWTs",
    )
    jwt_algorithm: str = Field(
        default="RS256",
        description="JWT signing algorithm",
    )
    access_token_expire_minutes: int = Field(
        default=1440,  # 24 hours
        description="Access token expiration in minutes",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration in days",
    )

    # Encryption
    encryption_key: str = Field(
        ...,
        description="Fernet key for encrypting OAuth tokens",
    )

    # Google OAuth
    google_client_id: str = Field(
        ...,
        description="Google OAuth2 client ID",
    )
    google_client_secret: str = Field(
        ...,
        description="Google OAuth2 client secret",
    )

    # Gmail API (can use same credentials as Google OAuth)
    gmail_client_id: Optional[str] = Field(
        default=None,
        description="Gmail OAuth2 client ID (defaults to google_client_id)",
    )
    gmail_client_secret: Optional[str] = Field(
        default=None,
        description="Gmail OAuth2 client secret (defaults to google_client_secret)",
    )

    # Slack OAuth
    slack_client_id: str = Field(
        ...,
        description="Slack OAuth2 client ID",
    )
    slack_client_secret: str = Field(
        ...,
        description="Slack OAuth2 client secret",
    )
    slack_signing_secret: str = Field(
        ...,
        description="Slack signing secret for request verification",
    )

    # Application
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="Frontend URL for redirects",
    )
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host",
    )
    api_port: int = Field(
        default=8000,
        description="API server port",
    )
    debug: bool = Field(
        default=False,
        description="Debug mode",
    )
    environment: str = Field(
        default="development",
        description="Environment name",
    )

    # Rate Limiting
    rate_limit_auth_requests: int = Field(
        default=10,
        description="Max auth requests per window",
    )
    rate_limit_auth_window_seconds: int = Field(
        default=60,
        description="Rate limit window in seconds",
    )

    @field_validator("jwt_private_key", "jwt_public_key")
    @classmethod
    def decode_base64_key(cls, v: str) -> str:
        """Decode base64-encoded keys."""
        try:
            # Try to decode - if it fails, assume it's already decoded
            decoded = base64.b64decode(v).decode("utf-8")
            return decoded
        except Exception:
            # Already decoded or PEM format
            return v

    @property
    def gmail_client_id_resolved(self) -> str:
        """Get Gmail client ID, defaulting to Google client ID."""
        return self.gmail_client_id or self.google_client_id

    @property
    def gmail_client_secret_resolved(self) -> str:
        """Get Gmail client secret, defaulting to Google client secret."""
        return self.gmail_client_secret or self.google_client_secret


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
