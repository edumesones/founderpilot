"""Invoice service for CRUD operations and invoice management."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
import logging

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from src.models.invoice_pilot.invoice import Invoice, InvoiceAction
from src.core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service for handling invoice operations."""

    def __init__(self, db: Session):
        self.db = db

    # --- CRUD Operations ---

    def create(
        self,
        tenant_id: UUID,
        gmail_message_id: str,
        client_name: str,
        client_email: str,
        amount_total: Decimal,
        currency: str,
        issue_date: date,
        due_date: date,
        confidence: float,
        invoice_number: Optional[str] = None,
        pdf_url: Optional[str] = None,
        notes: Optional[str] = None,
        status: str = "detected",
    ) -> Invoice:
        """Create a new invoice record."""
        # Check for duplicate gmail_message_id for this tenant
        existing = (
            self.db.query(Invoice)
            .filter(
                Invoice.tenant_id == tenant_id,
                Invoice.gmail_message_id == gmail_message_id,
            )
            .first()
        )

        if existing:
            logger.warning(
                f"Invoice already exists for tenant {tenant_id} with gmail_message_id {gmail_message_id}"
            )
            raise ValidationError("Invoice already exists for this email")

        # Create invoice
        invoice = Invoice(
            tenant_id=tenant_id,
            gmail_message_id=gmail_message_id,
            invoice_number=invoice_number,
            client_name=client_name,
            client_email=client_email,
            amount_total=amount_total,
            amount_paid=Decimal("0.00"),
            currency=currency,
            issue_date=issue_date,
            due_date=due_date,
            status=status,
            confidence=confidence,
            pdf_url=pdf_url,
            notes=notes,
        )

        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        # Log action
        self._log_action(
            invoice_id=invoice.id,
            action_type="detected",
            actor="agent",
            details={
                "confidence": float(confidence),
                "gmail_message_id": gmail_message_id,
            },
        )

        logger.info(f"Created invoice {invoice.id} for tenant {tenant_id}")
        return invoice

    def get(self, invoice_id: UUID, tenant_id: UUID) -> Invoice:
        """Get a single invoice by ID with tenant check."""
        invoice = (
            self.db.query(Invoice)
            .options(
                joinedload(Invoice.reminders),
                joinedload(Invoice.actions),
            )
            .filter(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id,
            )
            .first()
        )

        if not invoice:
            raise NotFoundError(f"Invoice {invoice_id} not found")

        return invoice

    def list(
        self,
        tenant_id: UUID,
        status: Optional[str] = None,
        client_email: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        amount_min: Optional[Decimal] = None,
        amount_max: Optional[Decimal] = None,
        is_overdue: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Invoice]:
        """List invoices with filters."""
        query = self.db.query(Invoice).filter(Invoice.tenant_id == tenant_id)

        # Apply filters
        if status:
            query = query.filter(Invoice.status == status)

        if client_email:
            query = query.filter(Invoice.client_email == client_email)

        if date_from:
            query = query.filter(Invoice.due_date >= date_from)

        if date_to:
            query = query.filter(Invoice.due_date <= date_to)

        if amount_min is not None:
            query = query.filter(Invoice.amount_total >= amount_min)

        if amount_max is not None:
            query = query.filter(Invoice.amount_total <= amount_max)

        if is_overdue is not None:
            today = date.today()
            if is_overdue:
                query = query.filter(
                    and_(
                        Invoice.due_date < today,
                        Invoice.status.notin_(["paid", "rejected"]),
                    )
                )
            else:
                query = query.filter(
                    or_(
                        Invoice.due_date >= today,
                        Invoice.status.in_(["paid", "rejected"]),
                    )
                )

        # Order by due date (oldest first)
        query = query.order_by(Invoice.due_date.asc())

        # Pagination
        query = query.limit(limit).offset(offset)

        return query.all()

    def update(
        self,
        invoice_id: UUID,
        tenant_id: UUID,
        **kwargs,
    ) -> Invoice:
        """Update invoice fields."""
        invoice = self.get(invoice_id, tenant_id)

        # Update allowed fields
        allowed_fields = [
            "invoice_number",
            "client_name",
            "client_email",
            "amount_total",
            "amount_paid",
            "currency",
            "issue_date",
            "due_date",
            "status",
            "confidence",
            "pdf_url",
            "notes",
        ]

        updated_fields = {}
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(invoice, field, value)
                updated_fields[field] = str(value)

        if updated_fields:
            self.db.commit()
            self.db.refresh(invoice)

            # Log action
            self._log_action(
                invoice_id=invoice.id,
                action_type="updated",
                actor="user",
                details={"updated_fields": updated_fields},
            )

            logger.info(f"Updated invoice {invoice_id}: {updated_fields}")

        return invoice

    def delete(self, invoice_id: UUID, tenant_id: UUID) -> None:
        """Delete an invoice (soft delete by status or hard delete)."""
        invoice = self.get(invoice_id, tenant_id)

        # Hard delete (cascade will handle reminders and actions)
        self.db.delete(invoice)
        self.db.commit()

        logger.info(f"Deleted invoice {invoice_id} for tenant {tenant_id}")

    # --- Invoice-specific Operations ---

    def mark_as_paid(
        self,
        invoice_id: UUID,
        tenant_id: UUID,
        amount_paid: Optional[Decimal] = None,
        actor: str = "user",
    ) -> Invoice:
        """Mark invoice as paid (full or partial)."""
        invoice = self.get(invoice_id, tenant_id)

        # If amount not specified, assume full payment
        if amount_paid is None:
            amount_paid = invoice.amount_remaining

        # Update paid amount
        new_total_paid = invoice.amount_paid + amount_paid

        # Validate payment doesn't exceed total
        if new_total_paid > invoice.amount_total:
            raise ValidationError(
                f"Payment amount {amount_paid} exceeds remaining balance {invoice.amount_remaining}"
            )

        invoice.amount_paid = new_total_paid

        # Update status
        if invoice.amount_paid >= invoice.amount_total:
            invoice.status = "paid"
            action_type = "marked_paid"
        else:
            invoice.status = "partial"
            action_type = "marked_partial_paid"

        self.db.commit()
        self.db.refresh(invoice)

        # Log action
        self._log_action(
            invoice_id=invoice.id,
            action_type=action_type,
            actor=actor,
            details={
                "amount_paid": float(amount_paid),
                "total_paid": float(invoice.amount_paid),
                "amount_remaining": float(invoice.amount_remaining),
            },
        )

        logger.info(
            f"Marked invoice {invoice_id} as {invoice.status} (paid {amount_paid})"
        )
        return invoice

    def confirm_invoice(
        self,
        invoice_id: UUID,
        tenant_id: UUID,
        actor: str = "user",
    ) -> Invoice:
        """Confirm a detected invoice (move from detected to pending)."""
        invoice = self.get(invoice_id, tenant_id)

        if invoice.status != "detected":
            raise ValidationError(
                f"Invoice status is {invoice.status}, expected 'detected'"
            )

        invoice.status = "pending"
        self.db.commit()
        self.db.refresh(invoice)

        # Log action
        self._log_action(
            invoice_id=invoice.id,
            action_type="confirmed",
            actor=actor,
            details={},
        )

        logger.info(f"Confirmed invoice {invoice_id}")
        return invoice

    def reject_invoice(
        self,
        invoice_id: UUID,
        tenant_id: UUID,
        reason: Optional[str] = None,
        actor: str = "user",
    ) -> Invoice:
        """Reject a detected invoice (false positive)."""
        invoice = self.get(invoice_id, tenant_id)

        invoice.status = "rejected"
        if reason:
            invoice.notes = (
                f"{invoice.notes}\n\nRejection reason: {reason}"
                if invoice.notes
                else f"Rejection reason: {reason}"
            )

        self.db.commit()
        self.db.refresh(invoice)

        # Log action
        self._log_action(
            invoice_id=invoice.id,
            action_type="rejected",
            actor=actor,
            details={"reason": reason} if reason else {},
        )

        logger.info(f"Rejected invoice {invoice_id}")
        return invoice

    # --- Helpers ---

    def _log_action(
        self,
        invoice_id: UUID,
        action_type: str,
        actor: str,
        details: dict,
        workflow_id: Optional[UUID] = None,
    ) -> InvoiceAction:
        """Log an action in the audit trail."""
        action = InvoiceAction(
            invoice_id=invoice_id,
            workflow_id=workflow_id,
            action_type=action_type,
            actor=actor,
            details=details,
            timestamp=datetime.utcnow(),
        )
        self.db.add(action)
        self.db.commit()
        return action

    # --- Bulk Operations ---

    def get_overdue_invoices(self, tenant_id: UUID) -> list[Invoice]:
        """Get all overdue unpaid invoices for a tenant."""
        today = date.today()
        return (
            self.db.query(Invoice)
            .filter(
                Invoice.tenant_id == tenant_id,
                Invoice.due_date < today,
                Invoice.status.notin_(["paid", "rejected"]),
            )
            .order_by(Invoice.due_date.asc())
            .all()
        )

    def get_invoices_by_client(
        self, tenant_id: UUID, client_email: str
    ) -> list[Invoice]:
        """Get all invoices for a specific client."""
        return (
            self.db.query(Invoice)
            .filter(
                Invoice.tenant_id == tenant_id,
                Invoice.client_email == client_email,
            )
            .order_by(Invoice.due_date.desc())
            .all()
        )

    def count_reminders_for_invoice(self, invoice_id: UUID) -> int:
        """Count number of reminders sent for an invoice."""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            return 0
        return (
            self.db.query(invoice.reminders)
            .filter_by(status="sent")
            .count()
        )
