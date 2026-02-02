"""
Unit tests for InvoiceService.

Tests CRUD operations, filtering, status transitions, and business logic.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.core.exceptions import NotFoundError, ValidationError
from src.models.invoice_pilot.invoice import Invoice, InvoiceAction
from src.services.invoice_pilot.invoice_service import InvoiceService


class TestInvoiceServiceCreate:
    """Tests for InvoiceService.create()."""

    def test_create_invoice(self, db_session):
        """Test creating an invoice."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        invoice = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-123",
            invoice_number="INV-2024-001",
            client_name="Acme Corp",
            client_email="billing@acme.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date(2024, 1, 1),
            due_date=date(2024, 2, 1),
            confidence=0.95,
        )

        assert invoice.id is not None
        assert invoice.tenant_id == tenant_id
        assert invoice.invoice_number == "INV-2024-001"
        assert invoice.client_name == "Acme Corp"
        assert invoice.amount_total == Decimal("1000.00")
        assert invoice.status == "detected"

    def test_create_invoice_with_optional_fields(self, db_session):
        """Test creating invoice with optional fields."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        invoice = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-456",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("500.00"),
            currency="EUR",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.8,
            pdf_url="https://example.com/invoice.pdf",
            notes="Test notes",
        )

        assert invoice.pdf_url == "https://example.com/invoice.pdf"
        assert invoice.notes == "Test notes"

    def test_create_invoice_logs_action(self, db_session):
        """Test that creating invoice logs an action."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        invoice = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-789",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        # Check action was logged
        actions = db_session.query(InvoiceAction).filter_by(invoice_id=invoice.id).all()
        assert len(actions) == 1
        assert actions[0].action_type == "detected"
        assert actions[0].actor == "agent"

    def test_create_duplicate_invoice_raises_error(self, db_session):
        """Test that duplicate gmail_message_id raises error."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        # Create first invoice
        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-duplicate",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        # Try to create duplicate
        with pytest.raises(ValidationError, match="Invoice already exists"):
            service.create(
                tenant_id=tenant_id,
                gmail_message_id="msg-duplicate",
                client_name="Different Client",
                client_email="different@client.com",
                amount_total=Decimal("2000.00"),
                currency="USD",
                issue_date=date.today(),
                due_date=date.today() + timedelta(days=30),
                confidence=0.9,
            )


class TestInvoiceServiceGet:
    """Tests for InvoiceService.get()."""

    def test_get_invoice(self, db_session):
        """Test getting an invoice by ID."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        created_invoice = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-get-test",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        fetched_invoice = service.get(created_invoice.id, tenant_id)
        assert fetched_invoice.id == created_invoice.id
        assert fetched_invoice.client_name == "Test Client"

    def test_get_nonexistent_invoice_raises_error(self, db_session):
        """Test getting nonexistent invoice raises NotFoundError."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()
        fake_id = uuid4()

        with pytest.raises(NotFoundError):
            service.get(fake_id, tenant_id)

    def test_get_invoice_wrong_tenant_raises_error(self, db_session):
        """Test getting invoice with wrong tenant ID raises error."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()
        wrong_tenant_id = uuid4()

        created_invoice = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-wrong-tenant",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        with pytest.raises(NotFoundError):
            service.get(created_invoice.id, wrong_tenant_id)


class TestInvoiceServiceList:
    """Tests for InvoiceService.list()."""

    def test_list_all_invoices(self, db_session):
        """Test listing all invoices for a tenant."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        # Create multiple invoices
        for i in range(3):
            service.create(
                tenant_id=tenant_id,
                gmail_message_id=f"msg-list-{i}",
                client_name=f"Client {i}",
                client_email=f"client{i}@example.com",
                amount_total=Decimal("1000.00"),
                currency="USD",
                issue_date=date.today(),
                due_date=date.today() + timedelta(days=30),
                confidence=0.9,
            )

        invoices = service.list(tenant_id)
        assert len(invoices) == 3

    def test_list_filter_by_status(self, db_session):
        """Test filtering invoices by status."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        # Create invoices with different statuses
        inv1 = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-status-1",
            client_name="Client 1",
            client_email="client1@example.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
            status="detected",
        )

        inv2 = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-status-2",
            client_name="Client 2",
            client_email="client2@example.com",
            amount_total=Decimal("2000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
            status="pending",
        )

        # Update status
        service.update(inv2.id, tenant_id, status="paid")

        # Filter by status
        detected = service.list(tenant_id, status="detected")
        assert len(detected) == 1
        assert detected[0].id == inv1.id

        paid = service.list(tenant_id, status="paid")
        assert len(paid) == 1
        assert paid[0].id == inv2.id

    def test_list_filter_by_client_email(self, db_session):
        """Test filtering invoices by client email."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-email-1",
            client_name="Client A",
            client_email="clienta@example.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-email-2",
            client_name="Client B",
            client_email="clientb@example.com",
            amount_total=Decimal("2000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        filtered = service.list(tenant_id, client_email="clienta@example.com")
        assert len(filtered) == 1
        assert filtered[0].client_email == "clienta@example.com"

    def test_list_filter_by_date_range(self, db_session):
        """Test filtering invoices by date range."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-date-1",
            client_name="Client 1",
            client_email="client1@example.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=10),
            confidence=0.9,
        )

        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-date-2",
            client_name="Client 2",
            client_email="client2@example.com",
            amount_total=Decimal("2000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        # Filter by date range
        filtered = service.list(
            tenant_id,
            date_from=date.today() + timedelta(days=5),
            date_to=date.today() + timedelta(days=15),
        )
        assert len(filtered) == 1

    def test_list_filter_by_amount_range(self, db_session):
        """Test filtering invoices by amount range."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-amt-1",
            client_name="Client 1",
            client_email="client1@example.com",
            amount_total=Decimal("500.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-amt-2",
            client_name="Client 2",
            client_email="client2@example.com",
            amount_total=Decimal("2000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        # Filter by amount
        filtered = service.list(
            tenant_id,
            amount_min=Decimal("1000.00"),
            amount_max=Decimal("3000.00"),
        )
        assert len(filtered) == 1
        assert filtered[0].amount_total == Decimal("2000.00")

    def test_list_filter_is_overdue(self, db_session):
        """Test filtering overdue invoices."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        # Create overdue invoice
        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-overdue-1",
            client_name="Client 1",
            client_email="client1@example.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today() - timedelta(days=40),
            due_date=date.today() - timedelta(days=10),
            confidence=0.9,
            status="overdue",
        )

        # Create not overdue invoice
        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-overdue-2",
            client_name="Client 2",
            client_email="client2@example.com",
            amount_total=Decimal("2000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        overdue = service.list(tenant_id, is_overdue=True)
        assert len(overdue) == 1

        not_overdue = service.list(tenant_id, is_overdue=False)
        assert len(not_overdue) == 1

    def test_list_pagination(self, db_session):
        """Test pagination of invoice list."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        # Create 10 invoices
        for i in range(10):
            service.create(
                tenant_id=tenant_id,
                gmail_message_id=f"msg-page-{i}",
                client_name=f"Client {i}",
                client_email=f"client{i}@example.com",
                amount_total=Decimal("1000.00"),
                currency="USD",
                issue_date=date.today(),
                due_date=date.today() + timedelta(days=30),
                confidence=0.9,
            )

        # Get first page
        page1 = service.list(tenant_id, limit=5, offset=0)
        assert len(page1) == 5

        # Get second page
        page2 = service.list(tenant_id, limit=5, offset=5)
        assert len(page2) == 5

        # Ensure pages are different
        assert page1[0].id != page2[0].id


class TestInvoiceServiceUpdate:
    """Tests for InvoiceService.update()."""

    def test_update_invoice(self, db_session):
        """Test updating invoice fields."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        invoice = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-update",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        updated = service.update(
            invoice.id,
            tenant_id,
            client_name="Updated Client",
            notes="Updated notes",
        )

        assert updated.client_name == "Updated Client"
        assert updated.notes == "Updated notes"


class TestInvoiceServiceMarkAsPaid:
    """Tests for InvoiceService.mark_as_paid()."""

    def test_mark_as_fully_paid(self, db_session):
        """Test marking invoice as fully paid."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()
        user_id = uuid4()

        invoice = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-paid",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        paid_invoice = service.mark_as_paid(
            invoice.id,
            tenant_id,
            amount_paid=Decimal("1000.00"),
            paid_by=str(user_id),
        )

        assert paid_invoice.amount_paid == Decimal("1000.00")
        assert paid_invoice.status == "paid"

    def test_mark_as_partially_paid(self, db_session):
        """Test marking invoice as partially paid."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()
        user_id = uuid4()

        invoice = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-partial",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        partial_invoice = service.mark_as_paid(
            invoice.id,
            tenant_id,
            amount_paid=Decimal("500.00"),
            paid_by=str(user_id),
        )

        assert partial_invoice.amount_paid == Decimal("500.00")
        assert partial_invoice.status == "partial"


class TestInvoiceServiceConfirmReject:
    """Tests for InvoiceService.confirm_invoice() and reject_invoice()."""

    def test_confirm_invoice(self, db_session):
        """Test confirming a detected invoice."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()
        user_id = uuid4()

        invoice = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-confirm",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.75,  # Low confidence
            status="detected",
        )

        confirmed = service.confirm_invoice(invoice.id, tenant_id, str(user_id))
        assert confirmed.status == "pending"

    def test_reject_invoice(self, db_session):
        """Test rejecting a detected invoice."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()
        user_id = uuid4()

        invoice = service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-reject",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.75,
            status="detected",
        )

        rejected = service.reject_invoice(
            invoice.id,
            tenant_id,
            str(user_id),
            reason="Not a valid invoice",
        )
        assert rejected.status == "rejected"


class TestInvoiceServiceUtilityMethods:
    """Tests for utility methods."""

    def test_get_overdue_invoices(self, db_session):
        """Test getting overdue invoices."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        # Create overdue invoice
        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-util-overdue",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today() - timedelta(days=40),
            due_date=date.today() - timedelta(days=10),
            confidence=0.9,
            status="overdue",
        )

        # Create not overdue invoice
        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-util-notdue",
            client_name="Test Client 2",
            client_email="test2@client.com",
            amount_total=Decimal("2000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        overdue = service.get_overdue_invoices(tenant_id)
        assert len(overdue) == 1

    def test_get_invoices_by_client(self, db_session):
        """Test getting invoices for a specific client."""
        service = InvoiceService(db_session)
        tenant_id = uuid4()

        # Create multiple invoices for same client
        for i in range(3):
            service.create(
                tenant_id=tenant_id,
                gmail_message_id=f"msg-client-{i}",
                client_name="Same Client",
                client_email="same@client.com",
                amount_total=Decimal("1000.00"),
                currency="USD",
                issue_date=date.today(),
                due_date=date.today() + timedelta(days=30),
                confidence=0.9,
            )

        # Create invoice for different client
        service.create(
            tenant_id=tenant_id,
            gmail_message_id="msg-diff-client",
            client_name="Different Client",
            client_email="different@client.com",
            amount_total=Decimal("2000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        invoices = service.get_invoices_by_client(tenant_id, "same@client.com")
        assert len(invoices) == 3
