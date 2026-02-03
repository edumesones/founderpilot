"""Unit tests for AgentAuditLog model."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.core.database import Base
from src.models.agent_audit_log import (
    AgentAuditLog,
    AgentType,
    InboxPilotAction,
    InvoicePilotAction,
    MeetingPilotAction,
)


@pytest.fixture(scope="function")
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class TestAgentAuditLogModel:
    """Tests for AgentAuditLog model."""

    def test_create_audit_log_with_all_fields(self, db_session):
        """Test creating audit log with all fields."""
        user_id = uuid4()
        workflow_id = uuid4()

        log = AgentAuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            workflow_id=workflow_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
            input_summary="Test email",
            output_summary="Category: urgent",
            decision="Classified as urgent",
            confidence=0.95,
            escalated=False,
            authorized_by="agent",
            trace_id="trace_123",
            metadata={"key": "value"},
            rolled_back=False,
        )

        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.user_id == user_id
        assert log.workflow_id == workflow_id
        assert log.agent_type == AgentType.INBOX_PILOT
        assert log.action == InboxPilotAction.CLASSIFY_EMAIL
        assert log.confidence == 0.95

    def test_create_audit_log_with_minimal_fields(self, db_session):
        """Test creating audit log with only required fields."""
        user_id = uuid4()

        log = AgentAuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
        )

        db_session.add(log)
        db_session.commit()

        assert log.id is not None
        assert log.user_id == user_id
        assert log.escalated is False  # Default value
        assert log.rolled_back is False  # Default value

    def test_confidence_constraint_rejects_negative_value(self, db_session):
        """Test confidence constraint rejects values < 0."""
        user_id = uuid4()

        log = AgentAuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
            confidence=-0.1,  # Invalid: below 0
        )

        db_session.add(log)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_confidence_constraint_rejects_value_above_one(self, db_session):
        """Test confidence constraint rejects values > 1."""
        user_id = uuid4()

        log = AgentAuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
            confidence=1.1,  # Invalid: above 1
        )

        db_session.add(log)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_confidence_accepts_boundary_values(self, db_session):
        """Test confidence accepts 0.0 and 1.0."""
        user_id = uuid4()

        # Test 0.0
        log1 = AgentAuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
            confidence=0.0,
        )
        db_session.add(log1)
        db_session.commit()
        assert log1.confidence == 0.0

        # Test 1.0
        log2 = AgentAuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
            confidence=1.0,
        )
        db_session.add(log2)
        db_session.commit()
        assert log2.confidence == 1.0

    def test_repr_method(self, db_session):
        """Test __repr__ method returns correct string."""
        user_id = uuid4()

        log = AgentAuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            agent_type=AgentType.INBOX_PILOT,
            action=InboxPilotAction.CLASSIFY_EMAIL,
        )

        db_session.add(log)
        db_session.commit()

        repr_str = repr(log)
        assert "AgentAuditLog" in repr_str
        assert str(log.id) in repr_str
        assert AgentType.INBOX_PILOT in repr_str
        assert InboxPilotAction.CLASSIFY_EMAIL in repr_str


class TestAgentTypeConstants:
    """Tests for AgentType constants."""

    def test_agent_type_constants_exist(self):
        """Test all agent type constants are defined."""
        assert AgentType.INBOX_PILOT == "inbox_pilot"
        assert AgentType.INVOICE_PILOT == "invoice_pilot"
        assert AgentType.MEETING_PILOT == "meeting_pilot"


class TestActionConstants:
    """Tests for action constants."""

    def test_inbox_pilot_action_constants(self):
        """Test InboxPilot action constants are defined."""
        assert InboxPilotAction.CLASSIFY_EMAIL == "classify_email"
        assert InboxPilotAction.DRAFT_RESPONSE == "draft_response"
        assert InboxPilotAction.SEND_RESPONSE == "send_response"
        assert InboxPilotAction.ARCHIVE_EMAIL == "archive_email"
        assert InboxPilotAction.FLAG_EMAIL == "flag_email"
        assert InboxPilotAction.ESCALATE_TO_HUMAN == "escalate_to_human"

    def test_invoice_pilot_action_constants(self):
        """Test InvoicePilot action constants are defined."""
        assert InvoicePilotAction.DETECT_INVOICE == "detect_invoice"
        assert InvoicePilotAction.EXTRACT_INVOICE_DATA == "extract_invoice_data"
        assert InvoicePilotAction.MATCH_INVOICE == "match_invoice"
        assert InvoicePilotAction.SEND_REMINDER == "send_reminder"
        assert InvoicePilotAction.ESCALATE_TO_HUMAN == "escalate_to_human"

    def test_meeting_pilot_action_constants(self):
        """Test MeetingPilot action constants are defined."""
        assert MeetingPilotAction.SCHEDULE_MEETING == "schedule_meeting"
        assert MeetingPilotAction.SEND_REMINDER == "send_reminder"
        assert MeetingPilotAction.RESCHEDULE_MEETING == "reschedule_meeting"
        assert MeetingPilotAction.CANCEL_MEETING == "cancel_meeting"
        assert MeetingPilotAction.ESCALATE_TO_HUMAN == "escalate_to_human"
