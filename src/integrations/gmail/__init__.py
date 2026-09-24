"""Gmail integration module."""

from src.integrations.gmail.client import GmailClient
from src.integrations.gmail.webhook import parse_gmail_notification

__all__ = ["GmailClient", "parse_gmail_notification"]
