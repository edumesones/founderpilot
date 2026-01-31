"""Application configuration with environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "FounderPilot"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://localhost/founderpilot"

    # JWT Auth (from FEAT-001)
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Stripe Configuration
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

    # Frontend URLs (for Stripe redirects)
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
