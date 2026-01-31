"""Classify email node - categorizes email using LLM."""

import json
from datetime import datetime

from src.agents.inbox_pilot.prompts.classify import (
    CLASSIFICATION_SYSTEM_PROMPT,
    build_classification_prompt,
)
from src.agents.inbox_pilot.state import ClassificationResult, InboxState
from src.core.llm import LLMRouter


async def classify_email(
    state: InboxState,
    llm_router: LLMRouter,
) -> dict:
    """Classify email using LLM.

    Uses GPT-4o-mini for fast, cost-effective classification.
    Returns category (urgent/important/routine/spam) and confidence score.

    Args:
        state: Current agent state with email data
        llm_router: LLM provider router

    Returns:
        State update with classification result
    """
    email = state.get("email")

    if not email:
        return {
            "classification": None,
            "error": "No email data available for classification",
            "steps": state.get("steps", []) + [{
                "node": "classify",
                "timestamp": datetime.utcnow().isoformat(),
                "result": None,
                "error": "No email data",
            }],
        }

    try:
        # Build the prompt
        user_prompt = build_classification_prompt(email)

        # Call the LLM
        response = await llm_router.call(
            task_type="classify",
            system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # Parse JSON response
        classification: ClassificationResult = json.loads(response)

        # Validate required fields
        if "category" not in classification or "confidence" not in classification:
            raise ValueError("Invalid classification response: missing required fields")

        # Ensure confidence is in valid range
        classification["confidence"] = max(0.0, min(1.0, classification["confidence"]))

        step = {
            "node": "classify",
            "timestamp": datetime.utcnow().isoformat(),
            "result": classification,
            "error": None,
        }

        return {
            "classification": classification,
            "steps": state.get("steps", []) + [step],
        }

    except json.JSONDecodeError as e:
        step = {
            "node": "classify",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": f"Failed to parse LLM response: {str(e)}",
        }

        # Default to escalation on parse error
        return {
            "classification": {
                "category": "important",
                "confidence": 0.0,
                "reasoning": "Classification failed - defaulting to escalation",
                "suggested_action": "escalate",
            },
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step = {
            "node": "classify",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": str(e),
        }

        return {
            "classification": {
                "category": "important",
                "confidence": 0.0,
                "reasoning": f"Classification error: {str(e)}",
                "suggested_action": "escalate",
            },
            "error": f"Classification failed: {str(e)}",
            "steps": state.get("steps", []) + [step],
        }
