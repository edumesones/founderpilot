"""Extract data node - uses multimodal LLM to extract invoice fields from PDF."""

import json
from datetime import datetime

from src.agents.invoice_pilot.prompts.extraction import (
    INVOICE_EXTRACTION_SYSTEM_PROMPT,
    build_extraction_prompt,
)
from src.agents.invoice_pilot.state import ExtractionResult, InvoiceData, InvoiceState
from src.core.llm import LLMRouter


async def extract_data(
    state: InvoiceState,
    llm_router: LLMRouter,
) -> dict:
    """Extract structured invoice data from PDF using multimodal LLM.

    Uses GPT-4o (multimodal) for PDF parsing and structured extraction.
    Returns extracted data with confidence score and missing fields list.

    Args:
        state: Current agent state with email data and detection result
        llm_router: LLM provider router

    Returns:
        State update with extraction result
    """
    email_data = state.get("email_data")
    detection = state.get("detection")

    if not email_data:
        return {
            "extraction": None,
            "error": "No email data available for extraction",
            "steps": state.get("steps", []) + [{
                "node": "extract_data",
                "timestamp": datetime.utcnow().isoformat(),
                "result": None,
                "error": "No email data",
            }],
        }

    if not detection or not detection.get("is_invoice"):
        return {
            "extraction": None,
            "error": "Cannot extract - email is not an invoice",
            "steps": state.get("steps", []) + [{
                "node": "extract_data",
                "timestamp": datetime.utcnow().isoformat(),
                "result": None,
                "error": "Not an invoice",
            }],
        }

    try:
        # Get PDF attachment
        attachments = email_data.get("attachments", [])
        pdf_attachments = [
            att for att in attachments
            if att.get("mimeType") == "application/pdf"
        ]

        if not pdf_attachments:
            raise ValueError("No PDF attachment found")

        # Use first PDF (most likely the invoice)
        pdf_attachment = pdf_attachments[0]
        pdf_url = pdf_attachment.get("url") or detection.get("pdf_url")

        if not pdf_url:
            raise ValueError("PDF URL not available")

        # Build the prompt
        user_prompt = build_extraction_prompt(email_data)

        # Call the multimodal LLM with PDF image/content
        response = await llm_router.call(
            task_type="extract",  # Use extraction task type
            system_prompt=INVOICE_EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            attachments=[{
                "type": "pdf",
                "url": pdf_url,
            }],
        )

        # Parse JSON response
        extraction_raw = json.loads(response)

        # Validate and build invoice data
        invoice_data: InvoiceData = {
            "invoice_number": extraction_raw.get("invoice_number"),
            "client_name": extraction_raw.get("client_name"),
            "client_email": extraction_raw.get("client_email"),
            "amount_total": extraction_raw.get("amount_total"),
            "currency": extraction_raw.get("currency"),
            "issue_date": _parse_date(extraction_raw.get("issue_date")),
            "due_date": _parse_date(extraction_raw.get("due_date")),
            "line_items": extraction_raw.get("line_items"),
        }

        # Build extraction result
        extraction: ExtractionResult = {
            "data": invoice_data,
            "confidence": max(0.0, min(1.0, float(extraction_raw.get("confidence", 0.0)))),
            "missing_fields": extraction_raw.get("missing_fields", []),
        }

        step = {
            "node": "extract_data",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "confidence": extraction["confidence"],
                "missing_fields": extraction["missing_fields"],
                "has_invoice_number": bool(invoice_data.get("invoice_number")),
                "has_client_name": bool(invoice_data.get("client_name")),
                "has_amount": invoice_data.get("amount_total") is not None,
            },
            "error": None,
        }

        return {
            "extraction": extraction,
            "steps": state.get("steps", []) + [step],
        }

    except json.JSONDecodeError as e:
        step = {
            "node": "extract_data",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": f"Failed to parse LLM response: {str(e)}",
        }

        # Return low-confidence extraction with error
        return {
            "extraction": {
                "data": {
                    "invoice_number": None,
                    "client_name": None,
                    "client_email": None,
                    "amount_total": None,
                    "currency": None,
                    "issue_date": None,
                    "due_date": None,
                    "line_items": None,
                },
                "confidence": 0.0,
                "missing_fields": ["all"],
            },
            "error": f"Extraction parsing failed: {str(e)}",
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step = {
            "node": "extract_data",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": str(e),
        }

        return {
            "extraction": {
                "data": {
                    "invoice_number": None,
                    "client_name": None,
                    "client_email": None,
                    "amount_total": None,
                    "currency": None,
                    "issue_date": None,
                    "due_date": None,
                    "line_items": None,
                },
                "confidence": 0.0,
                "missing_fields": ["all"],
            },
            "error": f"Extraction failed: {str(e)}",
            "steps": state.get("steps", []) + [step],
        }


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse ISO date string to datetime object.

    Args:
        date_str: Date string in YYYY-MM-DD format or None

    Returns:
        datetime object or None if parsing fails
    """
    if not date_str:
        return None

    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None
