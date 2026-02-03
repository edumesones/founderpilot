"""
Integration tests for invoice API routes.

Tests the full request/response cycle for InvoicePilot endpoints including:
- Authentication and authorization
- CRUD operations
- Invoice confirmation and rejection
- Payment tracking
- Reminder management
- Settings management
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.models.invoice_pilot.invoice import Invoice, InvoiceReminder
from src.services.invoice_pilot.invoice_service import InvoiceService
from src.services.invoice_pilot.reminder_service import ReminderService


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_current_user():
    """Mock current user for authentication."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    return user


@pytest.fixture
def auth_headers(mock_current_user):
    """Create authentication headers."""
    # In a real test, you'd generate a valid JWT token
    # For now, we'll mock the get_current_user dependency
    return {"Authorization": "Bearer mock_token"}


@pytest.fixture
def sample_invoice_data(mock_current_user):
    """Sample invoice data for creating invoices."""
    return {
        "tenant_id": str(mock_current_user.id),
        "gmail_message_id": f"msg-{uuid4()}",
        "invoice_number": "INV-2024-001",
        "client_name": "Acme Corp",
        "client_email": "billing@acme.com",
        "amount_total": "1000.00",
        "currency": "USD",
        "issue_date": str(date.today()),
        "due_date": str(date.today() + timedelta(days=30)),
        "confidence": 0.95,
    }


class TestInvoiceListEndpoint:
    """Tests for GET /api/v1/invoices"""

    @patch("src.api.dependencies.get_current_user")
    def test_list_invoices_requires_auth(self, mock_auth, client):
        """Test that listing invoices requires authentication."""
        mock_auth.return_value = None
        response = client.get("/api/v1/invoices")
        assert response.status_code == 401

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_list_invoices_success(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test listing invoices successfully."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Create some invoices
        service = InvoiceService(db_session)
        for i in range(3):
            service.create(
                tenant_id=mock_current_user.id,
                gmail_message_id=f"msg-{i}",
                client_name=f"Client {i}",
                client_email=f"client{i}@example.com",
                amount_total=Decimal("1000.00"),
                currency="USD",
                issue_date=date.today(),
                due_date=date.today() + timedelta(days=30),
                confidence=0.9,
            )

        response = client.get("/api/v1/invoices")
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
        assert "total" in data
        assert len(data["invoices"]) == 3

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_list_invoices_filter_by_status(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test filtering invoices by status."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        service = InvoiceService(db_session)
        # Create detected invoice
        service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-detected",
            client_name="Client A",
            client_email="clienta@example.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
            status="detected",
        )

        # Create paid invoice
        inv = service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-paid",
            client_name="Client B",
            client_email="clientb@example.com",
            amount_total=Decimal("2000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )
        service.update(inv.id, mock_current_user.id, status="paid")

        # Filter by detected
        response = client.get("/api/v1/invoices?status=detected")
        assert response.status_code == 200
        data = response.json()
        assert len(data["invoices"]) == 1
        assert data["invoices"][0]["status"] == "detected"

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_list_invoices_pagination(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test pagination of invoice list."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        service = InvoiceService(db_session)
        # Create 10 invoices
        for i in range(10):
            service.create(
                tenant_id=mock_current_user.id,
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
        response = client.get("/api/v1/invoices?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["invoices"]) == 5

        # Get second page
        response = client.get("/api/v1/invoices?limit=5&offset=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["invoices"]) == 5


class TestInvoiceGetEndpoint:
    """Tests for GET /api/v1/invoices/{invoice_id}"""

    @patch("src.api.dependencies.get_current_user")
    def test_get_invoice_requires_auth(self, mock_auth, client):
        """Test that getting invoice requires authentication."""
        mock_auth.return_value = None
        response = client.get(f"/api/v1/invoices/{uuid4()}")
        assert response.status_code == 401

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_get_invoice_success(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test getting invoice details successfully."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        service = InvoiceService(db_session)
        invoice = service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-get",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        response = client.get(f"/api/v1/invoices/{invoice.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(invoice.id)
        assert data["client_name"] == "Test Client"
        assert "reminders" in data

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_get_invoice_not_found(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test getting nonexistent invoice returns 404."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        fake_id = uuid4()
        response = client.get(f"/api/v1/invoices/{fake_id}")
        assert response.status_code == 404

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_get_invoice_wrong_tenant_returns_404(
        self, mock_db, mock_auth, client, db_session
    ):
        """Test that accessing another tenant's invoice returns 404."""
        # Create invoice as one user
        user1 = MagicMock()
        user1.id = uuid4()
        service = InvoiceService(db_session)
        invoice = service.create(
            tenant_id=user1.id,
            gmail_message_id="msg-tenant-test",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        # Try to access as different user
        user2 = MagicMock()
        user2.id = uuid4()
        mock_auth.return_value = user2
        mock_db.return_value = db_session

        response = client.get(f"/api/v1/invoices/{invoice.id}")
        assert response.status_code == 404


class TestInvoiceConfirmEndpoint:
    """Tests for POST /api/v1/invoices/{invoice_id}/confirm"""

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_confirm_invoice_success(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test confirming an invoice successfully."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        service = InvoiceService(db_session)
        invoice = service.create(
            tenant_id=mock_current_user.id,
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

        response = client.post(f"/api/v1/invoices/{invoice.id}/confirm")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_confirm_invoice_with_updates(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test confirming invoice with field updates."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        service = InvoiceService(db_session)
        invoice = service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-confirm-update",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.75,
            status="detected",
        )

        payload = {
            "invoice_number": "INV-UPDATED-001",
            "notes": "Confirmed with updates",
        }

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/confirm",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["invoice_number"] == "INV-UPDATED-001"
        assert data["notes"] == "Confirmed with updates"


class TestInvoiceRejectEndpoint:
    """Tests for POST /api/v1/invoices/{invoice_id}/reject"""

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_reject_invoice_success(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test rejecting an invoice successfully."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        service = InvoiceService(db_session)
        invoice = service.create(
            tenant_id=mock_current_user.id,
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

        payload = {"reason": "Not a valid invoice"}

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/reject",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Invoice rejected successfully"


class TestInvoiceMarkPaidEndpoint:
    """Tests for POST /api/v1/invoices/{invoice_id}/mark-paid"""

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_mark_invoice_fully_paid(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test marking invoice as fully paid."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        service = InvoiceService(db_session)
        invoice = service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-paid",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        payload = {
            "amount_paid": "1000.00",
            "payment_date": str(date.today()),
        }

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/mark-paid",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paid"
        assert float(data["amount_paid"]) == 1000.00

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_mark_invoice_partially_paid(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test marking invoice as partially paid."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        service = InvoiceService(db_session)
        invoice = service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-partial",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        payload = {
            "amount_paid": "500.00",
            "payment_date": str(date.today()),
        }

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/mark-paid",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "partial"
        assert float(data["amount_paid"]) == 500.00


class TestReminderEndpoints:
    """Tests for reminder-related endpoints"""

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_list_reminders_for_invoice(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test listing reminders for an invoice."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Create invoice
        invoice_service = InvoiceService(db_session)
        invoice = invoice_service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-reminders",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        # Schedule reminders
        reminder_service = ReminderService(db_session)
        reminder_service.schedule_reminders(invoice)

        response = client.get(f"/api/v1/invoices/{invoice.id}/reminders")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4  # Default schedule has 4 reminders

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_approve_reminder(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test approving a reminder."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Create invoice and reminders
        invoice_service = InvoiceService(db_session)
        invoice = invoice_service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-approve-reminder",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        reminder_service = ReminderService(db_session)
        reminders = reminder_service.schedule_reminders(invoice)
        reminder = reminders[0]

        # Set draft message
        reminder_service.set_draft_message(reminder.id, "Draft message")

        payload = {"final_message": "Approved message"}

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/reminders/{reminder.id}/approve",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["final_message"] == "Approved message"

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_edit_reminder(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test editing a reminder message."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Create invoice and reminders
        invoice_service = InvoiceService(db_session)
        invoice = invoice_service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-edit-reminder",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        reminder_service = ReminderService(db_session)
        reminders = reminder_service.schedule_reminders(invoice)
        reminder = reminders[0]

        # Set draft message
        reminder_service.set_draft_message(reminder.id, "Original message")

        payload = {"new_message": "Edited message"}

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/reminders/{reminder.id}/edit",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["final_message"] == "Edited message"

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_skip_reminder(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test skipping a reminder."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        # Create invoice and reminders
        invoice_service = InvoiceService(db_session)
        invoice = invoice_service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-skip-reminder",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        reminder_service = ReminderService(db_session)
        reminders = reminder_service.schedule_reminders(invoice)
        reminder = reminders[0]

        payload = {"reason": "Not needed"}

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/reminders/{reminder.id}/skip",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Reminder skipped successfully"


class TestInvoiceValidation:
    """Tests for request validation and error handling"""

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_mark_paid_invalid_amount(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test that invalid payment amount is rejected."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        service = InvoiceService(db_session)
        invoice = service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-invalid-amt",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        # Try to pay negative amount
        payload = {
            "amount_paid": "-100.00",
            "payment_date": str(date.today()),
        }

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/mark-paid",
            json=payload,
        )
        assert response.status_code == 422

    @patch("src.api.dependencies.get_current_user")
    @patch("src.api.dependencies.get_db")
    def test_mark_paid_exceeds_total(
        self, mock_db, mock_auth, client, mock_current_user, db_session
    ):
        """Test that payment exceeding total is rejected."""
        mock_auth.return_value = mock_current_user
        mock_db.return_value = db_session

        service = InvoiceService(db_session)
        invoice = service.create(
            tenant_id=mock_current_user.id,
            gmail_message_id="msg-exceed-amt",
            client_name="Test Client",
            client_email="test@client.com",
            amount_total=Decimal("1000.00"),
            currency="USD",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            confidence=0.9,
        )

        # Try to pay more than total
        payload = {
            "amount_paid": "1500.00",
            "payment_date": str(date.today()),
        }

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/mark-paid",
            json=payload,
        )
        assert response.status_code == 422
