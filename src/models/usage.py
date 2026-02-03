"""Usage tracking models for events and counters."""
from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.models.base import Base


class UsageEvent(Base):
    """
    Individual usage event - audit trail for all agent actions.

    Each event represents a single billable action by an agent.
    Events are immutable and never deleted (retained for 90 days).
    """

    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent = Column(String(20), nullable=False)  # 'inbox', 'invoice', 'meeting'
    action_type = Column(String(50), nullable=False)  # 'email_processed', 'invoice_detected', 'meeting_prep'
    resource_id = Column(UUID(as_uuid=True), nullable=True)  # FK to specific resource (email_record, etc)
    quantity = Column(Integer, nullable=False, default=1)  # Usually 1, allows batch actions
    idempotency_key = Column(String(255), unique=True, nullable=False)  # Prevents duplicate events
    metadata = Column(JSONB, nullable=True)  # Extra context
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_usage_events_tenant_agent', 'tenant_id', 'agent', 'created_at'),
        Index('idx_usage_events_idempotency', 'idempotency_key'),
    )

    def __repr__(self) -> str:
        return f"<UsageEvent {self.id} ({self.agent}/{self.action_type})>"


class UsageCounter(Base):
    """
    Aggregated usage counter - performance cache for fast queries.

    One counter per (tenant, agent, billing period).
    Counter.count must equal sum(UsageEvent.quantity) for the period.
    """

    __tablename__ = "usage_counters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent = Column(String(20), nullable=False)  # 'inbox', 'invoice', 'meeting'
    period_start = Column(DateTime, nullable=False)  # subscription.current_period_start
    period_end = Column(DateTime, nullable=False)    # subscription.current_period_end
    count = Column(Integer, nullable=False, default=0)  # Incremented atomically
    last_event_at = Column(DateTime, nullable=True)  # Timestamp of most recent event
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint('tenant_id', 'agent', 'period_start', name='uq_usage_counter_tenant_agent_period'),
        CheckConstraint('count >= 0', name='ck_usage_counter_count_non_negative'),
        Index('idx_usage_counters_tenant_period', 'tenant_id', 'period_start'),
    )

    def __repr__(self) -> str:
        return f"<UsageCounter {self.tenant_id}/{self.agent} ({self.count})>"

    @property
    def usage_percentage(self) -> Optional[int]:
        """Calculate usage percentage if limit is known (requires plan context)."""
        # Note: Limit comes from Plan model, not stored in counter
        # This is a helper property, actual calculation in UsageService
        return None
