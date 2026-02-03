"""
Unit tests for Invoice models.

Tests Invoice, InvoiceReminder, and InvoiceAction models including:
- Model creation and field validation
- Status transitions
- Relationships between models
- Computed properties (amount_remaining, is_overdue, days_overdue)
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from src.models.invoice_pilot.invoice import Invoice, InvoiceAction, InvoiceReminder


class TestInvoiceModel:
    """Tests for Invoice model."""

    def test_create_invoice(self, db_session):
        """Test creating an invoice with all required fields."""
        tenant_id = uuid4()
        invoice = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg-123",
            invoice_number="INV-2024-001",
            client_name="Acme Corp",
            client_email="billing@acme.com",
            amount_total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            currency="USD",
            issue_date=date(2024, 1, 1),
            due_date=date(2024, 2, 1),
            status="detected",
            confidence=Decimal("0.95"),
        )
        db_session.add(invoice)
        db_session.commit()

        assert invoice.id is not None
        assert invoice.tenant_id == tenant_id
        assert invoice.invoice_number == "INV-2024-001"
        assert invoice.client_name == "Acme Corp"
        assert invoice.amount_total == Decimal("1000.00")
        assert invoice.status == "detected"

    def test_invoice_defaults(self, db_session):
        """Test default values for invoice fields."""
        tenant_id = uuid4()
        invoice = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg-456",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("500.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        assert invoice.amount_paid == Decimal("0.00")
        assert invoice.currency == "USD"
        assert invoice.status == "detected"
        assert invoice.confidence == Decimal("0.00")

    def test_amount_remaining_property(self, db_session):
        """Test amount_remaining computed property."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-789",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            amount_paid=Decimal("300.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        assert invoice.amount_remaining == Decimal("700.00")

    def test_amount_remaining_fully_paid(self, db_session):
        """Test amount_remaining when fully paid."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-101",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            amount_paid=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        assert invoice.amount_remaining == Decimal("0.00")

    def test_is_overdue_property_past_due(self, db_session):
        """Test is_overdue for past due invoice."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-102",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today() - timedelta(days=40),
            due_date=date.today() - timedelta(days=10),
            status="overdue",
        )
        db_session.add(invoice)
        db_session.commit()

        assert invoice.is_overdue is True

    def test_is_overdue_property_not_due_yet(self, db_session):
        """Test is_overdue for invoice not yet due."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-103",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="pending",
        )
        db_session.add(invoice)
        db_session.commit()

        assert invoice.is_overdue is False

    def test_is_overdue_property_paid_invoice(self, db_session):
        """Test is_overdue returns False for paid invoices even if past due date."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-104",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            amount_paid=Decimal("1000.00"),
            issue_date=date.today() - timedelta(days=40),
            due_date=date.today() - timedelta(days=10),
            status="paid",
        )
        db_session.add(invoice)
        db_session.commit()

        assert invoice.is_overdue is False

    def test_is_overdue_property_rejected_invoice(self, db_session):
        """Test is_overdue returns False for rejected invoices."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-105",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today() - timedelta(days=40),
            due_date=date.today() - timedelta(days=10),
            status="rejected",
        )
        db_session.add(invoice)
        db_session.commit()

        assert invoice.is_overdue is False

    def test_days_overdue_property_past_due(self, db_session):
        """Test days_overdue for past due invoice."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-106",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today() - timedelta(days=40),
            due_date=date.today() - timedelta(days=10),
            status="overdue",
        )
        db_session.add(invoice)
        db_session.commit()

        assert invoice.days_overdue == 10

    def test_days_overdue_property_not_due_yet(self, db_session):
        """Test days_overdue for invoice not yet due (should be negative)."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-107",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="pending",
        )
        db_session.add(invoice)
        db_session.commit()

        assert invoice.days_overdue == -30

    def test_status_transitions(self, db_session):
        """Test various status transitions."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-108",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="detected",
        )
        db_session.add(invoice)
        db_session.commit()

        # detected -> pending
        invoice.status = "pending"
        db_session.commit()
        assert invoice.status == "pending"

        # pending -> partial
        invoice.amount_paid = Decimal("500.00")
        invoice.status = "partial"
        db_session.commit()
        assert invoice.status == "partial"

        # partial -> paid
        invoice.amount_paid = Decimal("1000.00")
        invoice.status = "paid"
        db_session.commit()
        assert invoice.status == "paid"

    def test_invoice_relationship_to_reminders(self, db_session):
        """Test invoice-to-reminders relationship."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-109",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        # Add reminders
        reminder1 = InvoiceReminder(
            invoice_id=invoice.id,
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=27),
            type="pre_due",
            draft_message="Gentle reminder",
        )
        reminder2 = InvoiceReminder(
            invoice_id=invoice.id,
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=33),
            type="post_due_3d",
            draft_message="Payment overdue",
        )
        db_session.add_all([reminder1, reminder2])
        db_session.commit()

        # Refresh to load relationships
        db_session.refresh(invoice)
        assert len(invoice.reminders) == 2
        assert invoice.reminders[0].type == "pre_due"
        assert invoice.reminders[1].type == "post_due_3d"

    def test_invoice_relationship_to_actions(self, db_session):
        """Test invoice-to-actions relationship."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-110",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        # Add actions
        action1 = InvoiceAction(
            invoice_id=invoice.id,
            action_type="detected",
            actor="agent",
            details={"confidence": 0.95},
            timestamp=datetime.now(timezone.utc),
        )
        action2 = InvoiceAction(
            invoice_id=invoice.id,
            action_type="confirmed",
            actor=str(uuid4()),
            details={},
            timestamp=datetime.now(timezone.utc),
        )
        db_session.add_all([action1, action2])
        db_session.commit()

        # Refresh to load relationships
        db_session.refresh(invoice)
        assert len(invoice.actions) == 2
        assert invoice.actions[0].action_type == "detected"
        assert invoice.actions[1].action_type == "confirmed"

    def test_unique_constraint_tenant_gmail_message(self, db_session):
        """Test unique constraint on tenant_id + gmail_message_id."""
        tenant_id = uuid4()
        invoice1 = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg-unique-test",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice1)
        db_session.commit()

        # Try to create duplicate
        invoice2 = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg-unique-test",
            client_name="Different Client",
            client_email="different@client.com",
            amount_total=Decimal("2000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice2)

        with pytest.raises(Exception):  # Should raise integrity error
            db_session.commit()

    def test_invoice_repr(self, db_session):
        """Test string representation of invoice."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-repr-test",
            invoice_number="INV-999",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1234.56"),
            currency="EUR",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="pending",
        )
        db_session.add(invoice)
        db_session.commit()

        repr_str = repr(invoice)
        assert "Invoice" in repr_str
        assert "INV-999" in repr_str
        assert "Test Client" in repr_str
        assert "1234.56" in repr_str
        assert "EUR" in repr_str
        assert "pending" in repr_str


class TestInvoiceReminderModel:
    """Tests for InvoiceReminder model."""

    def test_create_reminder(self, db_session):
        """Test creating a reminder."""
        # Create invoice first
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-reminder-test",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        # Create reminder
        scheduled = datetime.now(timezone.utc) + timedelta(days=27)
        reminder = InvoiceReminder(
            invoice_id=invoice.id,
            scheduled_at=scheduled,
            type="pre_due",
            draft_message="Friendly reminder about upcoming payment",
            status="pending",
        )
        db_session.add(reminder)
        db_session.commit()

        assert reminder.id is not None
        assert reminder.invoice_id == invoice.id
        assert reminder.type == "pre_due"
        assert reminder.status == "pending"
        assert reminder.draft_message == "Friendly reminder about upcoming payment"

    def test_reminder_defaults(self, db_session):
        """Test default values for reminder."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-reminder-defaults",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        reminder = InvoiceReminder(
            invoice_id=invoice.id,
            scheduled_at=datetime.now(timezone.utc),
            type="pre_due",
            draft_message="Test message",
        )
        db_session.add(reminder)
        db_session.commit()

        assert reminder.status == "pending"
        assert reminder.response_received is False
        assert reminder.sent_at is None
        assert reminder.final_message is None
        assert reminder.approved_by is None

    def test_reminder_status_transitions(self, db_session):
        """Test reminder status transitions."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-reminder-status",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        reminder = InvoiceReminder(
            invoice_id=invoice.id,
            scheduled_at=datetime.now(timezone.utc),
            type="pre_due",
            draft_message="Test message",
            status="pending",
        )
        db_session.add(reminder)
        db_session.commit()

        # pending -> approved
        reminder.status = "approved"
        reminder.approved_by = str(uuid4())
        db_session.commit()
        assert reminder.status == "approved"

        # approved -> sent
        reminder.status = "sent"
        reminder.sent_at = datetime.now(timezone.utc)
        db_session.commit()
        assert reminder.status == "sent"
        assert reminder.sent_at is not None

    def test_reminder_with_edited_message(self, db_session):
        """Test reminder with human-edited message."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-reminder-edit",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        reminder = InvoiceReminder(
            invoice_id=invoice.id,
            scheduled_at=datetime.now(timezone.utc),
            type="pre_due",
            draft_message="Original AI message",
            final_message="Edited by human",
            status="approved",
        )
        db_session.add(reminder)
        db_session.commit()

        assert reminder.draft_message == "Original AI message"
        assert reminder.final_message == "Edited by human"

    def test_reminder_relationship_to_invoice(self, db_session):
        """Test reminder-to-invoice relationship."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-reminder-rel",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        reminder = InvoiceReminder(
            invoice_id=invoice.id,
            scheduled_at=datetime.now(timezone.utc),
            type="pre_due",
            draft_message="Test",
        )
        db_session.add(reminder)
        db_session.commit()

        # Refresh to load relationship
        db_session.refresh(reminder)
        assert reminder.invoice.id == invoice.id
        assert reminder.invoice.client_name == "Test Client"

    def test_reminder_repr(self, db_session):
        """Test string representation of reminder."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-reminder-repr",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        scheduled = datetime.now(timezone.utc)
        reminder = InvoiceReminder(
            invoice_id=invoice.id,
            scheduled_at=scheduled,
            type="post_due_7d",
            draft_message="Test",
            status="pending",
        )
        db_session.add(reminder)
        db_session.commit()

        repr_str = repr(reminder)
        assert "InvoiceReminder" in repr_str
        assert "post_due_7d" in repr_str
        assert "pending" in repr_str


class TestInvoiceActionModel:
    """Tests for InvoiceAction model."""

    def test_create_action(self, db_session):
        """Test creating an invoice action."""
        # Create invoice first
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-action-test",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        # Create action
        action = InvoiceAction(
            invoice_id=invoice.id,
            action_type="detected",
            actor="agent",
            details={"confidence": 0.95, "source": "gmail"},
            timestamp=datetime.now(timezone.utc),
        )
        db_session.add(action)
        db_session.commit()

        assert action.id is not None
        assert action.invoice_id == invoice.id
        assert action.action_type == "detected"
        assert action.actor == "agent"
        assert action.details["confidence"] == 0.95

    def test_action_with_workflow_id(self, db_session):
        """Test action with workflow_id."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-action-workflow",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        workflow_id = uuid4()
        action = InvoiceAction(
            invoice_id=invoice.id,
            workflow_id=workflow_id,
            action_type="reminder_sent",
            actor="agent",
            details={"reminder_type": "post_due_3d"},
            timestamp=datetime.now(timezone.utc),
        )
        db_session.add(action)
        db_session.commit()

        assert action.workflow_id == workflow_id

    def test_action_relationship_to_invoice(self, db_session):
        """Test action-to-invoice relationship."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-action-rel",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        action = InvoiceAction(
            invoice_id=invoice.id,
            action_type="confirmed",
            actor=str(uuid4()),
            details={},
            timestamp=datetime.now(timezone.utc),
        )
        db_session.add(action)
        db_session.commit()

        # Refresh to load relationship
        db_session.refresh(action)
        assert action.invoice.id == invoice.id
        assert action.invoice.client_name == "Test Client"

    def test_action_audit_trail(self, db_session):
        """Test multiple actions create audit trail."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-action-audit",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        # Create action sequence
        now = datetime.now(timezone.utc)
        actions = [
            InvoiceAction(
                invoice_id=invoice.id,
                action_type="detected",
                actor="agent",
                details={},
                timestamp=now,
            ),
            InvoiceAction(
                invoice_id=invoice.id,
                action_type="confirmed",
                actor=str(uuid4()),
                details={},
                timestamp=now + timedelta(minutes=5),
            ),
            InvoiceAction(
                invoice_id=invoice.id,
                action_type="reminder_sent",
                actor="agent",
                details={"type": "pre_due"},
                timestamp=now + timedelta(days=27),
            ),
            InvoiceAction(
                invoice_id=invoice.id,
                action_type="marked_paid",
                actor=str(uuid4()),
                details={"amount": "1000.00"},
                timestamp=now + timedelta(days=28),
            ),
        ]
        db_session.add_all(actions)
        db_session.commit()

        # Refresh invoice and check actions
        db_session.refresh(invoice)
        assert len(invoice.actions) == 4
        assert invoice.actions[0].action_type == "detected"
        assert invoice.actions[-1].action_type == "marked_paid"

    def test_action_repr(self, db_session):
        """Test string representation of action."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-action-repr",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        action = InvoiceAction(
            invoice_id=invoice.id,
            action_type="reminder_sent",
            actor="agent",
            details={},
            timestamp=datetime.now(timezone.utc),
        )
        db_session.add(action)
        db_session.commit()

        repr_str = repr(action)
        assert "InvoiceAction" in repr_str
        assert "reminder_sent" in repr_str
        assert "agent" in repr_str


class TestCascadeDeletes:
    """Test cascade delete behavior."""

    def test_delete_invoice_cascades_to_reminders(self, db_session):
        """Test that deleting invoice also deletes reminders."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-cascade-reminder",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        reminder = InvoiceReminder(
            invoice_id=invoice.id,
            scheduled_at=datetime.now(timezone.utc),
            type="pre_due",
            draft_message="Test",
        )
        db_session.add(reminder)
        db_session.commit()

        reminder_id = reminder.id

        # Delete invoice
        db_session.delete(invoice)
        db_session.commit()

        # Check reminder is gone
        deleted_reminder = db_session.query(InvoiceReminder).filter_by(id=reminder_id).first()
        assert deleted_reminder is None

    def test_delete_invoice_cascades_to_actions(self, db_session):
        """Test that deleting invoice also deletes actions."""
        invoice = Invoice(
            tenant_id=uuid4(),
            gmail_message_id="msg-cascade-action",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
        )
        db_session.add(invoice)
        db_session.commit()

        action = InvoiceAction(
            invoice_id=invoice.id,
            action_type="detected",
            actor="agent",
            details={},
            timestamp=datetime.now(timezone.utc),
        )
        db_session.add(action)
        db_session.commit()

        action_id = action.id

        # Delete invoice
        db_session.delete(invoice)
        db_session.commit()

        # Check action is gone
        deleted_action = db_session.query(InvoiceAction).filter_by(id=action_id).first()
        assert deleted_action is None
