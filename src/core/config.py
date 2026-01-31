"""Application configuration with environment variables."""
from functools import lru_cache
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
    APP_ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://localhost/founderpilot"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT Auth (from FEAT-001)
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Google OAuth (FEAT-001, FEAT-003)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Gmail Push Notifications (FEAT-003)
    GMAIL_PUBSUB_TOPIC: Optional[str] = None
    GMAIL_PUBSUB_SUBSCRIPTION: Optional[str] = None

    # Stripe Configuration (FEAT-002)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Stripe Price IDs (created in Stripe Dashboard)
    STRIPE_PRICE_INBOX: str = ""
    STRIPE_PRICE_INVOICE: str = ""
    STRIPE_PRICE_MEETING: str = ""
    STRIPE_PRICE_BUNDLE: str = ""

    # Trial configuration
    TRIAL_DAYS: int = 14

    # Slack Integration (FEAT-003, FEAT-006)
    SLACK_CLIENT_ID: Optional[str] = None
    SLACK_CLIENT_SECRET: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_APP_TOKEN: Optional[str] = None

    # Encryption key for sensitive data
    ENCRYPTION_KEY: Optional[str] = None

    # OAuth Redirect
    SLACK_REDIRECT_URI: Optional[str] = None

    # Frontend URLs
    FRONTEND_URL: str = "http://localhost:3000"

    # LLM Providers
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Langfuse (Observability)
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # InboxPilot specific (FEAT-003)
    INBOX_PILOT_ESCALATION_THRESHOLD: float = 0.8
    INBOX_PILOT_DRAFT_THRESHOLD: float = 0.7
    INBOX_PILOT_RATE_LIMIT_TRIAL: int = 50
    INBOX_PILOT_RATE_LIMIT_PAID: int = 500

    @property
    def slack_configured(self) -> bool:
        """Check if Slack is properly configured."""
        return all([
            self.SLACK_CLIENT_ID,
            self.SLACK_CLIENT_SECRET,
            self.SLACK_SIGNING_SECRET,
        ])


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
