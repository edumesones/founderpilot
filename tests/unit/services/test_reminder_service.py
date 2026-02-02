"""
Unit tests for ReminderService.

Tests reminder scheduling, approval workflow, and reminder management.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from src.core.exceptions import NotFoundError, ValidationError
from src.models.invoice_pilot.invoice import Invoice, InvoiceReminder
from src.services.invoice_pilot.invoice_service import InvoiceService
from src.services.invoice_pilot.reminder_service import ReminderService


@pytest.fixture
def invoice_service(db_session):
    """Create InvoiceService instance."""
    return InvoiceService(db_session)


@pytest.fixture
def reminder_service(db_session):
    """Create ReminderService instance."""
    return ReminderService(db_session)


@pytest.fixture
def sample_invoice(invoice_service):
    """Create a sample invoice for testing."""
    tenant_id = uuid4()
    return invoice_service.create(
        tenant_id=tenant_id,
        gmail_message_id=f"msg-{uuid4()}",
        client_name="Test Client",
        client_email="test@client.com",
        amount_total=Decimal("1000.00"),
        currency="USD",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        confidence=0.9,
    )


class TestReminderServiceScheduling:
    """Tests for ReminderService.schedule_reminders()."""

    def test_schedule_reminders_default_schedule(self, reminder_service, sample_invoice):
        """Test scheduling reminders with default schedule."""
        reminders = reminder_service.schedule_reminders(sample_invoice)

        # Default schedule: [-3, 3, 7, 14]
        assert len(reminders) == 4
        assert reminders[0].type == "pre_due"
        assert reminders[1].type == "post_due_3d"
        assert reminders[2].type == "post_due_7d"
        assert reminders[3].type == "post_due_14d"

    def test_schedule_reminders_custom_schedule(self, reminder_service, sample_invoice):
        """Test scheduling reminders with custom schedule."""
        custom_schedule = [-7, -3, 1, 5]
        reminders = reminder_service.schedule_reminders(sample_invoice, custom_schedule)

        assert len(reminders) == 4

    def test_schedule_reminders_dates_calculation(
        self, reminder_service, sample_invoice, db_session
    ):
        """Test that reminder dates are calculated correctly."""
        reminders = reminder_service.schedule_reminders(sample_invoice)

        # Check first reminder (3 days before due date)
        expected_date_pre = sample_invoice.due_date - timedelta(days=3)
        assert reminders[0].scheduled_at.date() == expected_date_pre

        # Check last reminder (14 days after due date)
        expected_date_post = sample_invoice.due_date + timedelta(days=14)
        assert reminders[3].scheduled_at.date() == expected_date_post

    def test_schedule_reminders_time_is_9am(self, reminder_service, sample_invoice):
        """Test that reminders are scheduled for 9 AM."""
        reminders = reminder_service.schedule_reminders(sample_invoice)

        for reminder in reminders:
            assert reminder.scheduled_at.hour == 9
            assert reminder.scheduled_at.minute == 0

    def test_schedule_reminders_no_duplicates(
        self, reminder_service, sample_invoice, db_session
    ):
        """Test that duplicate reminders are not created."""
        # Schedule first time
        first_reminders = reminder_service.schedule_reminders(sample_invoice)
        assert len(first_reminders) == 4

        # Try to schedule again
        second_reminders = reminder_service.schedule_reminders(sample_invoice)
        assert len(second_reminders) == 0

        # Verify only 4 reminders exist in DB
        all_reminders = (
            db_session.query(InvoiceReminder)
            .filter_by(invoice_id=sample_invoice.id)
            .all()
        )
        assert len(all_reminders) == 4

    def test_schedule_reminders_status_pending(self, reminder_service, sample_invoice):
        """Test that new reminders have pending status."""
        reminders = reminder_service.schedule_reminders(sample_invoice)

        for reminder in reminders:
            assert reminder.status == "pending"


class TestReminderServiceGet:
    """Tests for ReminderService.get_reminder()."""

    def test_get_reminder(self, reminder_service, sample_invoice):
        """Test getting a reminder by ID."""
        reminders = reminder_service.schedule_reminders(sample_invoice)
        first_reminder = reminders[0]

        fetched = reminder_service.get_reminder(first_reminder.id)
        assert fetched.id == first_reminder.id

    def test_get_reminder_with_invoice_check(self, reminder_service, sample_invoice):
        """Test getting reminder with invoice ID check."""
        reminders = reminder_service.schedule_reminders(sample_invoice)
        first_reminder = reminders[0]

        fetched = reminder_service.get_reminder(
            first_reminder.id, invoice_id=sample_invoice.id
        )
        assert fetched.id == first_reminder.id

    def test_get_nonexistent_reminder_raises_error(self, reminder_service):
        """Test getting nonexistent reminder raises NotFoundError."""
        fake_id = uuid4()

        with pytest.raises(NotFoundError):
            reminder_service.get_reminder(fake_id)

    def test_get_reminder_wrong_invoice_raises_error(
        self, reminder_service, sample_invoice
    ):
        """Test getting reminder with wrong invoice ID raises error."""
        reminders = reminder_service.schedule_reminders(sample_invoice)
        first_reminder = reminders[0]
        wrong_invoice_id = uuid4()

        with pytest.raises(NotFoundError):
            reminder_service.get_reminder(first_reminder.id, invoice_id=wrong_invoice_id)


class TestReminderServiceList:
    """Tests for ReminderService.list_reminders_for_invoice()."""

    def test_list_reminders_for_invoice(self, reminder_service, sample_invoice):
        """Test listing all reminders for an invoice."""
        reminder_service.schedule_reminders(sample_invoice)
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)

        assert len(reminders) == 4

    def test_list_reminders_filter_by_status(
        self, reminder_service, sample_invoice, db_session
    ):
        """Test listing reminders filtered by status."""
        reminder_service.schedule_reminders(sample_invoice)

        # Approve one reminder
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)
        user_id = str(uuid4())
        reminder_service.approve_reminder(reminders[0].id, user_id)

        # List by status
        pending = reminder_service.list_reminders_for_invoice(
            sample_invoice.id, status="pending"
        )
        assert len(pending) == 3

        approved = reminder_service.list_reminders_for_invoice(
            sample_invoice.id, status="approved"
        )
        assert len(approved) == 1

    def test_list_reminders_ordered_by_scheduled_at(
        self, reminder_service, sample_invoice
    ):
        """Test that reminders are ordered by scheduled_at."""
        reminder_service.schedule_reminders(sample_invoice)
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)

        # Should be ordered chronologically
        for i in range(len(reminders) - 1):
            assert reminders[i].scheduled_at <= reminders[i + 1].scheduled_at


class TestReminderServiceGetDue:
    """Tests for ReminderService.get_due_reminders()."""

    def test_get_due_reminders(self, reminder_service, invoice_service, db_session):
        """Test getting reminders that are due."""
        tenant_id = uuid4()

        # Create invoice with due date in the past
        invoice = invoice_service.create(
            tenant_id=tenant_id,
            gmail_message_id=f"msg-{uuid4()}",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today() - timedelta(days=40),
            due_date=date.today() - timedelta(days=10),
            confidence=0.9,
        )

        reminder_service.schedule_reminders(invoice)

        # Get due reminders
        due = reminder_service.get_due_reminders(tenant_id=tenant_id)

        # Should include reminders that are already past their scheduled time
        assert len(due) > 0

    def test_get_due_reminders_with_cutoff(
        self, reminder_service, sample_invoice, db_session
    ):
        """Test getting due reminders with cutoff time."""
        reminder_service.schedule_reminders(sample_invoice)

        # Get reminders due before a future date
        future = datetime.now(timezone.utc) + timedelta(days=35)
        due = reminder_service.get_due_reminders(before=future)

        # Should include all reminders
        assert len(due) == 4

    def test_get_due_reminders_only_pending(
        self, reminder_service, sample_invoice, db_session
    ):
        """Test that only pending reminders are returned."""
        reminder_service.schedule_reminders(sample_invoice)

        # Approve one reminder
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)
        user_id = str(uuid4())
        reminder_service.approve_reminder(reminders[0].id, user_id)

        # Get due reminders - should not include approved one
        future = datetime.now(timezone.utc) + timedelta(days=35)
        due = reminder_service.get_due_reminders(before=future)

        # Should only include pending reminders
        for reminder in due:
            assert reminder.status == "pending"


class TestReminderServiceApprove:
    """Tests for ReminderService.approve_reminder()."""

    def test_approve_reminder(self, reminder_service, sample_invoice, db_session):
        """Test approving a reminder."""
        reminder_service.schedule_reminders(sample_invoice)
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)
        user_id = str(uuid4())

        approved = reminder_service.approve_reminder(reminders[0].id, user_id)

        assert approved.status == "approved"
        assert approved.approved_by == user_id

    def test_approve_reminder_with_message(
        self, reminder_service, sample_invoice, db_session
    ):
        """Test approving reminder with final message."""
        reminder_service.schedule_reminders(sample_invoice)
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)
        user_id = str(uuid4())

        # Set draft message first
        reminder_service.set_draft_message(reminders[0].id, "Draft message")

        approved = reminder_service.approve_reminder(
            reminders[0].id, user_id, final_message="Approved message"
        )

        assert approved.draft_message == "Draft message"
        assert approved.final_message == "Approved message"


class TestReminderServiceEdit:
    """Tests for ReminderService.edit_reminder()."""

    def test_edit_reminder_message(self, reminder_service, sample_invoice, db_session):
        """Test editing a reminder message."""
        reminder_service.schedule_reminders(sample_invoice)
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)

        # Set draft message
        reminder_service.set_draft_message(reminders[0].id, "Original message")

        # Edit it
        edited = reminder_service.edit_reminder(
            reminders[0].id, new_message="Edited message"
        )

        assert edited.final_message == "Edited message"


class TestReminderServiceSkip:
    """Tests for ReminderService.skip_reminder()."""

    def test_skip_reminder(self, reminder_service, sample_invoice, db_session):
        """Test skipping a reminder."""
        reminder_service.schedule_reminders(sample_invoice)
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)
        user_id = str(uuid4())

        skipped = reminder_service.skip_reminder(
            reminders[0].id, user_id, reason="Not needed"
        )

        assert skipped.status == "skipped"


class TestReminderServiceMarkAsSent:
    """Tests for ReminderService.mark_as_sent()."""

    def test_mark_as_sent(self, reminder_service, sample_invoice, db_session):
        """Test marking reminder as sent."""
        reminder_service.schedule_reminders(sample_invoice)
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)
        user_id = str(uuid4())

        # Approve first
        reminder_service.approve_reminder(reminders[0].id, user_id)

        # Mark as sent
        sent = reminder_service.mark_as_sent(reminders[0].id, gmail_message_id="msg-123")

        assert sent.status == "sent"
        assert sent.sent_at is not None

    def test_mark_as_sent_without_approval_raises_error(
        self, reminder_service, sample_invoice
    ):
        """Test that marking unapproved reminder as sent raises error."""
        reminder_service.schedule_reminders(sample_invoice)
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)

        with pytest.raises(ValidationError, match="cannot be sent"):
            reminder_service.mark_as_sent(reminders[0].id, gmail_message_id="msg-123")


class TestReminderServiceResponseReceived:
    """Tests for ReminderService.mark_response_received()."""

    def test_mark_response_received(self, reminder_service, sample_invoice, db_session):
        """Test marking that client responded to reminder."""
        reminder_service.schedule_reminders(sample_invoice)
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)
        user_id = str(uuid4())

        # Send reminder first
        reminder_service.approve_reminder(reminders[0].id, user_id)
        reminder_service.mark_as_sent(reminders[0].id, gmail_message_id="msg-123")

        # Mark response received
        updated = reminder_service.mark_response_received(reminders[0].id)

        assert updated.response_received is True


class TestReminderServiceUtilityMethods:
    """Tests for utility methods."""

    def test_get_reminder_history(self, reminder_service, sample_invoice, db_session):
        """Test getting reminder history for invoice."""
        reminder_service.schedule_reminders(sample_invoice)
        user_id = str(uuid4())

        # Approve and send a reminder
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)
        reminder_service.approve_reminder(reminders[0].id, user_id)
        reminder_service.mark_as_sent(reminders[0].id, gmail_message_id="msg-123")

        # Get history
        history = reminder_service.get_reminder_history(sample_invoice.id)

        assert len(history) >= 1
        assert history[0].status == "sent"

    def test_count_sent_reminders(self, reminder_service, sample_invoice, db_session):
        """Test counting sent reminders."""
        reminder_service.schedule_reminders(sample_invoice)
        user_id = str(uuid4())

        # Initially 0
        count = reminder_service.count_sent_reminders(sample_invoice.id)
        assert count == 0

        # Send two reminders
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)
        for i in range(2):
            reminder_service.approve_reminder(reminders[i].id, user_id)
            reminder_service.mark_as_sent(reminders[i].id, gmail_message_id=f"msg-{i}")

        # Should count 2
        count = reminder_service.count_sent_reminders(sample_invoice.id)
        assert count == 2


class TestReminderServiceSetDraftMessage:
    """Tests for ReminderService.set_draft_message()."""

    def test_set_draft_message(self, reminder_service, sample_invoice, db_session):
        """Test setting draft message for reminder."""
        reminder_service.schedule_reminders(sample_invoice)
        reminders = reminder_service.list_reminders_for_invoice(sample_invoice.id)

        draft_msg = "This is a friendly reminder about your invoice."
        updated = reminder_service.set_draft_message(reminders[0].id, draft_msg)

        assert updated.draft_message == draft_msg
