# Models module
from src.models.base import Base, TimestampMixin, UUIDMixin

# Auth models (FEAT-001)
from src.models.user import User
from src.models.integration import Integration
from src.models.refresh_token import RefreshToken
from src.models.audit_log import AuditLog, AuditAction

# Billing models (FEAT-002)
from src.models.billing import Plan, Subscription, Invoice, StripeEvent

# Slack models (FEAT-006)
from src.models.slack_installation import SlackInstallation

# InboxPilot models (FEAT-003)
from src.models.inbox_pilot.email_record import EmailRecord
from src.models.inbox_pilot.agent_config import InboxPilotConfig

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    # Auth (FEAT-001)
    "User",
    "Integration",
    "RefreshToken",
    "AuditLog",
    "AuditAction",
    # Billing (FEAT-002)
    "Plan",
    "Subscription",
    "Invoice",
    "StripeEvent",
    # Slack (FEAT-006)
    "SlackInstallation",
    # InboxPilot (FEAT-003)
    "EmailRecord",
    "InboxPilotConfig",
]
