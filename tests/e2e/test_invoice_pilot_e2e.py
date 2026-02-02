"""
End-to-end tests for InvoicePilot feature.

Tests the complete flow from invoice email detection to payment.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from src.main import app
from src.models.invoice import Invoice, InvoiceReminder, InvoiceAction
from src.agents.invoice_pilot import InvoicePilotAgent
from src.services.invoice_service import InvoiceService
from src.services.reminder_service import ReminderService
from src.tasks.invoice_tasks import scan_invoices_for_tenant, check_invoice_reminders_for_tenant


@pytest.fixture
def client():
    """Test client for API requests."""
    return TestClient(app)


@pytest.fixture
def tenant_id():
    """Test tenant ID."""
    return str(uuid4())


@pytest.fixture
def auth_headers(tenant_id):
    """Mock authentication headers."""
    return {
        "Authorization": "Bearer test_token",
        "X-Tenant-ID": tenant_id
    }


@pytest.fixture
def mock_gmail_invoice_email():
    """Mock Gmail email with invoice attachment."""
    return {
        "id": "test_msg_001",
        "threadId": "test_thread_001",
        "labelIds": ["SENT"],
        "snippet": "Invoice INV-E2E-001 for January services",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Invoice INV-E2E-001 - January 2026"},
                {"name": "To", "value": "e2e-client@example.com"},
                {"name": "From", "value": "test@peopletop.com"},
                {"name": "Date", "value": "Mon, 20 Jan 2026 10:00:00 +0000"}
            ],
            "parts": [
                {
                    "mimeType": "application/pdf",
                    "filename": "invoice_INV-E2E-001.pdf",
                    "body": {
                        "attachmentId": "test_attach_001"
                    }
                }
            ]
        }
    }


@pytest.fixture
def mock_pdf_content():
    """Mock PDF content for invoice."""
    return b"""Mock PDF Content
    INVOICE
    Invoice Number: INV-E2E-001
    Date: January 20, 2026
    Due Date: February 20, 2026

    Bill To:
    E2E Test Client Corp
    e2e-client@example.com

    Description                 Amount
    Consulting Services         €2,500.00

    TOTAL: €2,500.00
    """


@pytest.mark.e2e
@pytest.mark.asyncio
class TestInvoicePilotE2E:
    """End-to-end tests for the complete InvoicePilot workflow."""

    async def test_complete_invoice_lifecycle_high_confidence(
        self,
        db_session,
        client,
        tenant_id,
        auth_headers,
        mock_gmail_invoice_email,
        mock_pdf_content
    ):
        """
        Test complete flow: Email → Detect → Extract → Auto-confirm → Schedule → Send Reminder → Mark Paid.

        This is the happy path with high confidence (>80%).
        """
        # ===== STEP 1: Mock external services =====
        with patch('src.integrations.gmail.GmailService.list_sent_emails') as mock_list_emails, \
             patch('src.integrations.gmail.GmailService.get_message') as mock_get_message, \
             patch('src.integrations.gmail.GmailService.get_attachment') as mock_get_attachment, \
             patch('src.integrations.gmail.GmailService.send_email') as mock_send_email, \
             patch('src.integrations.slack.SlackNotifier.send_escalation_alert') as mock_slack_escalate, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService._extract_with_llm') as mock_llm_extract, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService._detect_with_llm') as mock_llm_detect, \
             patch('src.agents.invoice_pilot.InvoicePilotAgent._draft_reminder_message') as mock_draft_reminder:

            # Configure mocks
            mock_list_emails.return_value = [mock_gmail_invoice_email["id"]]
            mock_get_message.return_value = mock_gmail_invoice_email
            mock_get_attachment.return_value = mock_pdf_content

            mock_llm_detect.return_value = {
                "is_invoice": True,
                "confidence": 0.95,
                "reasoning": "Clear invoice format with number, amount, and client details"
            }

            mock_llm_extract.return_value = {
                "invoice_number": "INV-E2E-001",
                "client_name": "E2E Test Client Corp",
                "client_email": "e2e-client@example.com",
                "amount_total": 2500.00,
                "currency": "EUR",
                "issue_date": "2026-01-20",
                "due_date": "2026-02-20",
                "confidence": 0.92,
                "items": [
                    {"description": "Consulting Services", "amount": 2500.00}
                ]
            }

            mock_draft_reminder.return_value = {
                "subject": "Friendly reminder: Invoice INV-E2E-001",
                "message": "Hello,\n\nThis is a friendly reminder that invoice INV-E2E-001 for €2,500.00 is due on February 20, 2026.\n\nBest regards",
                "tone": "friendly"
            }

            mock_send_email.return_value = {"id": "sent_reminder_001"}

            # ===== STEP 2: Run invoice detection (simulating Celery task) =====
            agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)
            detection_result = await agent.scan_and_detect_invoices()

            # Verify invoice was detected and saved
            assert len(detection_result["detected_invoices"]) == 1

            invoice = db_session.query(Invoice).filter_by(
                tenant_id=tenant_id,
                invoice_number="INV-E2E-001"
            ).first()

            assert invoice is not None
            assert invoice.client_name == "E2E Test Client Corp"
            assert invoice.amount_total == 2500.00
            assert invoice.currency == "EUR"
            assert invoice.status == "pending"  # Auto-confirmed due to high confidence
            assert invoice.confidence >= 0.8

            # Verify audit log for detection
            detection_action = db_session.query(InvoiceAction).filter_by(
                invoice_id=invoice.id,
                action_type="detected"
            ).first()
            assert detection_action is not None

            # ===== STEP 3: API - List invoices =====
            response = client.get(
                "/api/v1/invoices",
                headers=auth_headers,
                params={"status": "pending"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["invoice_number"] == "INV-E2E-001"
            assert data["items"][0]["amount_total"] == 2500.00

            # ===== STEP 4: API - Get invoice details =====
            response = client.get(
                f"/api/v1/invoices/{invoice.id}",
                headers=auth_headers
            )

            assert response.status_code == 200
            invoice_data = response.json()
            assert invoice_data["id"] == str(invoice.id)
            assert invoice_data["client_email"] == "e2e-client@example.com"

            # ===== STEP 5: System schedules reminders =====
            reminder_service = ReminderService(db=db_session)
            reminder_service.schedule_reminders_for_invoice(
                invoice_id=invoice.id,
                schedule_days=[-3, 3, 7, 14]  # 3 days before, 3/7/14 days after due
            )

            reminders = db_session.query(InvoiceReminder).filter_by(
                invoice_id=invoice.id
            ).all()

            assert len(reminders) == 4
            assert reminders[0].type == "pre_due"  # -3 days
            assert reminders[1].type == "overdue_3"  # +3 days
            assert reminders[2].type == "overdue_7"  # +7 days
            assert reminders[3].type == "overdue_14"  # +14 days

            # ===== STEP 6: Time passes - reminder becomes due =====
            # Simulate due date passing - set first overdue reminder as due
            overdue_reminder = reminders[1]
            overdue_reminder.scheduled_at = datetime.now() - timedelta(hours=1)
            db_session.commit()

            # ===== STEP 7: Run reminder check (simulating Celery task) =====
            reminder_result = await agent.check_and_draft_reminders()

            # Verify reminder was drafted
            assert len(reminder_result["drafted_reminders"]) == 1

            db_session.refresh(overdue_reminder)
            assert overdue_reminder.draft_message is not None
            assert overdue_reminder.status == "awaiting_approval"

            # ===== STEP 8: API - Approve reminder =====
            response = client.post(
                f"/api/v1/invoices/{invoice.id}/reminders/{overdue_reminder.id}/approve",
                headers=auth_headers,
                json={"message": overdue_reminder.draft_message}  # Use draft as-is
            )

            assert response.status_code == 200

            db_session.refresh(overdue_reminder)
            assert overdue_reminder.status == "approved"
            assert overdue_reminder.approved_by == tenant_id

            # ===== STEP 9: Send approved reminder =====
            await agent.send_approved_reminders()

            db_session.refresh(overdue_reminder)
            assert overdue_reminder.status == "sent"
            assert overdue_reminder.sent_at is not None

            # Verify Gmail send was called
            mock_send_email.assert_called_once()
            send_call_args = mock_send_email.call_args
            assert "e2e-client@example.com" in str(send_call_args)

            # Verify audit log for reminder sent
            reminder_action = db_session.query(InvoiceAction).filter_by(
                invoice_id=invoice.id,
                action_type="reminder_sent"
            ).first()
            assert reminder_action is not None

            # ===== STEP 10: API - Mark invoice as paid =====
            response = client.post(
                f"/api/v1/invoices/{invoice.id}/mark-paid",
                headers=auth_headers,
                json={
                    "amount_paid": 2500.00,
                    "payment_date": datetime.now().isoformat(),
                    "notes": "Payment received via bank transfer"
                }
            )

            assert response.status_code == 200

            db_session.refresh(invoice)
            assert invoice.status == "paid"
            assert invoice.amount_paid == 2500.00

            # Verify audit log for payment
            payment_action = db_session.query(InvoiceAction).filter_by(
                invoice_id=invoice.id,
                action_type="marked_paid"
            ).first()
            assert payment_action is not None
            assert payment_action.actor == tenant_id

            # ===== STEP 11: Verify complete audit trail =====
            all_actions = db_session.query(InvoiceAction).filter_by(
                invoice_id=invoice.id
            ).order_by(InvoiceAction.timestamp).all()

            expected_actions = ["detected", "reminder_scheduled", "reminder_drafted",
                              "reminder_approved", "reminder_sent", "marked_paid"]
            actual_action_types = [action.action_type for action in all_actions]

            for expected_action in expected_actions:
                assert expected_action in actual_action_types, \
                    f"Missing action: {expected_action}. Got: {actual_action_types}"

    async def test_complete_invoice_lifecycle_low_confidence(
        self,
        db_session,
        client,
        tenant_id,
        auth_headers,
        mock_gmail_invoice_email,
        mock_pdf_content
    ):
        """
        Test complete flow with LOW confidence requiring manual confirmation.

        Flow: Email → Detect → Extract (low conf) → Slack notification → Manual confirm → Rest of flow
        """
        with patch('src.integrations.gmail.GmailService.list_sent_emails') as mock_list_emails, \
             patch('src.integrations.gmail.GmailService.get_message') as mock_get_message, \
             patch('src.integrations.gmail.GmailService.get_attachment') as mock_get_attachment, \
             patch('src.integrations.slack.SlackNotifier.send_invoice_confirmation') as mock_slack_confirm, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService._extract_with_llm') as mock_llm_extract, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService._detect_with_llm') as mock_llm_detect:

            # Configure mocks
            mock_list_emails.return_value = [mock_gmail_invoice_email["id"]]
            mock_get_message.return_value = mock_gmail_invoice_email
            mock_get_attachment.return_value = mock_pdf_content

            mock_llm_detect.return_value = {
                "is_invoice": True,
                "confidence": 0.70,
                "reasoning": "Possible invoice but unclear formatting"
            }

            # LOW confidence extraction
            mock_llm_extract.return_value = {
                "invoice_number": "INV-E2E-002",
                "client_name": "Uncertain Client",
                "client_email": "uncertain@example.com",
                "amount_total": 1000.00,
                "currency": "EUR",
                "issue_date": "2026-01-20",
                "due_date": "2026-02-20",
                "confidence": 0.68,  # Below 0.8 threshold
                "items": [
                    {"description": "Services", "amount": 1000.00}
                ]
            }

            mock_slack_confirm.return_value = {"ts": "test_slack_ts_001"}

            # ===== STEP 1: Run detection =====
            agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)
            detection_result = await agent.scan_and_detect_invoices()

            # Verify invoice requires confirmation
            assert len(detection_result["pending_confirmation"]) == 1

            invoice = db_session.query(Invoice).filter_by(
                tenant_id=tenant_id,
                invoice_number="INV-E2E-002"
            ).first()

            assert invoice is not None
            assert invoice.status == "draft"  # Not confirmed yet
            assert invoice.confidence < 0.8

            # Verify Slack notification was sent
            mock_slack_confirm.assert_called_once()

            # ===== STEP 2: API - List pending confirmations =====
            response = client.get(
                "/api/v1/invoices",
                headers=auth_headers,
                params={"status": "draft"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) == 1
            assert data["items"][0]["status"] == "draft"

            # ===== STEP 3: API - Manual confirmation =====
            response = client.post(
                f"/api/v1/invoices/{invoice.id}/confirm",
                headers=auth_headers,
                json={
                    "confirmed_data": {
                        "invoice_number": "INV-E2E-002",
                        "client_name": "Uncertain Client (Confirmed)",
                        "amount_total": 1000.00,
                        "due_date": "2026-02-20"
                    }
                }
            )

            assert response.status_code == 200

            db_session.refresh(invoice)
            assert invoice.status == "pending"
            assert invoice.client_name == "Uncertain Client (Confirmed)"

            # Verify confirmation action in audit log
            confirm_action = db_session.query(InvoiceAction).filter_by(
                invoice_id=invoice.id,
                action_type="confirmed"
            ).first()
            assert confirm_action is not None
            assert confirm_action.actor == tenant_id

            # ===== STEP 4: Now invoice follows normal flow =====
            # (Scheduling reminders, etc. - same as high confidence flow)

    async def test_escalation_flow_e2e(
        self,
        db_session,
        client,
        tenant_id,
        auth_headers
    ):
        """
        Test escalation flow: Multiple reminders → No payment → Escalation.
        """
        # ===== STEP 1: Create overdue invoice with multiple reminders =====
        invoice = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg_escalation_001",
            invoice_number="INV-E2E-OVERDUE",
            client_name="Problem Client Corp",
            client_email="problem@example.com",
            amount_total=5000.00,
            currency="EUR",
            issue_date=datetime.now().date() - timedelta(days=60),
            due_date=datetime.now().date() - timedelta(days=30),  # 30 days overdue
            status="overdue",
            confidence=0.95
        )
        db_session.add(invoice)
        db_session.commit()

        # Create 3 sent reminders
        for i in range(3):
            reminder = InvoiceReminder(
                invoice_id=invoice.id,
                scheduled_at=datetime.now() - timedelta(days=25 - i*7),
                sent_at=datetime.now() - timedelta(days=25 - i*7),
                type=f"overdue_{i+1}",
                status="sent",
                draft_message=f"Reminder {i+1}",
                final_message=f"Reminder {i+1}"
            )
            db_session.add(reminder)
        db_session.commit()

        # ===== STEP 2: Run escalation check =====
        with patch('src.integrations.slack.SlackNotifier.send_escalation_alert') as mock_slack_escalate:
            mock_slack_escalate.return_value = {"ts": "escalation_ts_001"}

            agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)
            escalation_result = await agent.detect_problem_patterns()

            # Verify escalation occurred
            assert len(escalation_result["escalated_invoices"]) == 1
            assert escalation_result["escalated_invoices"][0]["invoice_id"] == invoice.id

            # Verify Slack alert was sent
            mock_slack_escalate.assert_called_once()
            call_kwargs = mock_slack_escalate.call_args[1]
            assert "Problem Client Corp" in str(call_kwargs)
            assert "5000" in str(call_kwargs)

        # ===== STEP 3: Verify escalation in audit log =====
        escalation_action = db_session.query(InvoiceAction).filter_by(
            invoice_id=invoice.id,
            action_type="escalated"
        ).first()

        assert escalation_action is not None
        assert "3 reminders" in escalation_action.details or "30 days" in escalation_action.details

        # ===== STEP 4: API - Get invoice with escalation status =====
        response = client.get(
            f"/api/v1/invoices/{invoice.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        invoice_data = response.json()
        assert invoice_data["status"] == "overdue"

        # Check reminders
        response = client.get(
            f"/api/v1/invoices/{invoice.id}/reminders",
            headers=auth_headers
        )

        assert response.status_code == 200
        reminders_data = response.json()
        assert len(reminders_data) >= 3

    async def test_partial_payment_flow(
        self,
        db_session,
        client,
        tenant_id,
        auth_headers
    ):
        """
        Test partial payment flow: Invoice with partial payments → Full payment.
        """
        # ===== STEP 1: Create invoice =====
        invoice = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg_partial_001",
            invoice_number="INV-E2E-PARTIAL",
            client_name="Installment Client",
            client_email="installment@example.com",
            amount_total=3000.00,
            amount_paid=0.00,
            currency="EUR",
            issue_date=datetime.now().date() - timedelta(days=10),
            due_date=datetime.now().date() + timedelta(days=20),
            status="pending",
            confidence=0.95
        )
        db_session.add(invoice)
        db_session.commit()

        # ===== STEP 2: First partial payment (1000) =====
        response = client.post(
            f"/api/v1/invoices/{invoice.id}/mark-paid",
            headers=auth_headers,
            json={
                "amount_paid": 1000.00,
                "payment_date": datetime.now().isoformat(),
                "notes": "First installment"
            }
        )

        assert response.status_code == 200

        db_session.refresh(invoice)
        assert invoice.amount_paid == 1000.00
        assert invoice.status == "partially_paid"

        # ===== STEP 3: Second partial payment (1000) =====
        response = client.post(
            f"/api/v1/invoices/{invoice.id}/mark-paid",
            headers=auth_headers,
            json={
                "amount_paid": 2000.00,  # Cumulative
                "payment_date": datetime.now().isoformat(),
                "notes": "Second installment"
            }
        )

        assert response.status_code == 200

        db_session.refresh(invoice)
        assert invoice.amount_paid == 2000.00
        assert invoice.status == "partially_paid"

        # ===== STEP 4: Final payment (remaining 1000) =====
        response = client.post(
            f"/api/v1/invoices/{invoice.id}/mark-paid",
            headers=auth_headers,
            json={
                "amount_paid": 3000.00,  # Full amount
                "payment_date": datetime.now().isoformat(),
                "notes": "Final payment"
            }
        )

        assert response.status_code == 200

        db_session.refresh(invoice)
        assert invoice.amount_paid == 3000.00
        assert invoice.status == "paid"

        # ===== STEP 5: Verify all payment actions =====
        payment_actions = db_session.query(InvoiceAction).filter_by(
            invoice_id=invoice.id,
            action_type="marked_paid"
        ).all()

        assert len(payment_actions) == 3

    async def test_invoice_rejection_flow(
        self,
        db_session,
        client,
        tenant_id,
        auth_headers
    ):
        """
        Test invoice rejection flow: Low confidence → Manual review → Reject.
        """
        # ===== STEP 1: Create draft invoice =====
        invoice = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg_reject_001",
            invoice_number="INV-E2E-REJECT",
            client_name="False Positive",
            client_email="notinvoice@example.com",
            amount_total=500.00,
            currency="EUR",
            issue_date=datetime.now().date(),
            due_date=datetime.now().date() + timedelta(days=30),
            status="draft",
            confidence=0.60
        )
        db_session.add(invoice)
        db_session.commit()

        # ===== STEP 2: API - Reject invoice =====
        response = client.post(
            f"/api/v1/invoices/{invoice.id}/reject",
            headers=auth_headers,
            json={
                "reason": "Not actually an invoice - just a quote"
            }
        )

        assert response.status_code == 200

        db_session.refresh(invoice)
        assert invoice.status == "rejected"

        # ===== STEP 3: Verify rejection action =====
        reject_action = db_session.query(InvoiceAction).filter_by(
            invoice_id=invoice.id,
            action_type="rejected"
        ).first()

        assert reject_action is not None
        assert "Not actually an invoice" in reject_action.details

        # ===== STEP 4: Verify rejected invoice doesn't appear in pending =====
        response = client.get(
            "/api/v1/invoices",
            headers=auth_headers,
            params={"status": "pending"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should not include rejected invoice
        invoice_numbers = [item["invoice_number"] for item in data["items"]]
        assert "INV-E2E-REJECT" not in invoice_numbers


@pytest.mark.e2e
@pytest.mark.asyncio
class TestInvoicePilotPerformance:
    """Performance and load tests for InvoicePilot."""

    async def test_batch_detection_performance(
        self,
        db_session,
        tenant_id
    ):
        """
        Test that agent can handle batch processing of multiple invoices.
        """
        # Create 10 mock emails
        mock_emails = []
        for i in range(10):
            mock_emails.append({
                "id": f"msg_{i:03d}",
                "threadId": f"thread_{i:03d}",
                "snippet": f"Invoice INV-BATCH-{i:03d}",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": f"Invoice INV-BATCH-{i:03d}"},
                        {"name": "To", "value": f"client{i}@example.com"}
                    ],
                    "parts": [
                        {
                            "mimeType": "application/pdf",
                            "filename": f"invoice_{i}.pdf",
                            "body": {"attachmentId": f"attach_{i}"}
                        }
                    ]
                }
            })

        with patch('src.integrations.gmail.GmailService.list_sent_emails') as mock_list, \
             patch('src.integrations.gmail.GmailService.get_message') as mock_get, \
             patch('src.integrations.gmail.GmailService.get_attachment') as mock_attach, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService._detect_with_llm') as mock_detect, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService._extract_with_llm') as mock_extract:

            mock_list.return_value = [email["id"] for email in mock_emails]
            mock_get.side_effect = lambda email_id: next(e for e in mock_emails if e["id"] == email_id)
            mock_attach.return_value = b"Mock PDF"

            mock_detect.return_value = {"is_invoice": True, "confidence": 0.95, "reasoning": "Clear invoice"}

            def mock_extract_fn(email_id, *args, **kwargs):
                idx = int(email_id.split("_")[1])
                return {
                    "invoice_number": f"INV-BATCH-{idx:03d}",
                    "client_name": f"Client {idx}",
                    "client_email": f"client{idx}@example.com",
                    "amount_total": 1000.00 + idx * 100,
                    "currency": "EUR",
                    "issue_date": datetime.now().date().isoformat(),
                    "due_date": (datetime.now().date() + timedelta(days=30)).isoformat(),
                    "confidence": 0.92,
                    "items": [{"description": "Services", "amount": 1000.00 + idx * 100}]
                }

            mock_extract.side_effect = mock_extract_fn

            # Measure performance
            import time
            start_time = time.time()

            agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)
            result = await agent.scan_and_detect_invoices()

            end_time = time.time()
            processing_time = end_time - start_time

            # Verify all invoices were processed
            assert len(result["detected_invoices"]) == 10

            # Performance assertion: should process 10 invoices in < 30 seconds
            # (This is a generous limit; actual performance should be much better with parallel processing)
            assert processing_time < 30, f"Batch processing took {processing_time:.2f}s - too slow"

            # Verify all invoices in DB
            invoices = db_session.query(Invoice).filter_by(tenant_id=tenant_id).all()
            assert len(invoices) == 10
