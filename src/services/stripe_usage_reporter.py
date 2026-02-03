"""Stripe usage reporting service with circuit breaker pattern."""
from datetime import datetime, timedelta
from typing import Optional
import logging
import time

import stripe
from stripe.error import StripeError

logger = logging.getLogger(__name__)


class CircuitBreakerError(Exception):
    """Circuit breaker is open, rejecting requests."""
    pass


class StripeUsageReporter:
    """
    Service for reporting usage to Stripe metered billing with circuit breaker.

    Circuit breaker pattern:
    - After 5 consecutive failures, circuit opens (stops accepting requests)
    - Circuit stays open for 15 minutes (cooldown period)
    - After cooldown, circuit enters half-open state (allows 1 test request)
    - If test succeeds, circuit closes (normal operation)
    - If test fails, circuit reopens for another cooldown period
    """

    def __init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.circuit_open_until: Optional[datetime] = None
        self.max_failures = 5
        self.cooldown_minutes = 15

    def report_usage(
        self,
        subscription_item_id: str,
        quantity: int,
        timestamp: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> bool:
        """
        Report usage to Stripe metered billing.

        Args:
            subscription_item_id: Stripe subscription item ID for the metered component
            quantity: Usage quantity to report
            timestamp: Unix timestamp (defaults to current time)
            idempotency_key: Optional idempotency key for safe retries

        Returns:
            bool: True if successful, False otherwise

        Raises:
            CircuitBreakerError: If circuit breaker is open
            StripeError: If Stripe API call fails (after circuit breaker check)
        """
        # Check circuit breaker
        if self._is_circuit_open():
            logger.warning(
                "Circuit breaker is open, rejecting Stripe usage report",
                extra={
                    "circuit_open_until": self.circuit_open_until.isoformat() if self.circuit_open_until else None,
                },
            )
            raise CircuitBreakerError("Circuit breaker is open, Stripe API unavailable")

        timestamp = timestamp or int(time.time())

        try:
            # Report usage to Stripe
            usage_record = stripe.SubscriptionItem.create_usage_record(
                subscription_item_id,
                quantity=quantity,
                timestamp=timestamp,
                action="set",  # 'set' replaces previous value, 'increment' adds to it
                idempotency_key=idempotency_key,
            )

            # Success - reset failure count
            self._record_success()

            logger.info(
                "Successfully reported usage to Stripe",
                extra={
                    "subscription_item_id": subscription_item_id,
                    "quantity": quantity,
                    "timestamp": timestamp,
                    "usage_record_id": usage_record.id,
                },
            )

            return True

        except StripeError as e:
            # Failure - increment failure count and check circuit breaker
            self._record_failure()

            logger.error(
                f"Failed to report usage to Stripe: {e}",
                extra={
                    "subscription_item_id": subscription_item_id,
                    "quantity": quantity,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "failure_count": self.failure_count,
                },
            )

            raise

    def _is_circuit_open(self) -> bool:
        """
        Check if circuit breaker is open.

        Returns:
            bool: True if circuit is open (rejecting requests)
        """
        if self.circuit_open_until is None:
            return False

        # Check if cooldown period has passed
        if datetime.utcnow() >= self.circuit_open_until:
            # Cooldown passed, enter half-open state
            logger.info(
                "Circuit breaker cooldown complete, entering half-open state",
                extra={
                    "circuit_was_open_until": self.circuit_open_until.isoformat(),
                },
            )
            self.circuit_open_until = None
            return False

        # Still in cooldown period
        return True

    def _record_success(self):
        """Record successful Stripe API call."""
        self.success_count += 1
        self.failure_count = 0  # Reset failure count on success

        # Close circuit if it was open
        if self.circuit_open_until is not None:
            logger.info(
                "Circuit breaker test successful, closing circuit",
                extra={
                    "success_count": self.success_count,
                },
            )
            self.circuit_open_until = None

    def _record_failure(self):
        """Record failed Stripe API call and potentially open circuit."""
        self.failure_count += 1

        # Open circuit if failure threshold exceeded
        if self.failure_count >= self.max_failures:
            self.circuit_open_until = datetime.utcnow() + timedelta(minutes=self.cooldown_minutes)

            logger.error(
                f"Circuit breaker OPENED after {self.failure_count} consecutive failures",
                extra={
                    "failure_count": self.failure_count,
                    "circuit_open_until": self.circuit_open_until.isoformat(),
                    "cooldown_minutes": self.cooldown_minutes,
                },
            )

    def get_status(self) -> dict:
        """
        Get current circuit breaker status.

        Returns:
            dict: Status information
        """
        is_open = self._is_circuit_open()

        return {
            "circuit_status": "open" if is_open else "closed",
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "circuit_open_until": self.circuit_open_until.isoformat() if self.circuit_open_until else None,
            "max_failures": self.max_failures,
            "cooldown_minutes": self.cooldown_minutes,
        }


# Global instance for worker tasks
stripe_usage_reporter = StripeUsageReporter()
