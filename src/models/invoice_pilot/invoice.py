"""Invoice models for tracking invoices, reminders, and actions."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import (
    DECIMAL,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from src.models.user import User


class Invoice(Base, UUIDMixin, TimestampMixin):
    """
    Invoice model for tracking outgoing invoices.

    Represents an invoice detected from Gmail, extracted via LLM,
    and tracked for payment reminders.
    """

    __tablename__ = "invoices"

    # Tenant isolation (links to User as tenant)
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Gmail reference
    gmail_message_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Gmail message ID of the invoice email",
    )

    # Invoice details
    invoice_number: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Invoice number extracted from PDF/email",
    )

    client_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Client name or company",
    )

    client_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Client email address for reminders",
    )

    # Financial details
    amount_total: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False,
        comment="Total invoice amount",
    )

    amount_paid: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Amount paid (for partial payments)",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
        comment="ISO 4217 currency code (USD, EUR, GBP, etc)",
    )

    # Dates
    issue_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date invoice was issued",
    )

    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Payment due date",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="detected",
        index=True,
        comment="Status: detected, pending, overdue, partial, paid, rejected",
    )

    # LLM extraction metadata
    confidence: Mapped[float] = mapped_column(
        DECIMAL(3, 2),
        nullable=False,
        default=0.0,
        comment="LLM extraction confidence (0.0-1.0)",
    )

    # File storage
    pdf_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="URL or path to stored invoice PDF",
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User notes or comments",
    )

    # Relationships
    reminders: Mapped[List["InvoiceReminder"]] = relationship(
        "InvoiceReminder",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceReminder.scheduled_at",
    )

    actions: Mapped[List["InvoiceAction"]] = relationship(
        "InvoiceAction",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceAction.timestamp",
    )

    # Indexes
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "gmail_message_id",
            name="uq_invoice_tenant_gmail_message",
        ),
        Index("idx_invoice_tenant_status", "tenant_id", "status"),
        Index("idx_invoice_tenant_due_date", "tenant_id", "due_date"),
        Index("idx_invoice_status_due_date", "status", "due_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<Invoice(id={self.id}, invoice_number={self.invoice_number}, "
            f"client={self.client_name}, amount={self.amount_total} {self.currency}, "
            f"status={self.status})>"
        )

    @property
    def amount_remaining(self) -> Decimal:
        """Calculate remaining amount to be paid."""
        return self.amount_total - self.amount_paid

    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue based on current date."""
        from datetime import date as date_class

        return self.due_date < date_class.today() and self.status not in [
            "paid",
            "rejected",
        ]

    @property
    def days_overdue(self) -> int:
        """Calculate days overdue (negative if not yet due)."""
        from datetime import date as date_class

        delta = date_class.today() - self.due_date
        return delta.days


class InvoiceReminder(Base, UUIDMixin, TimestampMixin):
    """
    Invoice reminder model for tracking scheduled and sent reminders.

    Represents a reminder draft, approval workflow, and sending status.
    """

    __tablename__ = "invoice_reminders"

    # Foreign key to invoice
    invoice_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scheduling
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When reminder is scheduled to be sent",
    )

    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When reminder was actually sent",
    )

    # Reminder type
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Reminder type: pre_due, post_due_3d, post_due_7d, post_due_14d",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="Status: pending, approved, sent, skipped, rejected",
    )

    # Message content
    draft_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="LLM-generated reminder draft",
    )

    final_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Final message after human edit (if any)",
    )

    # Approval tracking
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User ID who approved the reminder",
    )

    # Response tracking
    response_received: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether client responded to reminder",
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="reminders",
    )

    # Indexes
    __table_args__ = (
        Index("idx_reminder_invoice_status", "invoice_id", "status"),
        Index("idx_reminder_status_scheduled", "status", "scheduled_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<InvoiceReminder(id={self.id}, invoice_id={self.invoice_id}, "
            f"type={self.type}, status={self.status}, scheduled_at={self.scheduled_at})>"
        )


class InvoiceAction(Base, UUIDMixin, TimestampMixin):
    """
    Invoice action model for audit trail.

    Immutable log of all actions taken on an invoice by agent or human.
    """

    __tablename__ = "invoice_actions"

    # Foreign key to invoice
    invoice_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional workflow reference
    workflow_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="LangGraph workflow run ID if applicable",
    )

    # Action details
    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Action type: detected, confirmed, reminder_sent, marked_paid, etc",
    )

    actor: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Who performed action: 'agent' or user_id",
    )

    details: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Action-specific data as JSON",
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When action occurred",
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="actions",
    )

    # Indexes
    __table_args__ = (
        Index("idx_action_invoice_timestamp", "invoice_id", "timestamp"),
        Index("idx_action_type_timestamp", "action_type", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<InvoiceAction(id={self.id}, invoice_id={self.invoice_id}, "
            f"type={self.action_type}, actor={self.actor}, timestamp={self.timestamp})>"
        )
