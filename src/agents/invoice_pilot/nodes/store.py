"""Store invoice node - saves invoice to database with audit trail."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.invoice_pilot.state import InvoiceState
from src.models.invoice import Invoice, InvoiceAction, InvoiceStatus


async def store_invoice(
    state: InvoiceState,
    db_session: AsyncSession,
) -> dict:
    """Store confirmed invoice in database.

    Creates Invoice record and logs initial action to audit trail.
    Handles both auto-confirmed (high confidence) and human-confirmed invoices.

    Args:
        state: Current agent state with extraction data
        db_session: Database session for transaction

    Returns:
        State update with invoice_id and stored flag
    """
    extraction = state.get("extraction")
    detection = state.get("detection")
    human_decision = state.get("human_decision")
    edited_data = state.get("edited_data")

    if not extraction or not detection:
        return {
            "stored": False,
            "error": "Cannot store - missing extraction or detection data",
            "steps": state.get("steps", []) + [{
                "node": "store_invoice",
                "timestamp": datetime.utcnow().isoformat(),
                "result": None,
                "error": "Missing data",
            }],
        }

    try:
        # Use edited data if provided, otherwise use extracted data
        invoice_data = edited_data if edited_data else extraction["data"]

        # Determine initial status
        if invoice_data.get("amount_paid") and invoice_data["amount_paid"] >= invoice_data.get("amount_total", 0):
            initial_status = InvoiceStatus.PAID
        elif invoice_data.get("due_date"):
            days_until_due = (invoice_data["due_date"] - datetime.utcnow()).days
            if days_until_due < 0:
                initial_status = InvoiceStatus.OVERDUE
            else:
                initial_status = InvoiceStatus.SENT
        else:
            initial_status = InvoiceStatus.SENT

        # Create invoice record
        invoice = Invoice(
            tenant_id=state["tenant_id"],
            gmail_message_id=state["gmail_message_id"],
            invoice_number=invoice_data.get("invoice_number"),
            client_name=invoice_data.get("client_name"),
            client_email=invoice_data.get("client_email"),
            amount_total=invoice_data.get("amount_total"),
            amount_paid=invoice_data.get("amount_paid", 0.0),
            currency=invoice_data.get("currency", "USD"),
            issue_date=invoice_data.get("issue_date"),
            due_date=invoice_data.get("due_date"),
            status=initial_status,
            pdf_url=detection.get("pdf_url"),
            confidence=extraction.get("confidence", 0.0),
            notes=None,
        )

        db_session.add(invoice)
        await db_session.flush()  # Get the invoice ID

        # Create audit log entry
        action_type = "detected" if not human_decision else "confirmed"
        actor = "system" if not human_decision else "human"

        action = InvoiceAction(
            invoice_id=invoice.id,
            workflow_id=state.get("trace_id"),
            action_type=action_type,
            actor=actor,
            details={
                "confidence": extraction.get("confidence"),
                "human_decision": human_decision,
                "edited": bool(edited_data),
                "missing_fields": extraction.get("missing_fields", []),
            },
            timestamp=datetime.utcnow(),
        )

        db_session.add(action)
        await db_session.commit()

        step = {
            "node": "store_invoice",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "invoice_id": invoice.id,
                "status": initial_status.value,
                "action_type": action_type,
                "actor": actor,
            },
            "error": None,
        }

        return {
            "invoice_id": invoice.id,
            "stored": True,
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        await db_session.rollback()

        step = {
            "node": "store_invoice",
            "timestamp": datetime.utcnow().isoformat(),
            "result": None,
            "error": str(e),
        }

        return {
            "invoice_id": None,
            "stored": False,
            "error": f"Failed to store invoice: {str(e)}",
            "steps": state.get("steps", []) + [step],
        }
