"""Detect invoice node - uses LLM to identify if email contains an invoice."""

import json
from datetime import datetime

from src.agents.invoice_pilot.prompts.detection import (
    INVOICE_DETECTION_SYSTEM_PROMPT,
    build_detection_prompt,
)
from src.agents.invoice_pilot.state import DetectionResult, InvoiceState
from src.core.llm import LLMRouter


async def detect_invoice(
    state: InvoiceState,
    llm_router: LLMRouter,
) -> dict:
    """Detect if email contains an invoice using LLM.

    Uses fast, cost-effective model (GPT-4o-mini) for binary classification.
    Returns detection result with confidence score.

    Args:
        state: Current agent state with email data
        llm_router: LLM provider router

    Returns:
        State update with detection result
    """
    email_data = state.get("email_data")

    if not email_data:
        return {
            "detection": None,
            "error": "No email data available for detection",
            "steps": state.get("steps", []) + [{
                "node": "detect_invoice",
                "timestamp": datetime.utcnow().isoformat(),
                "result": None,
                "error": "No email data",
            }],
        }

    try:
        # Build the prompt
        user_prompt = build_detection_prompt(email_data)

        # Call the LLM
        response = await llm_router.call(
            task_type="classify",  # Use classification task type
            system_prompt=INVOICE_DETECTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # Parse JSON response
        detection_raw = json.loads(response)

        # Validate required fields
        if "is_invoice" not in detection_raw or "confidence" not in detection_raw:
            raise ValueError("Invalid detection response: missing required fields")

        # Build detection result
        detection: DetectionResult = {
            "is_invoice": bool(detection_raw["is_invoice"]),
            "confidence": max(0.0, min(1.0, float(detection_raw["confidence"]))),
            "reasoning": detection_raw.get("reasoning", ""),
            "gmail_message_id": state["gmail_message_id"],
            "pdf_url": detection_raw.get("pdf_url"),
        }

        # If not an invoice, short-circuit the flow
        if not detection["is_invoice"]:
            return {
                "detection": detection,
                "error": f"Not an invoice (confidence: {detection['confidence']:.2f})",
                "steps": state.get("steps", []) + [{
                    "node": "detect_invoice",
                    "timestamp": datetime.utcnow().isoformat(),
                    "result": detection,
                    "error": "Not an invoice",
                }],
            }

        step = {
            "node": "detect_invoice",
            "timestamp": datetime.utcnow().isoformat(),
            "result": detection,
            "error": None,
        }

        return {
            "detection": detection,
            "steps": state.get("steps", []) + [step],
        }

    except json.JSONDecodeError as e:
        step = {
            "node": "detect_invoice",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": f"Failed to parse LLM response: {str(e)}",
        }

        # Default to not an invoice on parse error
        return {
            "detection": {
                "is_invoice": False,
                "confidence": 0.0,
                "reasoning": "Detection failed - could not parse LLM response",
                "gmail_message_id": state["gmail_message_id"],
                "pdf_url": None,
            },
            "error": f"Detection parsing failed: {str(e)}",
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step = {
            "node": "detect_invoice",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": str(e),
        }

        return {
            "detection": {
                "is_invoice": False,
                "confidence": 0.0,
                "reasoning": f"Detection error: {str(e)}",
                "gmail_message_id": state["gmail_message_id"],
                "pdf_url": None,
            },
            "error": f"Detection failed: {str(e)}",
            "steps": state.get("steps", []) + [step],
        }
