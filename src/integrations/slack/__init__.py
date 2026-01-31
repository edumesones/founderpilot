"""Slack integration for FounderPilot."""
from src.integrations.slack.app import create_slack_app, get_slack_app
from src.integrations.slack.blocks import (
    build_email_notification,
    build_invoice_notification,
    build_meeting_notification,
    build_success_blocks,
    build_edit_modal,
    build_welcome_message,
)

__all__ = [
    "create_slack_app",
    "get_slack_app",
    "build_email_notification",
    "build_invoice_notification",
    "build_meeting_notification",
    "build_success_blocks",
    "build_edit_modal",
    "build_welcome_message",
]
