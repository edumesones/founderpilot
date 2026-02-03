"""Celery tasks for usage tracking background jobs."""
from datetime import datetime
from typing import Dict, List
import logging
import time

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.core.database import SessionLocal
from src.models.usage import UsageEvent, UsageCounter
from src.models.billing import Subscription, Plan
from src.services.stripe_usage_reporter import stripe_usage_reporter, CircuitBreakerError
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="reset_usage_counters")
def reset_usage_counters() -> Dict[str, int]:
    """
    Check all active subscriptions and create new counters when billing period rolls over.

    This task runs daily at 00:05 UTC to detect period rollovers and initialize
    new counters for the new billing period.

    Returns:
        Dict with statistics: counters_created, subscriptions_checked
    """
    db = SessionLocal()
    try:
        # Get all active subscriptions (trial or active status)
        subscriptions = (
            db.query(Subscription)
            .filter(Subscription.status.in_(["trial", "active"]))
            .all()
        )

        counters_created = 0
        subscriptions_checked = len(subscriptions)

        logger.info(f"Checking {subscriptions_checked} active subscriptions for period rollover")

        for subscription in subscriptions:
            # For each agent type, check if counter exists for current period
            for agent in ["inbox", "invoice", "meeting"]:
                existing_counter = (
                    db.query(UsageCounter)
                    .filter(
                        UsageCounter.tenant_id == subscription.tenant_id,
                        UsageCounter.agent == agent,
                        UsageCounter.period_start == subscription.current_period_start,
                    )
                    .first()
                )

                if not existing_counter:
                    # Create new counter for new billing period
                    new_counter = UsageCounter(
                        tenant_id=subscription.tenant_id,
                        agent=agent,
                        period_start=subscription.current_period_start,
                        period_end=subscription.current_period_end,
                        count=0,
                    )
                    db.add(new_counter)
                    counters_created += 1

                    logger.info(
                        "Created new usage counter",
                        extra={
                            "tenant_id": str(subscription.tenant_id),
                            "agent": agent,
                            "period_start": subscription.current_period_start.isoformat(),
                        },
                    )

        db.commit()

        logger.info(
            f"Reset usage counters complete: created {counters_created} new counters",
            extra={
                "counters_created": counters_created,
                "subscriptions_checked": subscriptions_checked,
            },
        )

        return {
            "counters_created": counters_created,
            "subscriptions_checked": subscriptions_checked,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reset usage counters: {e}", exc_info=True)
        raise
    finally:
        db.close()


@celery_app.task(
    name="report_overage_to_stripe",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def report_overage_to_stripe(self) -> Dict[str, int]:
    """
    Report overage usage to Stripe for all active subscriptions.

    This task runs daily at 01:00 UTC and at the end of billing periods.
    Uses circuit breaker pattern: stops after 5 consecutive failures.

    Returns:
        Dict with statistics: success_count, failure_count, skipped_count

    Raises:
        Exception: If task should be retried
    """
    db = SessionLocal()
    try:
        # Get all counters for current periods with potential overage
        counters_query = (
            db.query(UsageCounter, Subscription, Plan)
            .join(Subscription, UsageCounter.tenant_id == Subscription.tenant_id)
            .join(Plan, Subscription.plan_id == Plan.id)
            .filter(Subscription.status == "active")
            .filter(UsageCounter.period_start == Subscription.current_period_start)
        )

        results = counters_query.all()

        success_count = 0
        failure_count = 0
        skipped_count = 0

        logger.info(f"Checking {len(results)} counters for overage reporting")

        for counter, subscription, plan in results:
            # Get limit for this agent from plan
            limit = _get_limit_for_agent(plan, counter.agent)
            overage = max(0, counter.count - limit)

            if overage == 0:
                skipped_count += 1
                continue

            try:
                # Generate idempotency key for safe retries
                idempotency_key = f"overage_{counter.tenant_id}_{counter.agent}_{counter.period_start.strftime('%Y%m%d')}"

                # Report to Stripe via usage reporter (with circuit breaker)
                # Note: subscription_item_id would come from subscription metadata
                # For now, using subscription_id as placeholder
                subscription_item_id = subscription.stripe_subscription_id

                stripe_usage_reporter.report_usage(
                    subscription_item_id=subscription_item_id,
                    quantity=overage,
                    timestamp=int(time.time()),
                    idempotency_key=idempotency_key,
                )

                success_count += 1
                logger.info(
                    "Reported overage to Stripe",
                    extra={
                        "tenant_id": str(counter.tenant_id),
                        "agent": counter.agent,
                        "overage": overage,
                        "subscription_id": subscription.stripe_subscription_id,
                    },
                )

            except CircuitBreakerError as e:
                # Circuit breaker is open, abort entire batch
                logger.error("Circuit breaker is open, aborting overage reporting batch")
                break

            except Exception as e:
                failure_count += 1
                logger.error(
                    f"Failed to report overage to Stripe for tenant {counter.tenant_id}, agent {counter.agent}: {e}",
                    extra={
                        "tenant_id": str(counter.tenant_id),
                        "agent": counter.agent,
                        "error": str(e),
                    },
                )
                # Continue to next tenant (circuit breaker handles abort logic)

        logger.info(
            f"Overage reporting complete: {success_count} success, {failure_count} failures, {skipped_count} skipped",
            extra={
                "success_count": success_count,
                "failure_count": failure_count,
                "skipped_count": skipped_count,
            },
        )

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "skipped_count": skipped_count,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to report overage to Stripe: {e}", exc_info=True)
        # Retry task after delay
        raise self.retry(exc=e, countdown=300)
    finally:
        db.close()


@celery_app.task(name="reconcile_usage_counters")
def reconcile_usage_counters() -> Dict[str, int]:
    """
    Reconcile usage counters with event logs to detect and fix drift.

    Compares sum(usage_events.quantity) vs usage_counter.count for each counter.
    Auto-corrects if drift < 5%, alerts if drift >= 5%.

    This task runs daily at 03:00 UTC.

    Returns:
        Dict with statistics: drift_detected, auto_corrected, high_drift_alerts
    """
    db = SessionLocal()
    try:
        # Get all current period counters
        counters = (
            db.query(UsageCounter, Subscription)
            .join(Subscription, UsageCounter.tenant_id == Subscription.tenant_id)
            .filter(UsageCounter.period_start == Subscription.current_period_start)
            .all()
        )

        drift_detected = 0
        auto_corrected = 0
        high_drift_alerts = 0

        logger.info(f"Reconciling {len(counters)} usage counters")

        for counter, subscription in counters:
            # Calculate actual sum from events
            events_sum = (
                db.query(func.sum(UsageEvent.quantity))
                .filter(
                    UsageEvent.tenant_id == counter.tenant_id,
                    UsageEvent.agent == counter.agent,
                    UsageEvent.created_at >= counter.period_start,
                    UsageEvent.created_at < counter.period_end,
                )
                .scalar()
            ) or 0

            # Check for drift
            diff = abs(events_sum - counter.count)
            drift_pct = (diff / events_sum * 100) if events_sum > 0 else 0

            if drift_pct > 0.1:  # More than 0.1% drift
                drift_detected += 1

                logger.warning(
                    f"Counter drift detected: tenant={counter.tenant_id}, agent={counter.agent}, "
                    f"counter={counter.count}, events_sum={events_sum}, diff={diff}, drift={drift_pct:.2f}%",
                    extra={
                        "tenant_id": str(counter.tenant_id),
                        "agent": counter.agent,
                        "counter_count": counter.count,
                        "events_sum": events_sum,
                        "diff": diff,
                        "drift_pct": drift_pct,
                    },
                )

                if drift_pct < 5:  # Auto-correct if less than 5%
                    counter.count = events_sum
                    db.commit()
                    auto_corrected += 1

                    logger.info(
                        f"Auto-corrected counter drift: {counter.tenant_id}/{counter.agent}",
                        extra={
                            "tenant_id": str(counter.tenant_id),
                            "agent": counter.agent,
                            "old_count": counter.count,
                            "new_count": events_sum,
                        },
                    )
                else:
                    # High drift - alert for manual investigation
                    high_drift_alerts += 1
                    logger.error(
                        f"HIGH DRIFT DETECTED (>= 5%): tenant={counter.tenant_id}, "
                        f"agent={counter.agent}, drift={drift_pct:.2f}%",
                        extra={
                            "tenant_id": str(counter.tenant_id),
                            "agent": counter.agent,
                            "counter_count": counter.count,
                            "events_sum": events_sum,
                            "drift_pct": drift_pct,
                            "severity": "high",
                        },
                    )

        logger.info(
            f"Reconciliation complete: {drift_detected} drift detected, {auto_corrected} auto-corrected, {high_drift_alerts} high drift alerts",
            extra={
                "drift_detected": drift_detected,
                "auto_corrected": auto_corrected,
                "high_drift_alerts": high_drift_alerts,
            },
        )

        return {
            "drift_detected": drift_detected,
            "auto_corrected": auto_corrected,
            "high_drift_alerts": high_drift_alerts,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reconcile usage counters: {e}", exc_info=True)
        raise
    finally:
        db.close()


def _get_limit_for_agent(plan: Plan, agent: str) -> int:
    """
    Helper function to extract limit for agent from plan.limits JSONB.

    Args:
        plan: Plan object
        agent: Agent type ('inbox', 'invoice', 'meeting')

    Returns:
        int: Usage limit for the agent
    """
    limit_key_map = {
        "inbox": "emails_per_month",
        "invoice": "invoices_per_month",
        "meeting": "meetings_per_month",
    }

    limit_key = limit_key_map.get(agent)
    if not limit_key:
        return 0

    return plan.limits.get(limit_key, 0)
