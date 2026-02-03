"""Usage service for retrieving usage statistics and calculating overage."""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
import logging

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from src.models.usage import UsageCounter
from src.models.billing import Subscription, Plan
from src.schemas.usage import (
    AgentUsage,
    UsageAlert,
    PlanInfo,
    UsageStatsResponse,
)

logger = logging.getLogger(__name__)


class UsageService:
    """
    Service for retrieving usage statistics, calculating overage costs, and generating alerts.
    """

    # Overage pricing per agent (in cents)
    OVERAGE_PRICING = {
        "inbox": 2,      # $0.02 per email
        "invoice": 10,   # $0.10 per invoice
        "meeting": 15,   # $0.15 per meeting
    }

    # Agent limit keys in plan.limits JSONB
    LIMIT_KEY_MAP = {
        "inbox": "emails_per_month",
        "invoice": "invoices_per_month",
        "meeting": "meetings_per_month",
    }

    def __init__(self, db: Session):
        self.db = db

    def get_usage_stats(self, tenant_id: UUID) -> UsageStatsResponse:
        """
        Get comprehensive usage statistics for a tenant's current billing period.

        Args:
            tenant_id: Tenant UUID

        Returns:
            UsageStatsResponse: Complete usage statistics with overage and alerts

        Raises:
            HTTPException: If tenant has no active subscription (404)
        """
        # Get subscription with plan
        subscription = self._get_active_subscription(tenant_id)

        if not subscription.plan:
            logger.error(
                "Subscription has no plan",
                extra={"tenant_id": str(tenant_id), "subscription_id": str(subscription.id)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Subscription configuration error: no plan assigned",
            )

        plan = subscription.plan

        # Get all counters for current billing period
        counters = (
            self.db.query(UsageCounter)
            .filter(
                UsageCounter.tenant_id == tenant_id,
                UsageCounter.period_start == subscription.current_period_start,
            )
            .all()
        )

        # Build usage dictionary for all agents
        usage_data = {}
        total_overage_cost = 0

        for agent in ["inbox", "invoice", "meeting"]:
            # Find counter for this agent
            counter = next((c for c in counters if c.agent == agent), None)
            count = counter.count if counter else 0

            # Get limit from plan
            limit = self._get_agent_limit(plan, agent)

            # Calculate metrics
            percentage = int((count / limit) * 100) if limit > 0 else 0
            overage = max(0, count - limit)
            overage_cost = self._calculate_overage_cost(agent, overage)
            total_overage_cost += overage_cost

            usage_data[agent] = AgentUsage(
                count=count,
                limit=limit,
                percentage=percentage,
                overage=overage,
                overage_cost_cents=overage_cost,
            )

        # Generate alerts based on usage
        alerts = self._generate_alerts(usage_data)

        # Build plan info
        plan_info = PlanInfo(
            name=plan.name,
            limits=plan.limits,
        )

        logger.info(
            "Retrieved usage stats",
            extra={
                "tenant_id": str(tenant_id),
                "total_overage_cost_cents": total_overage_cost,
                "alert_count": len(alerts),
            },
        )

        return UsageStatsResponse(
            tenant_id=tenant_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            plan=plan_info,
            usage=usage_data,
            total_overage_cost_cents=total_overage_cost,
            alerts=alerts,
        )

    def _get_active_subscription(self, tenant_id: UUID) -> Subscription:
        """
        Get active subscription for tenant.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Subscription: Active subscription

        Raises:
            HTTPException: If no active subscription found (404)
        """
        subscription = (
            self.db.query(Subscription)
            .filter(Subscription.tenant_id == tenant_id)
            .first()
        )

        if not subscription:
            logger.warning(
                "No subscription found for tenant",
                extra={"tenant_id": str(tenant_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found for this tenant",
            )

        if not subscription.is_active:
            logger.warning(
                "Subscription is not active",
                extra={
                    "tenant_id": str(tenant_id),
                    "subscription_status": subscription.status,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Subscription is not active (status: {subscription.status})",
            )

        return subscription

    def _get_agent_limit(self, plan: Plan, agent: str) -> int:
        """
        Extract usage limit for an agent from plan.limits JSONB.

        Args:
            plan: Plan object
            agent: Agent type ('inbox', 'invoice', 'meeting')

        Returns:
            int: Usage limit for the agent (0 if not found)
        """
        limit_key = self.LIMIT_KEY_MAP.get(agent)
        if not limit_key:
            logger.warning(
                "Unknown agent type",
                extra={"agent": agent},
            )
            return 0

        limit = plan.limits.get(limit_key, 0)

        # Handle trial users with generous limits or no limits
        if limit == 0 or limit is None:
            logger.debug(
                "Plan has no limit for agent (trial or unlimited)",
                extra={"plan_id": plan.id, "agent": agent},
            )
            # Return a very high limit for trial users (effectively unlimited)
            return 999999

        return limit

    def _calculate_overage_cost(self, agent: str, overage: int) -> int:
        """
        Calculate overage cost in cents.

        Args:
            agent: Agent type
            overage: Number of units over the limit

        Returns:
            int: Cost in cents
        """
        price_per_unit = self.OVERAGE_PRICING.get(agent, 0)
        return overage * price_per_unit

    def _generate_alerts(self, usage_data: Dict[str, AgentUsage]) -> List[UsageAlert]:
        """
        Generate alerts for high usage or overage.

        Args:
            usage_data: Dictionary of agent usage data

        Returns:
            List[UsageAlert]: List of alerts (empty if no alerts needed)
        """
        alerts = []

        for agent, usage in usage_data.items():
            if usage.percentage >= 100:
                # Overage alert (error level)
                alerts.append(
                    UsageAlert(
                        agent=agent,
                        message=f"You've exceeded your {agent} quota. Extra charges: ${usage.overage_cost_cents / 100:.2f}",
                        level="error",
                    )
                )
            elif usage.percentage >= 80:
                # High usage warning
                alerts.append(
                    UsageAlert(
                        agent=agent,
                        message=f"You've used {usage.percentage}% of your {agent} quota this month",
                        level="warning",
                    )
                )

        return alerts

    def get_usage_for_agent(
        self, tenant_id: UUID, agent: str
    ) -> Optional[AgentUsage]:
        """
        Get usage statistics for a specific agent.

        Args:
            tenant_id: Tenant UUID
            agent: Agent type

        Returns:
            AgentUsage: Usage stats for the agent, or None if no subscription
        """
        try:
            stats = self.get_usage_stats(tenant_id)
            return stats.usage.get(agent)
        except HTTPException:
            return None
