"""
Integration tests for InvoicePilotAgent.

Tests the complete agent workflows with mocked external services.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from src.agents.invoice_pilot import InvoicePilotAgent, InvoiceState, DetectionState, ReminderState
from src.models.invoice import Invoice, InvoiceReminder, InvoiceAction
from src.services.invoice_service import InvoiceService
from src.services.reminder_service import ReminderService
from src.services.invoice_detection_service import InvoiceDetectionService


@pytest.fixture
def tenant_id():
    """Fixture for tenant ID."""
    return str(uuid4())


@pytest.fixture
def mock_gmail_response():
    """Mock Gmail API response with invoice email."""
    return {
        "messages": [
            {
                "id": "msg123",
                "threadId": "thread123",
                "labelIds": ["SENT"],
                "snippet": "Invoice INV-001 attached",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Invoice INV-001 - January 2026"},
                        {"name": "To", "value": "client@example.com"},
                        {"name": "Date", "value": "Mon, 20 Jan 2026 10:00:00 +0000"}
                    ],
                    "parts": [
                        {
                            "mimeType": "application/pdf",
                            "filename": "invoice_INV-001.pdf",
                            "body": {
                                "attachmentId": "attach123"
                            }
                        }
                    ]
                }
            }
        ]
    }


@pytest.fixture
def mock_llm_detection_response():
    """Mock LLM response for invoice detection."""
    return {
        "is_invoice": True,
        "confidence": 0.95,
        "reasoning": "Email contains PDF attachment with invoice number and amount"
    }


@pytest.fixture
def mock_llm_extraction_response():
    """Mock LLM response for data extraction."""
    return {
        "invoice_number": "INV-001",
        "client_name": "Acme Corp",
        "client_email": "client@example.com",
        "amount_total": 1500.00,
        "currency": "EUR",
        "issue_date": "2026-01-20",
        "due_date": "2026-02-20",
        "confidence": 0.92,
        "items": [
            {"description": "Consulting services", "amount": 1500.00}
        ]
    }


@pytest.fixture
def mock_llm_reminder_draft():
    """Mock LLM response for reminder draft."""
    return {
        "subject": "Friendly reminder: Invoice INV-001 due soon",
        "message": """Hello,

I hope this message finds you well. I wanted to send a friendly reminder that invoice INV-001 for €1,500.00 is due on February 20, 2026.

If you've already processed the payment, please disregard this message.

Best regards,
Test User""",
        "tone": "friendly"
    }


@pytest.mark.asyncio
class TestInvoiceDetectionFlow:
    """Test the invoice detection workflow."""

    async def test_successful_detection_high_confidence(
        self,
        db_session,
        tenant_id,
        mock_gmail_response,
        mock_llm_detection_response,
        mock_llm_extraction_response
    ):
        """Test successful invoice detection with high confidence."""
        agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)

        with patch('src.services.invoice_detection_service.InvoiceDetectionService.scan_gmail') as mock_scan, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService.detect_invoice') as mock_detect, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService.extract_data') as mock_extract:

            # Mock external calls
            mock_scan.return_value = [mock_gmail_response["messages"][0]]
            mock_detect.return_value = mock_llm_detection_response
            mock_extract.return_value = mock_llm_extraction_response

            # Run detection flow
            state = DetectionState(
                tenant_id=tenant_id,
                emails_to_scan=[],
                detected_invoices=[],
                pending_confirmation=[]
            )

            result = await agent.run_detection_flow(state)

            # Verify results
            assert len(result["detected_invoices"]) == 1
            assert len(result["pending_confirmation"]) == 0  # High confidence, no confirmation needed

            # Verify invoice was saved to DB
            invoice = db_session.query(Invoice).filter_by(
                tenant_id=tenant_id,
                invoice_number="INV-001"
            ).first()

            assert invoice is not None
            assert invoice.client_name == "Acme Corp"
            assert invoice.amount_total == 1500.00
            assert invoice.confidence >= 0.8
            assert invoice.status == "pending"

            # Verify audit log
            action = db_session.query(InvoiceAction).filter_by(
                invoice_id=invoice.id,
                action_type="detected"
            ).first()

            assert action is not None
            assert action.actor == "system"

    async def test_detection_low_confidence_needs_confirmation(
        self,
        db_session,
        tenant_id,
        mock_gmail_response,
        mock_llm_detection_response,
        mock_llm_extraction_response
    ):
        """Test detection with low confidence requiring human confirmation."""
        agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)

        # Modify response to have low confidence
        low_conf_extraction = mock_llm_extraction_response.copy()
        low_conf_extraction["confidence"] = 0.65

        with patch('src.services.invoice_detection_service.InvoiceDetectionService.scan_gmail') as mock_scan, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService.detect_invoice') as mock_detect, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService.extract_data') as mock_extract, \
             patch('src.integrations.slack.SlackNotifier.send_invoice_confirmation') as mock_slack:

            mock_scan.return_value = [mock_gmail_response["messages"][0]]
            mock_detect.return_value = mock_llm_detection_response
            mock_extract.return_value = low_conf_extraction
            mock_slack.return_value = {"ts": "123456.789"}

            # Run detection flow
            state = DetectionState(
                tenant_id=tenant_id,
                emails_to_scan=[],
                detected_invoices=[],
                pending_confirmation=[]
            )

            result = await agent.run_detection_flow(state)

            # Verify results
            assert len(result["pending_confirmation"]) == 1

            # Verify Slack notification was sent
            mock_slack.assert_called_once()

            # Verify invoice is in draft status
            invoice = db_session.query(Invoice).filter_by(
                tenant_id=tenant_id,
                invoice_number="INV-001"
            ).first()

            assert invoice.status == "draft"
            assert invoice.confidence < 0.8

    async def test_detection_no_invoices_found(
        self,
        db_session,
        tenant_id
    ):
        """Test detection when no invoices are found."""
        agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)

        with patch('src.services.invoice_detection_service.InvoiceDetectionService.scan_gmail') as mock_scan:
            mock_scan.return_value = []

            state = DetectionState(
                tenant_id=tenant_id,
                emails_to_scan=[],
                detected_invoices=[],
                pending_confirmation=[]
            )

            result = await agent.run_detection_flow(state)

            assert len(result["detected_invoices"]) == 0
            assert len(result["pending_confirmation"]) == 0


@pytest.mark.asyncio
class TestReminderFlow:
    """Test the reminder workflow."""

    async def test_reminder_due_and_approved(
        self,
        db_session,
        tenant_id,
        mock_llm_reminder_draft
    ):
        """Test reminder flow when reminder is due and approved."""
        # Create test invoice
        invoice = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg123",
            invoice_number="INV-001",
            client_name="Acme Corp",
            client_email="client@example.com",
            amount_total=1500.00,
            currency="EUR",
            issue_date=datetime.now().date() - timedelta(days=30),
            due_date=datetime.now().date() + timedelta(days=3),  # Due in 3 days
            status="pending",
            confidence=0.95
        )
        db_session.add(invoice)
        db_session.commit()

        agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)

        with patch('src.services.reminder_service.ReminderService.get_due_reminders') as mock_get_due, \
             patch('src.agents.invoice_pilot.InvoicePilotAgent._draft_reminder_message') as mock_draft, \
             patch('src.integrations.slack.SlackNotifier.send_reminder_approval') as mock_slack, \
             patch('src.integrations.gmail.GmailService.send_email') as mock_gmail:

            # Mock reminder scheduled for today
            reminder = InvoiceReminder(
                invoice_id=invoice.id,
                scheduled_at=datetime.now(),
                type="pre_due",
                status="pending"
            )
            db_session.add(reminder)
            db_session.commit()

            mock_get_due.return_value = [reminder]
            mock_draft.return_value = mock_llm_reminder_draft
            mock_slack.return_value = {"ts": "123456.789"}
            mock_gmail.return_value = {"id": "sent_msg_123"}

            # Run reminder flow
            state = ReminderState(
                tenant_id=tenant_id,
                due_reminders=[],
                drafted_reminders=[],
                approved_reminders=[]
            )

            result = await agent.run_reminder_flow(state)

            # Verify draft was created
            assert len(result["drafted_reminders"]) == 1

            # Simulate approval
            reminder.status = "approved"
            reminder.final_message = mock_llm_reminder_draft["message"]
            reminder.approved_by = "user123"
            db_session.commit()

            # Send reminder
            mock_gmail.assert_not_called()  # Not called in draft phase

            # Verify audit log
            action = db_session.query(InvoiceAction).filter_by(
                invoice_id=invoice.id,
                action_type="reminder_drafted"
            ).first()

            assert action is not None

    async def test_no_reminders_due(
        self,
        db_session,
        tenant_id
    ):
        """Test reminder flow when no reminders are due."""
        agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)

        with patch('src.services.reminder_service.ReminderService.get_due_reminders') as mock_get_due:
            mock_get_due.return_value = []

            state = ReminderState(
                tenant_id=tenant_id,
                due_reminders=[],
                drafted_reminders=[],
                approved_reminders=[]
            )

            result = await agent.run_reminder_flow(state)

            assert len(result["due_reminders"]) == 0
            assert len(result["drafted_reminders"]) == 0

    async def test_reminder_customization(
        self,
        db_session,
        tenant_id,
        mock_llm_reminder_draft
    ):
        """Test that user can customize reminder message."""
        # Create test invoice and reminder
        invoice = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg123",
            invoice_number="INV-001",
            client_name="Acme Corp",
            client_email="client@example.com",
            amount_total=1500.00,
            currency="EUR",
            issue_date=datetime.now().date() - timedelta(days=30),
            due_date=datetime.now().date() + timedelta(days=3),
            status="pending",
            confidence=0.95
        )
        db_session.add(invoice)
        db_session.commit()

        reminder = InvoiceReminder(
            invoice_id=invoice.id,
            scheduled_at=datetime.now(),
            type="pre_due",
            status="pending",
            draft_message=mock_llm_reminder_draft["message"]
        )
        db_session.add(reminder)
        db_session.commit()

        # User edits the message
        custom_message = "Custom reminder message from user"
        reminder.final_message = custom_message
        reminder.status = "approved"
        reminder.approved_by = "user123"
        db_session.commit()

        # Verify customization
        assert reminder.final_message == custom_message
        assert reminder.final_message != reminder.draft_message


@pytest.mark.asyncio
class TestEscalationFlow:
    """Test the escalation workflow."""

    async def test_escalation_after_multiple_reminders(
        self,
        db_session,
        tenant_id
    ):
        """Test escalation when invoice has 3+ reminders without payment."""
        # Create overdue invoice
        invoice = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg123",
            invoice_number="INV-001",
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
                scheduled_at=datetime.now() - timedelta(days=20 - i*7),
                sent_at=datetime.now() - timedelta(days=20 - i*7),
                type=f"overdue_{i+1}",
                status="sent"
            )
            db_session.add(reminder)
        db_session.commit()

        agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)

        with patch('src.integrations.slack.SlackNotifier.send_escalation_alert') as mock_slack:
            mock_slack.return_value = {"ts": "123456.789"}

            # Run escalation check
            result = await agent.detect_problem_patterns()

            # Verify escalation
            assert len(result["escalated_invoices"]) == 1
            assert result["escalated_invoices"][0]["invoice_id"] == invoice.id

            # Verify Slack alert was sent
            mock_slack.assert_called_once()
            call_args = mock_slack.call_args[1]
            assert "Problem Client Corp" in str(call_args)
            assert "5000.00" in str(call_args)
            assert "30" in str(call_args)  # days overdue

            # Verify audit log
            action = db_session.query(InvoiceAction).filter_by(
                invoice_id=invoice.id,
                action_type="escalated"
            ).first()

            assert action is not None
            assert action.actor == "system"

    async def test_no_escalation_for_paid_invoice(
        self,
        db_session,
        tenant_id
    ):
        """Test that paid invoices are not escalated."""
        # Create paid invoice with reminders
        invoice = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg123",
            invoice_number="INV-001",
            client_name="Good Client Corp",
            client_email="good@example.com",
            amount_total=1500.00,
            amount_paid=1500.00,  # Fully paid
            currency="EUR",
            issue_date=datetime.now().date() - timedelta(days=60),
            due_date=datetime.now().date() - timedelta(days=30),
            status="paid",
            confidence=0.95
        )
        db_session.add(invoice)
        db_session.commit()

        # Create reminders (shouldn't matter since invoice is paid)
        for i in range(3):
            reminder = InvoiceReminder(
                invoice_id=invoice.id,
                scheduled_at=datetime.now() - timedelta(days=20 - i*7),
                sent_at=datetime.now() - timedelta(days=20 - i*7),
                type=f"overdue_{i+1}",
                status="sent"
            )
            db_session.add(reminder)
        db_session.commit()

        agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)

        with patch('src.integrations.slack.SlackNotifier.send_escalation_alert') as mock_slack:
            result = await agent.detect_problem_patterns()

            # Verify no escalation
            assert len(result["escalated_invoices"]) == 0
            mock_slack.assert_not_called()

    async def test_escalation_threshold_configuration(
        self,
        db_session,
        tenant_id
    ):
        """Test that escalation threshold can be configured."""
        # Create invoice with 2 reminders (below default threshold of 3)
        invoice = Invoice(
            tenant_id=tenant_id,
            gmail_message_id="msg123",
            invoice_number="INV-001",
            client_name="Client Corp",
            client_email="client@example.com",
            amount_total=1500.00,
            currency="EUR",
            issue_date=datetime.now().date() - timedelta(days=45),
            due_date=datetime.now().date() - timedelta(days=15),
            status="overdue",
            confidence=0.95
        )
        db_session.add(invoice)
        db_session.commit()

        for i in range(2):
            reminder = InvoiceReminder(
                invoice_id=invoice.id,
                scheduled_at=datetime.now() - timedelta(days=10 - i*5),
                sent_at=datetime.now() - timedelta(days=10 - i*5),
                type=f"overdue_{i+1}",
                status="sent"
            )
            db_session.add(reminder)
        db_session.commit()

        # Test with default threshold (3)
        agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)
        result = await agent.detect_problem_patterns()
        assert len(result["escalated_invoices"]) == 0

        # Test with lower threshold (2)
        agent_low_threshold = InvoicePilotAgent(
            tenant_id=tenant_id,
            db=db_session,
            escalation_threshold=2
        )
        result = await agent_low_threshold.detect_problem_patterns()
        assert len(result["escalated_invoices"]) == 1


@pytest.mark.asyncio
class TestAgentErrorHandling:
    """Test agent error handling and resilience."""

    async def test_gmail_api_failure(
        self,
        db_session,
        tenant_id
    ):
        """Test handling of Gmail API failures."""
        agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)

        with patch('src.services.invoice_detection_service.InvoiceDetectionService.scan_gmail') as mock_scan:
            mock_scan.side_effect = Exception("Gmail API rate limit exceeded")

            state = DetectionState(
                tenant_id=tenant_id,
                emails_to_scan=[],
                detected_invoices=[],
                pending_confirmation=[],
                errors=[]
            )

            result = await agent.run_detection_flow(state)

            # Verify error was captured
            assert len(result["errors"]) == 1
            assert "Gmail API" in result["errors"][0]

    async def test_llm_extraction_failure(
        self,
        db_session,
        tenant_id,
        mock_gmail_response,
        mock_llm_detection_response
    ):
        """Test handling of LLM extraction failures."""
        agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)

        with patch('src.services.invoice_detection_service.InvoiceDetectionService.scan_gmail') as mock_scan, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService.detect_invoice') as mock_detect, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService.extract_data') as mock_extract:

            mock_scan.return_value = [mock_gmail_response["messages"][0]]
            mock_detect.return_value = mock_llm_detection_response
            mock_extract.side_effect = Exception("LLM service unavailable")

            state = DetectionState(
                tenant_id=tenant_id,
                emails_to_scan=[],
                detected_invoices=[],
                pending_confirmation=[],
                errors=[]
            )

            result = await agent.run_detection_flow(state)

            # Verify error was captured and email was skipped
            assert len(result["errors"]) == 1
            assert len(result["detected_invoices"]) == 0

    async def test_slack_notification_failure(
        self,
        db_session,
        tenant_id,
        mock_gmail_response,
        mock_llm_detection_response,
        mock_llm_extraction_response
    ):
        """Test handling of Slack notification failures."""
        agent = InvoicePilotAgent(tenant_id=tenant_id, db=db_session)

        # Low confidence extraction that requires Slack notification
        low_conf_extraction = mock_llm_extraction_response.copy()
        low_conf_extraction["confidence"] = 0.65

        with patch('src.services.invoice_detection_service.InvoiceDetectionService.scan_gmail') as mock_scan, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService.detect_invoice') as mock_detect, \
             patch('src.services.invoice_detection_service.InvoiceDetectionService.extract_data') as mock_extract, \
             patch('src.integrations.slack.SlackNotifier.send_invoice_confirmation') as mock_slack:

            mock_scan.return_value = [mock_gmail_response["messages"][0]]
            mock_detect.return_value = mock_llm_detection_response
            mock_extract.return_value = low_conf_extraction
            mock_slack.side_effect = Exception("Slack API error")

            state = DetectionState(
                tenant_id=tenant_id,
                emails_to_scan=[],
                detected_invoices=[],
                pending_confirmation=[],
                errors=[]
            )

            result = await agent.run_detection_flow(state)

            # Verify error was captured but invoice was still saved
            assert len(result["errors"]) == 1
            assert "Slack" in result["errors"][0]

            # Invoice should still be in DB as draft
            invoice = db_session.query(Invoice).filter_by(
                tenant_id=tenant_id,
                invoice_number="INV-001"
            ).first()

            assert invoice is not None
            assert invoice.status == "draft"
