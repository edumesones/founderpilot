"""Prompts for InboxPilot agent."""

from src.agents.inbox_pilot.prompts.classify import (
    CLASSIFICATION_SYSTEM_PROMPT,
    build_classification_prompt,
)
from src.agents.inbox_pilot.prompts.draft import (
    DRAFT_SYSTEM_PROMPT,
    build_draft_prompt,
)

__all__ = [
    "CLASSIFICATION_SYSTEM_PROMPT",
    "build_classification_prompt",
    "DRAFT_SYSTEM_PROMPT",
    "build_draft_prompt",
]
