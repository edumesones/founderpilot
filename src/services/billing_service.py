"""Billing service for subscription management and Stripe integration."""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import logging

import stripe
from sqlalchemy.orm import Session

from src.core.config import settings
from src.models.billing import Plan, Subscription, Invoice, StripeEvent
from src.schemas.billing import (
    SubscriptionResponse,
    SubscriptionData,
    SubscriptionPlan,
    UsageData,
    UsageResponse,
    PlanResponse,
    InvoiceResponse,
)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


class BillingService:
    """Service for handling billing operations with Stripe."""

    def __init__(self, db: Session):
        self.db = db

    # --- Plans ---

    def get_active_plans(self) -> list[PlanResponse]:
        """Get all active plans."""
        plans = self.db.query(Plan).filter(Plan.is_active == True).all()
        return [PlanResponse.model_validate(p) for p in plans]

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan by ID."""
        return self.db.query(Plan).filter(Plan.id == plan_id).first()

    # --- Subscription ---

    def get_subscription(self, tenant_id: UUID) -> Optional[Subscription]:
        """Get subscription for a tenant."""
        return (
            self.db.query(Subscription)
            .filter(Subscription.tenant_id == tenant_id)
            .first()
        )

    def get_subscription_with_usage(self, tenant_id: UUID) -> SubscriptionResponse:
        """Get subscription with current usage data."""
        sub = self.get_subscription(tenant_id)
        if not sub:
            raise ValueError("No subscription found for tenant")

        # Build subscription data
        plan_data = None
        if sub.plan:
            plan_data = SubscriptionPlan(
                id=sub.plan.id,
                name=sub.plan.name,
                price=sub.plan.price_cents,
                agents=sub.plan.agents_included,
            )

        subscription_data = SubscriptionData(
            id=sub.stripe_subscription_id or str(sub.id),
            status=sub.status,
            plan=plan_data,
            trial_ends_at=sub.trial_ends_at,
            trial_days_remaining=sub.days_remaining_in_trial,
            current_period_end=sub.current_period_end,
            cancel_at_period_end=sub.cancel_at_period_end,
        )

        # Get usage data (placeholder - will integrate with FEAT-008)
        usage = self._calculate_usage(tenant_id, sub)

        return SubscriptionResponse(subscription=subscription_data, usage=usage)

    def create_trial_subscription(
        self, tenant_id: UUID, email: str
    ) -> Subscription:
        """Create a trial subscription for a new user.

        Called from FEAT-001 Auth & Onboarding after user signup.
        """
        # Check if subscription already exists
        existing = self.get_subscription(tenant_id)
        if existing:
            logger.warning(f"Subscription already exists for tenant {tenant_id}")
            return existing

        # Create Stripe Customer
        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={"tenant_id": str(tenant_id)},
            )
        except stripe.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise ValueError(f"Failed to create Stripe customer: {e}")

        # Create local subscription in trial status
        trial_ends = datetime.utcnow() + timedelta(days=settings.TRIAL_DAYS)
        subscription = Subscription(
            tenant_id=tenant_id,
            stripe_customer_id=customer.id,
            status="trial",
            trial_ends_at=trial_ends,
            current_period_start=datetime.utcnow(),
            current_period_end=trial_ends,
        )
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)

        logger.info(f"Created trial subscription for tenant {tenant_id}")
        return subscription

    # --- Checkout ---

    def create_checkout_session(
        self,
        tenant_id: UUID,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe Checkout session for subscription."""
        sub = self.get_subscription(tenant_id)
        if not sub:
            raise ValueError("No subscription found for tenant")

        if sub.status == "active":
            raise ValueError("Already have an active subscription. Use portal to change plans.")

        try:
            session = stripe.checkout.Session.create(
                customer=sub.stripe_customer_id,
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=cancel_url,
                subscription_data={
                    "metadata": {"tenant_id": str(tenant_id)},
                },
                allow_promotion_codes=True,
            )
        except stripe.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise ValueError(f"Failed to create checkout session: {e}")

        return session.url

    # --- Portal ---

    def create_portal_session(self, tenant_id: UUID, return_url: str) -> str:
        """Create a Stripe Customer Portal session."""
        sub = self.get_subscription(tenant_id)
        if not sub:
            raise ValueError("No subscription found for tenant")

        try:
            session = stripe.billing_portal.Session.create(
                customer=sub.stripe_customer_id,
                return_url=return_url,
            )
        except stripe.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise ValueError(f"Failed to create portal session: {e}")

        return session.url

    # --- Webhooks ---

    def handle_webhook(self, payload: bytes, signature: str) -> None:
        """Process a Stripe webhook event."""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise ValueError(f"Invalid webhook payload: {e}")
        except stripe.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise ValueError(f"Invalid webhook signature: {e}")

        # Idempotency check
        if self._event_already_processed(event.id):
            logger.info(f"Event {event.id} already processed, skipping")
            return

        # Route to handler
        handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
        }

        handler = handlers.get(event.type)
        if handler:
            logger.info(f"Processing webhook event: {event.type}")
            handler(event.data.object)
        else:
            logger.debug(f"Unhandled webhook event type: {event.type}")

        # Mark event as processed
        self._mark_event_processed(event.id, event.type)

    def _handle_checkout_completed(self, session: dict) -> None:
        """Handle successful checkout - activate subscription."""
        # Get tenant_id from metadata
        tenant_id = session.get("metadata", {}).get("tenant_id")
        if not tenant_id:
            # Try getting from subscription metadata
            sub_data = session.get("subscription_data", {})
            tenant_id = sub_data.get("metadata", {}).get("tenant_id")

        if not tenant_id:
            logger.error("No tenant_id in checkout session metadata")
            return

        # Get subscription details from Stripe
        stripe_sub_id = session.get("subscription")
        if not stripe_sub_id:
            logger.error("No subscription ID in checkout session")
            return

        try:
            stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
        except stripe.StripeError as e:
            logger.error(f"Failed to retrieve subscription: {e}")
            return

        # Update local subscription
        sub = (
            self.db.query(Subscription)
            .filter(Subscription.tenant_id == tenant_id)
            .first()
        )

        if sub:
            sub.stripe_subscription_id = stripe_sub.id
            sub.plan_id = stripe_sub["items"]["data"][0]["price"]["id"]
            sub.status = "active"
            sub.trial_ends_at = None
            sub.current_period_start = datetime.fromtimestamp(
                stripe_sub.current_period_start
            )
            sub.current_period_end = datetime.fromtimestamp(
                stripe_sub.current_period_end
            )
            self.db.commit()
            logger.info(f"Activated subscription for tenant {tenant_id}")

    def _handle_invoice_paid(self, invoice: dict) -> None:
        """Handle successful payment - log invoice."""
        stripe_sub_id = invoice.get("subscription")
        if not stripe_sub_id:
            return

        sub = (
            self.db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_sub_id)
            .first()
        )

        if sub:
            # Ensure subscription is active
            sub.status = "active"

            # Check if invoice already logged
            existing = (
                self.db.query(Invoice)
                .filter(Invoice.stripe_invoice_id == invoice["id"])
                .first()
            )
            if existing:
                return

            # Log the invoice
            inv = Invoice(
                tenant_id=sub.tenant_id,
                subscription_id=sub.id,
                stripe_invoice_id=invoice["id"],
                amount_cents=invoice.get("amount_paid", 0),
                currency=invoice.get("currency", "usd"),
                status="paid",
                period_start=datetime.fromtimestamp(invoice["period_start"])
                if invoice.get("period_start")
                else None,
                period_end=datetime.fromtimestamp(invoice["period_end"])
                if invoice.get("period_end")
                else None,
                paid_at=datetime.utcnow(),
                hosted_invoice_url=invoice.get("hosted_invoice_url"),
            )
            self.db.add(inv)
            self.db.commit()
            logger.info(f"Logged invoice {invoice['id']} for tenant {sub.tenant_id}")

    def _handle_invoice_payment_failed(self, invoice: dict) -> None:
        """Handle failed payment - update subscription status."""
        stripe_sub_id = invoice.get("subscription")
        if not stripe_sub_id:
            return

        sub = (
            self.db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_sub_id)
            .first()
        )

        if sub:
            sub.status = "past_due"
            self.db.commit()
            logger.warning(
                f"Payment failed for tenant {sub.tenant_id}, status set to past_due"
            )
            # TODO: Send notification to user (integrate with FEAT-006 Slack)

    def _handle_subscription_updated(self, stripe_sub: dict) -> None:
        """Handle subscription changes - sync plan and status."""
        sub = (
            self.db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_sub["id"])
            .first()
        )

        if sub:
            sub.plan_id = stripe_sub["items"]["data"][0]["price"]["id"]
            sub.status = stripe_sub["status"]
            sub.current_period_start = datetime.fromtimestamp(
                stripe_sub["current_period_start"]
            )
            sub.current_period_end = datetime.fromtimestamp(
                stripe_sub["current_period_end"]
            )
            sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
            if stripe_sub.get("canceled_at"):
                sub.canceled_at = datetime.fromtimestamp(stripe_sub["canceled_at"])
            self.db.commit()
            logger.info(f"Updated subscription for tenant {sub.tenant_id}")

    def _handle_subscription_deleted(self, stripe_sub: dict) -> None:
        """Handle subscription cancellation."""
        sub = (
            self.db.query(Subscription)
            .filter(Subscription.stripe_subscription_id == stripe_sub["id"])
            .first()
        )

        if sub:
            sub.status = "canceled"
            sub.canceled_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Canceled subscription for tenant {sub.tenant_id}")

    # --- Invoices ---

    def get_invoices(self, tenant_id: UUID) -> list[InvoiceResponse]:
        """Get invoices for a tenant."""
        invoices = (
            self.db.query(Invoice)
            .filter(Invoice.tenant_id == tenant_id)
            .order_by(Invoice.created_at.desc())
            .all()
        )
        return [InvoiceResponse.model_validate(inv) for inv in invoices]

    # --- Usage ---

    def _calculate_usage(
        self, tenant_id: UUID, subscription: Subscription
    ) -> UsageData:
        """Calculate current usage for tenant.

        TODO: Integrate with FEAT-008 Usage Tracking for actual data.
        """
        # For now, return placeholder data
        # In production, query usage tables for current period
        limits = {}
        if subscription.plan:
            limits = subscription.plan.limits or {}

        return UsageData(
            emails_processed=0,
            emails_limit=limits.get("emails_per_month", 500),
            invoices_processed=0,
            invoices_limit=limits.get("invoices_per_month", 50),
            meetings_processed=0,
            meetings_limit=limits.get("meetings_per_month", 30),
        )

    def get_usage(self, tenant_id: UUID) -> UsageResponse:
        """Get detailed usage report for tenant."""
        sub = self.get_subscription(tenant_id)
        if not sub:
            raise ValueError("No subscription found for tenant")

        usage = self._calculate_usage(tenant_id, sub)

        # Calculate overage
        def calc_overage(processed: int, limit: int) -> int:
            return max(0, processed - limit)

        return UsageResponse(
            emails_processed=usage.emails_processed,
            emails_limit=usage.emails_limit,
            emails_overage=calc_overage(usage.emails_processed, usage.emails_limit),
            invoices_processed=usage.invoices_processed,
            invoices_limit=usage.invoices_limit,
            invoices_overage=calc_overage(
                usage.invoices_processed, usage.invoices_limit
            ),
            meetings_processed=usage.meetings_processed,
            meetings_limit=usage.meetings_limit,
            meetings_overage=calc_overage(
                usage.meetings_processed, usage.meetings_limit
            ),
            period_start=sub.current_period_start or datetime.utcnow(),
            period_end=sub.current_period_end
            or (datetime.utcnow() + timedelta(days=30)),
        )

    # --- Helpers ---

    def _event_already_processed(self, event_id: str) -> bool:
        """Check if a Stripe event has already been processed."""
        return (
            self.db.query(StripeEvent).filter(StripeEvent.id == event_id).first()
            is not None
        )

    def _mark_event_processed(self, event_id: str, event_type: str) -> None:
        """Mark a Stripe event as processed."""
        event = StripeEvent(id=event_id, type=event_type)
        self.db.add(event)
        self.db.commit()

    # --- Trial Expiration Check ---

    def check_expired_trials(self) -> int:
        """Check and expire trials that have passed their end date.

        Returns the number of subscriptions expired.
        Should be run periodically via a background task.
        """
        now = datetime.utcnow()
        expired = (
            self.db.query(Subscription)
            .filter(
                Subscription.status == "trial",
                Subscription.trial_ends_at < now,
            )
            .all()
        )

        for sub in expired:
            sub.status = "expired"
            logger.info(f"Expired trial for tenant {sub.tenant_id}")

        if expired:
            self.db.commit()

        return len(expired)
