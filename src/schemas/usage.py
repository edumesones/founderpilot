"""Pydantic schemas for usage tracking API."""
from datetime import datetime
from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel, Field


class AgentUsage(BaseModel):
    """Usage statistics for a single agent."""

    count: int = Field(..., description="Current usage count for the period")
    limit: int = Field(..., description="Plan limit for this agent")
    percentage: int = Field(..., ge=0, description="Usage percentage (0-100+)")
    overage: int = Field(..., ge=0, description="Amount over limit (0 if under)")
    overage_cost_cents: int = Field(..., ge=0, description="Estimated overage cost in cents")

    class Config:
        json_schema_extra = {
            "example": {
                "count": 425,
                "limit": 500,
                "percentage": 85,
                "overage": 0,
                "overage_cost_cents": 0,
            }
        }


class UsageAlert(BaseModel):
    """Alert for high usage or overage."""

    agent: str = Field(..., description="Agent type (inbox/invoice/meeting)")
    message: str = Field(..., description="User-friendly alert message")
    level: str = Field(..., description="Alert level: 'warning' or 'error'")

    class Config:
        json_schema_extra = {
            "example": {
                "agent": "inbox",
                "message": "You've used 85% of your email quota this month",
                "level": "warning",
            }
        }


class PlanInfo(BaseModel):
    """Plan information with limits."""

    name: str = Field(..., description="Plan name")
    limits: Dict[str, int] = Field(..., description="Usage limits by agent")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Bundle",
                "limits": {
                    "emails_per_month": 500,
                    "invoices_per_month": 50,
                    "meetings_per_month": 30,
                },
            }
        }


class UsageStatsResponse(BaseModel):
    """Complete usage statistics response."""

    tenant_id: UUID = Field(..., description="Tenant UUID")
    period_start: datetime = Field(..., description="Billing period start")
    period_end: datetime = Field(..., description="Billing period end")
    plan: PlanInfo = Field(..., description="Current plan information")
    usage: Dict[str, AgentUsage] = Field(..., description="Usage by agent type")
    total_overage_cost_cents: int = Field(..., ge=0, description="Total overage cost in cents")
    alerts: List[UsageAlert] = Field(default_factory=list, description="Usage alerts")

    class Config:
        json_schema_extra = {
            "example": {
                "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                "period_start": "2024-02-01T00:00:00Z",
                "period_end": "2024-03-01T00:00:00Z",
                "plan": {
                    "name": "Bundle",
                    "limits": {
                        "emails_per_month": 500,
                        "invoices_per_month": 50,
                        "meetings_per_month": 30,
                    },
                },
                "usage": {
                    "inbox": {
                        "count": 425,
                        "limit": 500,
                        "percentage": 85,
                        "overage": 0,
                        "overage_cost_cents": 0,
                    },
                    "invoice": {
                        "count": 52,
                        "limit": 50,
                        "percentage": 104,
                        "overage": 2,
                        "overage_cost_cents": 20,
                    },
                    "meeting": {
                        "count": 15,
                        "limit": 30,
                        "percentage": 50,
                        "overage": 0,
                        "overage_cost_cents": 0,
                    },
                },
                "total_overage_cost_cents": 20,
                "alerts": [
                    {
                        "agent": "inbox",
                        "message": "You've used 85% of your email quota this month",
                        "level": "warning",
                    },
                    {
                        "agent": "invoice",
                        "message": "You've exceeded your invoice quota. Extra charges: $0.20",
                        "level": "error",
                    },
                ],
            }
        }
