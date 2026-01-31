"""Application configuration using pydantic-settings."""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "FounderPilot"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://localhost/founderpilot"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Auth
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Slack Integration
    SLACK_CLIENT_ID: Optional[str] = None
    SLACK_CLIENT_SECRET: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None
    SLACK_BOT_TOKEN: Optional[str] = None  # For dev/testing without OAuth
    SLACK_APP_TOKEN: Optional[str] = None  # For Socket Mode (xapp-...)

    # Encryption key for sensitive data (tokens)
    # Generate with: from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
    ENCRYPTION_KEY: Optional[str] = None

    # OAuth Redirect
    SLACK_REDIRECT_URI: Optional[str] = None
    FRONTEND_URL: str = "http://localhost:3000"

    # LLM Providers
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    @property
    def slack_configured(self) -> bool:
        """Check if Slack is properly configured."""
        return all([
            self.SLACK_CLIENT_ID,
            self.SLACK_CLIENT_SECRET,
            self.SLACK_SIGNING_SECRET,
        ])


# Global settings instance
settings = Settings()
