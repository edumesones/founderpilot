"""Usage tracker service for recording agent usage events."""
from datetime import datetime
from typing import Optional
from uuid import UUID
import logging

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.models.usage import UsageEvent, UsageCounter
from src.models.billing import Subscription

logger = logging.getLogger(__name__)


class UsageTracker:
    """
    Service for tracking agent usage with atomic event recording and counter updates.

    This service ensures that usage events are recorded with idempotency guarantees
    and counters are incremented atomically in a single transaction.
    """

    def __init__(self, db: Session):
        self.db = db

    def track_event(
        self,
        tenant_id: UUID,
        agent: str,
        action_type: str,
        resource_id: Optional[UUID] = None,
        quantity: int = 1,
        metadata: Optional[dict] = None,
    ) -> UsageEvent:
        """
        Record a usage event and increment the corresponding counter atomically.

        Args:
            tenant_id: UUID of the tenant
            agent: Agent type ('inbox', 'invoice', 'meeting')
            action_type: Type of action performed
            resource_id: Optional UUID of the resource (email, invoice, meeting)
            quantity: Number of units (default 1)
            metadata: Optional metadata dictionary

        Returns:
            UsageEvent: The created usage event

        Raises:
            ValueError: If tenant has no active subscription or invalid parameters
            IntegrityError: If idempotency key already exists (duplicate event)
        """
        # Validate agent type
        valid_agents = ["inbox", "invoice", "meeting"]
        if agent not in valid_agents:
            raise ValueError(f"Invalid agent type: {agent}. Must be one of {valid_agents}")

        # Generate idempotency key
        idempotency_key = self._generate_idempotency_key(
            tenant_id, agent, action_type, resource_id
        )

        try:
            # Start transaction - will be committed by the session context
            # Create usage event
            event = UsageEvent(
                tenant_id=tenant_id,
                agent=agent,
                action_type=action_type,
                resource_id=resource_id,
                quantity=quantity,
                idempotency_key=idempotency_key,
                metadata=metadata,
            )
            self.db.add(event)

            # Update or create counter atomically
            counter = self._get_or_create_counter(tenant_id, agent)
            counter.count += quantity
            counter.last_event_at = datetime.utcnow()

            # Flush to detect any constraint violations before commit
            self.db.flush()

            logger.info(
                "UsageEvent created",
                extra={
                    "tenant_id": str(tenant_id),
                    "agent": agent,
                    "action_type": action_type,
                    "quantity": quantity,
                    "counter_count": counter.count,
                },
            )

            return event

        except IntegrityError as e:
            # Idempotency key violation - event already recorded
            self.db.rollback()
            logger.warning(
                "Duplicate usage event detected (idempotency)",
                extra={
                    "tenant_id": str(tenant_id),
                    "agent": agent,
                    "action_type": action_type,
                    "idempotency_key": idempotency_key,
                },
            )
            raise IntegrityError(
                f"Duplicate event: {idempotency_key}",
                params=None,
                orig=e.orig,
            )
        except Exception as e:
            self.db.rollback()
            logger.error(
                "Failed to track usage event",
                extra={
                    "tenant_id": str(tenant_id),
                    "agent": agent,
                    "action_type": action_type,
                    "error": str(e),
                },
            )
            raise

    def _generate_idempotency_key(
        self,
        tenant_id: UUID,
        agent: str,
        action_type: str,
        resource_id: Optional[UUID],
    ) -> str:
        """
        Generate a unique idempotency key to prevent duplicate event recording.

        Format: {tenant_id}:{agent}:{resource_id}:{action_type}:{timestamp_ms}

        Args:
            tenant_id: Tenant UUID
            agent: Agent type
            action_type: Action type
            resource_id: Optional resource UUID

        Returns:
            str: Unique idempotency key
        """
        timestamp_ms = int(datetime.utcnow().timestamp() * 1000)
        resource_part = str(resource_id) if resource_id else "none"
        return f"{tenant_id}:{agent}:{resource_part}:{action_type}:{timestamp_ms}"

    def _get_or_create_counter(self, tenant_id: UUID, agent: str) -> UsageCounter:
        """
        Get existing counter for current billing period or create a new one.

        Args:
            tenant_id: Tenant UUID
            agent: Agent type

        Returns:
            UsageCounter: The counter for the current period

        Raises:
            ValueError: If tenant has no active subscription
        """
        # Get subscription to find current billing period
        subscription = (
            self.db.query(Subscription)
            .filter(Subscription.tenant_id == tenant_id)
            .first()
        )

        if not subscription:
            raise ValueError(f"Tenant {tenant_id} has no subscription")

        if not subscription.current_period_start or not subscription.current_period_end:
            raise ValueError(
                f"Tenant {tenant_id} subscription has no billing period defined"
            )

        # Find existing counter for current period
        counter = (
            self.db.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.agent == agent,
                UsageCounter.period_start == subscription.current_period_start,
            )
            .first()
        )

        if not counter:
            # Create new counter for this period
            counter = UsageCounter(
                tenant_id=tenant_id,
                agent=agent,
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
                count=0,
            )
            self.db.add(counter)
            self.db.flush()  # Get ID assigned

            logger.info(
                "Created new usage counter",
                extra={
                    "tenant_id": str(tenant_id),
                    "agent": agent,
                    "period_start": subscription.current_period_start.isoformat(),
                    "period_end": subscription.current_period_end.isoformat(),
                },
            )

        return counter

    def get_current_count(self, tenant_id: UUID, agent: str) -> int:
        """
        Get current usage count for a tenant and agent.

        Args:
            tenant_id: Tenant UUID
            agent: Agent type

        Returns:
            int: Current usage count (0 if no counter exists)
        """
        try:
            counter = self._get_or_create_counter(tenant_id, agent)
            return counter.count
        except ValueError:
            # No subscription or no period defined
            return 0
