"""Draft response node - generates email response using LLM."""

import json
from datetime import datetime

from src.agents.inbox_pilot.prompts.draft import (
    DRAFT_SYSTEM_PROMPT,
    build_draft_prompt,
)
from src.agents.inbox_pilot.state import DraftResult, InboxState
from src.core.llm import LLMRouter


async def draft_response(
    state: InboxState,
    llm_router: LLMRouter,
    email_signature: str | None = None,
) -> dict:
    """Generate draft response using LLM.

    Uses Claude 3.5 Sonnet for high-quality drafts.
    Only called for routine emails that could benefit from a template response.

    Args:
        state: Current agent state with email and classification
        llm_router: LLM provider router
        email_signature: User's email signature (optional)

    Returns:
        State update with draft result
    """
    email = state.get("email")
    classification = state.get("classification")

    if not email:
        return {
            "draft": None,
            "error": "No email data available for drafting",
            "steps": state.get("steps", []) + [{
                "node": "draft_response",
                "timestamp": datetime.utcnow().isoformat(),
                "result": None,
                "error": "No email data",
            }],
        }

    if not classification:
        return {
            "draft": None,
            "error": "No classification available for drafting",
            "steps": state.get("steps", []) + [{
                "node": "draft_response",
                "timestamp": datetime.utcnow().isoformat(),
                "result": None,
                "error": "No classification",
            }],
        }

    try:
        # Build the prompt
        user_prompt = build_draft_prompt(
            email=email,
            classification=classification,
            signature=email_signature,
        )

        # Call the LLM (use generate task type for Sonnet)
        response = await llm_router.call(
            task_type="generate",
            system_prompt=DRAFT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # Parse JSON response
        draft: DraftResult = json.loads(response)

        # Validate required fields
        if "content" not in draft or "confidence" not in draft:
            raise ValueError("Invalid draft response: missing required fields")

        # Ensure confidence is in valid range
        draft["confidence"] = max(0.0, min(1.0, draft["confidence"]))

        # Set default tone if not provided
        if "tone" not in draft:
            draft["tone"] = "professional"

        step = {
            "node": "draft_response",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "content_length": len(draft.get("content", "")),
                "confidence": draft.get("confidence"),
                "tone": draft.get("tone"),
            },
            "error": None,
        }

        return {
            "draft": draft,
            "steps": state.get("steps", []) + [step],
        }

    except json.JSONDecodeError as e:
        step = {
            "node": "draft_response",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": f"Failed to parse LLM response: {str(e)}",
        }

        return {
            "draft": None,
            "needs_human_review": True,
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step = {
            "node": "draft_response",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": str(e),
        }

        return {
            "draft": None,
            "error": f"Draft generation failed: {str(e)}",
            "needs_human_review": True,
            "steps": state.get("steps", []) + [step],
        }
