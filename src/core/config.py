"""Application configuration with environment variables."""

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

    # Application
    app_name: str = Field(default="FounderPilot", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://founderpilot:password@localhost:5432/founderpilot",
        alias="DATABASE_URL",
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # JWT Configuration (FEAT-001)
    jwt_private_key: Optional[str] = Field(default=None, alias="JWT_PRIVATE_KEY")
    jwt_public_key: Optional[str] = Field(default=None, alias="JWT_PUBLIC_KEY")
    jwt_secret_key: str = Field(
        default="change-me-in-production", alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="RS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=1440, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(default=7)

    # Encryption (FEAT-001)
    encryption_key: Optional[str] = Field(default=None, alias="ENCRYPTION_KEY")

    # Google OAuth (FEAT-001, FEAT-003)
    google_client_id: Optional[str] = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = Field(
        default=None, alias="GOOGLE_CLIENT_SECRET"
    )
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/google/callback",
        alias="GOOGLE_REDIRECT_URI",
    )

    # Gmail API (FEAT-001, FEAT-003)
    gmail_client_id: Optional[str] = Field(default=None, alias="GMAIL_CLIENT_ID")
    gmail_client_secret: Optional[str] = Field(
        default=None, alias="GMAIL_CLIENT_SECRET"
    )
    gmail_pubsub_topic: Optional[str] = Field(default=None, alias="GMAIL_PUBSUB_TOPIC")
    gmail_pubsub_subscription: Optional[str] = Field(
        default=None, alias="GMAIL_PUBSUB_SUBSCRIPTION"
    )

    # Stripe Configuration (FEAT-002)
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_publishable_key: str = Field(default="", alias="STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_price_inbox: str = Field(default="", alias="STRIPE_PRICE_INBOX")
    stripe_price_invoice: str = Field(default="", alias="STRIPE_PRICE_INVOICE")
    stripe_price_meeting: str = Field(default="", alias="STRIPE_PRICE_MEETING")
    stripe_price_bundle: str = Field(default="", alias="STRIPE_PRICE_BUNDLE")
    trial_days: int = Field(default=14, alias="TRIAL_DAYS")

    # Slack Integration (FEAT-001, FEAT-006)
    slack_client_id: Optional[str] = Field(default=None, alias="SLACK_CLIENT_ID")
    slack_client_secret: Optional[str] = Field(
        default=None, alias="SLACK_CLIENT_SECRET"
    )
    slack_signing_secret: Optional[str] = Field(
        default=None, alias="SLACK_SIGNING_SECRET"
    )
    slack_bot_token: Optional[str] = Field(default=None, alias="SLACK_BOT_TOKEN")
    slack_app_token: Optional[str] = Field(default=None, alias="SLACK_APP_TOKEN")
    slack_redirect_uri: Optional[str] = Field(default=None, alias="SLACK_REDIRECT_URI")

    # Frontend URLs
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")

    # API Server
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # LLM Providers
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")

    # Langfuse (Observability)
    langfuse_public_key: Optional[str] = Field(
        default=None, alias="LANGFUSE_PUBLIC_KEY"
    )
    langfuse_secret_key: Optional[str] = Field(
        default=None, alias="LANGFUSE_SECRET_KEY"
    )
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", alias="LANGFUSE_HOST"
    )

    # InboxPilot specific (FEAT-003)
    inbox_pilot_escalation_threshold: float = Field(
        default=0.8, alias="INBOX_PILOT_ESCALATION_THRESHOLD"
    )
    inbox_pilot_draft_threshold: float = Field(
        default=0.7, alias="INBOX_PILOT_DRAFT_THRESHOLD"
    )
    inbox_pilot_rate_limit_trial: int = Field(
        default=50, alias="INBOX_PILOT_RATE_LIMIT_TRIAL"
    )
    inbox_pilot_rate_limit_paid: int = Field(
        default=500, alias="INBOX_PILOT_RATE_LIMIT_PAID"
    )

    # MeetingPilot specific (FEAT-005)
    # Uses same Google OAuth credentials as Gmail - calendar.readonly scope
    meeting_pilot_escalation_threshold: float = Field(
        default=0.8, alias="MEETING_PILOT_ESCALATION_THRESHOLD"
    )
    meeting_pilot_brief_minutes_before: int = Field(
        default=30, alias="MEETING_PILOT_BRIEF_MINUTES_BEFORE"
    )
    meeting_pilot_sync_interval_minutes: int = Field(
        default=15, alias="MEETING_PILOT_SYNC_INTERVAL_MINUTES"
    )
    meeting_pilot_rate_limit_trial: int = Field(
        default=30, alias="MEETING_PILOT_RATE_LIMIT_TRIAL"
    )
    meeting_pilot_rate_limit_paid: int = Field(
        default=100, alias="MEETING_PILOT_RATE_LIMIT_PAID"
    )

    # InvoicePilot specific (FEAT-004)
    invoice_pilot_enabled: bool = Field(
        default=True, alias="INVOICE_PILOT_ENABLED"
    )
    invoice_confidence_threshold: float = Field(
        default=0.8, alias="INVOICE_CONFIDENCE_THRESHOLD"
    )
    invoice_reminder_schedule: str = Field(
        default="-3,3,7,14", alias="INVOICE_REMINDER_SCHEDULE"
    )
    invoice_scan_interval: int = Field(
        default=5, alias="INVOICE_SCAN_INTERVAL"
    )
    invoice_escalation_threshold: int = Field(
        default=3, alias="INVOICE_ESCALATION_THRESHOLD"
    )
    invoice_overdue_days_warning: int = Field(
        default=30, alias="INVOICE_OVERDUE_DAYS_WARNING"
    )
    invoice_reminder_tone: str = Field(
        default="friendly", alias="INVOICE_REMINDER_TONE"
    )
    invoice_pilot_rate_limit_trial: int = Field(
        default=20, alias="INVOICE_PILOT_RATE_LIMIT_TRIAL"
    )
    invoice_pilot_rate_limit_paid: int = Field(
        default=200, alias="INVOICE_PILOT_RATE_LIMIT_PAID"
    )

    # Rate Limiting (FEAT-001)
    rate_limit_auth_requests: int = Field(default=10)
    rate_limit_auth_window_seconds: int = Field(default=60)

    @property
    def invoice_reminder_schedule_list(self) -> list[int]:
        """Parse invoice reminder schedule string into list of integers."""
        return [int(day.strip()) for day in self.invoice_reminder_schedule.split(",")]

    @field_validator("jwt_private_key", "jwt_public_key", mode="before")
    @classmethod
    def decode_base64_key(cls, v: Optional[str]) -> Optional[str]:
        """Decode base64-encoded keys if present."""
        if v is None:
            return None
        try:
            decoded = base64.b64decode(v).decode("utf-8")
            return decoded
        except Exception:
            return v

    @property
    def gmail_client_id_resolved(self) -> Optional[str]:
        """Get Gmail client ID, defaulting to Google client ID."""
        return self.gmail_client_id or self.google_client_id

    @property
    def gmail_client_secret_resolved(self) -> Optional[str]:
        """Get Gmail client secret, defaulting to Google client secret."""
        return self.gmail_client_secret or self.google_client_secret

    @property
    def slack_configured(self) -> bool:
        """Check if Slack is properly configured."""
        return all(
            [
                self.slack_client_id,
                self.slack_client_secret,
                self.slack_signing_secret,
            ]
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
