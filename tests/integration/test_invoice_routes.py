"""Integration tests for the InvoicePilot HTTP API.

Authentication and the database session are swapped out with
`app.dependency_overrides`, which is the only mechanism FastAPI honours: the
routes captured their dependency callables at import time, so patching the
module attribute has no effect on an already-built route.
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.api.dependencies import get_current_user
from src.api.main import app
from src.core.database import get_sync_db
from src.services.invoice_pilot.invoice_service import InvoiceService
from src.services.invoice_pilot.reminder_service import ReminderService


@pytest.fixture
def current_user(make_user):
    """The authenticated user (and therefore the tenant) for these tests."""
    return make_user(email="invoice-routes@example.com")


# One TestClient for the whole module: each instance spins up its own anyio
# portal, and churning through one per test leaves closed event loops behind.
_client = TestClient(app)


@pytest.fixture
def client(db_session, current_user):
    """TestClient wired to the test session and an authenticated user."""
    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: current_user
    try:
        yield _client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def anon_client(db_session):
    """TestClient whose auth dependency rejects the request."""

    def _unauthenticated():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    app.dependency_overrides[get_sync_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = _unauthenticated
    try:
        yield _client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def invoice_service(db_session):
    return InvoiceService(db_session)


@pytest.fixture
def reminder_service(db_session):
    return ReminderService(db_session)


def make_invoice(service, tenant_id, gmail_message_id, **overrides):
    """Create an invoice with sensible defaults."""
    params = dict(
        tenant_id=tenant_id,
        gmail_message_id=gmail_message_id,
        client_name="Test Client",
        client_email="test@client.com",
        amount_total=Decimal("1000.00"),
        currency="USD",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        confidence=0.9,
    )
    params.update(overrides)
    return service.create(**params)


class TestInvoiceListEndpoint:
    """GET /api/v1/invoices"""

    def test_list_invoices_requires_auth(self, anon_client):
        assert anon_client.get("/api/v1/invoices").status_code == 401

    def test_list_invoices_success(self, client, invoice_service, current_user):
        for i in range(3):
            make_invoice(
                invoice_service,
                current_user.id,
                f"msg-{i}",
                client_name=f"Client {i}",
                client_email=f"client{i}@example.com",
            )

        response = client.get("/api/v1/invoices")
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
        assert "total" in data
        assert len(data["invoices"]) == 3
        assert data["total"] == 3

    def test_list_invoices_filter_by_status(
        self, client, invoice_service, current_user
    ):
        make_invoice(
            invoice_service,
            current_user.id,
            "msg-detected",
            client_name="Client A",
            status="detected",
        )
        paid = make_invoice(
            invoice_service,
            current_user.id,
            "msg-paid",
            client_name="Client B",
            amount_total=Decimal("2000.00"),
        )
        invoice_service.update(paid.id, current_user.id, status="paid")

        response = client.get("/api/v1/invoices?status=detected")
        assert response.status_code == 200
        data = response.json()
        assert len(data["invoices"]) == 1
        assert data["invoices"][0]["status"] == "detected"

    def test_list_invoices_pagination(self, client, invoice_service, current_user):
        for i in range(10):
            make_invoice(
                invoice_service,
                current_user.id,
                f"msg-page-{i}",
                client_email=f"client{i}@example.com",
            )

        first = client.get("/api/v1/invoices?limit=5&offset=0")
        assert first.status_code == 200
        assert len(first.json()["invoices"]) == 5
        assert first.json()["total"] == 10

        second = client.get("/api/v1/invoices?limit=5&offset=5")
        assert second.status_code == 200
        assert len(second.json()["invoices"]) == 5

        first_ids = {i["id"] for i in first.json()["invoices"]}
        second_ids = {i["id"] for i in second.json()["invoices"]}
        assert not first_ids & second_ids

    def test_list_invoices_rejects_inverted_amount_range(self, client):
        response = client.get("/api/v1/invoices?amount_min=500&amount_max=100")
        assert response.status_code == 422


class TestInvoiceGetEndpoint:
    """GET /api/v1/invoices/{invoice_id}"""

    def test_get_invoice_requires_auth(self, anon_client):
        assert anon_client.get(f"/api/v1/invoices/{uuid4()}").status_code == 401

    def test_get_invoice_success(self, client, invoice_service, current_user):
        invoice = make_invoice(invoice_service, current_user.id, "msg-get")

        response = client.get(f"/api/v1/invoices/{invoice.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(invoice.id)
        assert data["client_name"] == "Test Client"
        assert "reminders" in data

    def test_get_invoice_not_found(self, client):
        assert client.get(f"/api/v1/invoices/{uuid4()}").status_code == 404

    def test_get_invoice_wrong_tenant_returns_404(
        self, client, invoice_service, make_user
    ):
        other_tenant = make_user(email="other-tenant@example.com")
        invoice = make_invoice(invoice_service, other_tenant.id, "msg-tenant-test")

        # `client` is authenticated as a different user.
        assert client.get(f"/api/v1/invoices/{invoice.id}").status_code == 404


class TestInvoiceConfirmEndpoint:
    """POST /api/v1/invoices/{invoice_id}/confirm"""

    def test_confirm_invoice_success(self, client, invoice_service, current_user):
        invoice = make_invoice(
            invoice_service,
            current_user.id,
            "msg-confirm",
            confidence=0.75,
            status="detected",
        )

        response = client.post(f"/api/v1/invoices/{invoice.id}/confirm")
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    def test_confirm_invoice_with_updates(self, client, invoice_service, current_user):
        invoice = make_invoice(
            invoice_service,
            current_user.id,
            "msg-confirm-update",
            confidence=0.75,
            status="detected",
        )

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/confirm",
            json={
                "invoice_number": "INV-UPDATED-001",
                "notes": "Confirmed with updates",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["invoice_number"] == "INV-UPDATED-001"
        assert data["notes"] == "Confirmed with updates"
        assert data["status"] == "pending"

    def test_confirm_invoice_not_found(self, client):
        response = client.post(f"/api/v1/invoices/{uuid4()}/confirm")
        assert response.status_code == 404


class TestInvoiceRejectEndpoint:
    """POST /api/v1/invoices/{invoice_id}/reject"""

    def test_reject_invoice_success(self, client, invoice_service, current_user):
        invoice = make_invoice(
            invoice_service,
            current_user.id,
            "msg-reject",
            confidence=0.75,
            status="detected",
        )

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/reject",
            json={"reason": "Not a valid invoice"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Invoice rejected successfully"

        refreshed = invoice_service.get(invoice.id, current_user.id)
        assert refreshed.status == "rejected"


class TestInvoiceMarkPaidEndpoint:
    """POST /api/v1/invoices/{invoice_id}/mark-paid"""

    def test_mark_invoice_fully_paid(self, client, invoice_service, current_user):
        invoice = make_invoice(invoice_service, current_user.id, "msg-paid")

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/mark-paid",
            json={"amount_paid": "1000.00", "payment_date": str(date.today())},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paid"
        assert float(data["amount_paid"]) == 1000.00

    def test_mark_invoice_partially_paid(self, client, invoice_service, current_user):
        invoice = make_invoice(invoice_service, current_user.id, "msg-partial")

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/mark-paid",
            json={"amount_paid": "500.00", "payment_date": str(date.today())},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "partial"
        assert float(data["amount_paid"]) == 500.00


class TestReminderEndpoints:
    """Reminder sub-resources of an invoice."""

    def test_list_reminders_for_invoice(
        self, client, invoice_service, reminder_service, current_user
    ):
        invoice = make_invoice(invoice_service, current_user.id, "msg-reminders")
        reminder_service.schedule_reminders(invoice)

        response = client.get(f"/api/v1/invoices/{invoice.id}/reminders")
        assert response.status_code == 200
        assert len(response.json()) == 4  # default schedule: -3, 3, 7, 14

    def test_approve_reminder(
        self, client, invoice_service, reminder_service, current_user
    ):
        invoice = make_invoice(invoice_service, current_user.id, "msg-approve-reminder")
        reminder = reminder_service.schedule_reminders(invoice)[0]
        reminder_service.set_draft_message(reminder.id, "Draft message")

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/reminders/{reminder.id}/approve",
            json={"final_message": "Approved message"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["final_message"] == "Approved message"

    def test_edit_reminder(
        self, client, invoice_service, reminder_service, current_user
    ):
        invoice = make_invoice(invoice_service, current_user.id, "msg-edit-reminder")
        reminder = reminder_service.schedule_reminders(invoice)[0]
        reminder_service.set_draft_message(reminder.id, "Original message")

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/reminders/{reminder.id}/edit",
            json={"new_message": "Edited message"},
        )
        assert response.status_code == 200
        assert response.json()["final_message"] == "Edited message"

    def test_skip_reminder(
        self, client, invoice_service, reminder_service, current_user
    ):
        invoice = make_invoice(invoice_service, current_user.id, "msg-skip-reminder")
        reminder = reminder_service.schedule_reminders(invoice)[0]

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/reminders/{reminder.id}/skip",
            json={"reason": "Not needed"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Reminder skipped successfully"

        assert reminder_service.get_reminder(reminder.id).status == "skipped"


class TestInvoiceValidation:
    """Request validation and error handling."""

    def test_mark_paid_invalid_amount(self, client, invoice_service, current_user):
        invoice = make_invoice(invoice_service, current_user.id, "msg-invalid-amt")

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/mark-paid",
            json={"amount_paid": "-100.00", "payment_date": str(date.today())},
        )
        assert response.status_code == 422

    def test_mark_paid_exceeds_total(self, client, invoice_service, current_user):
        invoice = make_invoice(invoice_service, current_user.id, "msg-exceed-amt")

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/mark-paid",
            json={"amount_paid": "1500.00", "payment_date": str(date.today())},
        )
        assert response.status_code == 422
