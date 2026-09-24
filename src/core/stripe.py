"""Stripe client configuration."""
import stripe
from src.core.config import settings

# Configure Stripe API key
stripe.api_key = settings.stripe_secret_key

# Export stripe module for use in services
__all__ = ["stripe"]
