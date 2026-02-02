"""
Agent audit logging service for tracking AI agent actions.

This service handles creating and querying audit logs for InboxPilot,
InvoicePilot, and MeetingPilot actions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_audit_log import AgentAuditLog, AgentType


class AgentAuditService:
    """
    Service for creating and querying agent audit logs.

    All AI agent actions should be logged through this service
    to maintain transparency and enable the audit dashboard.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the agent audit service.

        Args:
            db: Database session
        """
        self.db = db

    async def log_action(
        self,
        user_id: UUID,
        agent_type: str,
        action: str,
        input_summary: Optional[str] = None,
        output_summary: Optional[str] = None,
        decision: Optional[str] = None,
        confidence: Optional[float] = None,
        escalated: bool = False,
        authorized_by: Optional[str] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[UUID] = None,
    ) -> AgentAuditLog:
        """
        Create a new agent audit log entry.

        Args:
            user_id: The user who owns this workflow
            agent_type: Type of agent (inbox_pilot, invoice_pilot, meeting_pilot)
            action: Action performed
            input_summary: Truncated input (max 2000 chars recommended)
            output_summary: Truncated output (max 2000 chars recommended)
            decision: Human-readable decision made
            confidence: Confidence level (0.0 to 1.0)
            escalated: Whether action was escalated for human approval
            authorized_by: Who authorized ('agent' or user_id)
            trace_id: Langfuse trace ID
            metadata: Full input/output and extra context
            workflow_id: LangGraph workflow run ID

        Returns:
            The created AgentAuditLog entry
        """
        # Truncate summaries if needed
        if input_summary and len(input_summary) > 2000:
            input_summary = input_summary[:1997] + "..."
        if output_summary and len(output_summary) > 2000:
            output_summary = output_summary[:1997] + "..."

        audit_log = AgentAuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            workflow_id=workflow_id,
            agent_type=agent_type,
            action=action,
            input_summary=input_summary,
            output_summary=output_summary,
            decision=decision,
            confidence=confidence,
            escalated=escalated,
            authorized_by=authorized_by or "agent",
            trace_id=trace_id,
            metadata=metadata or {},
            rolled_back=False,
        )

        self.db.add(audit_log)
        await self.db.flush()

        return audit_log

    async def get_logs(
        self,
        user_id: UUID,
        limit: int = 50,
        cursor: Optional[UUID] = None,
        agent_type: Optional[str] = None,
        escalated: Optional[bool] = None,
        min_confidence: Optional[float] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> tuple[List[AgentAuditLog], Optional[UUID], bool]:
        """
        Get agent audit logs with filters and pagination.

        Args:
            user_id: The user's ID
            limit: Maximum number of logs to return (max 100)
            cursor: Pagination cursor (last entry ID from previous page)
            agent_type: Filter by agent type
            escalated: Filter by escalation status
            min_confidence: Filter by minimum confidence level
            from_date: Start date filter
            to_date: End date filter
            search: Full-text search query

        Returns:
            Tuple of (logs list, next_cursor, has_more)
        """
        # Enforce max limit
        limit = min(limit, 100)

        # Build base query
        query = (
            select(AgentAuditLog)
            .where(AgentAuditLog.user_id == user_id)
            .order_by(desc(AgentAuditLog.timestamp), desc(AgentAuditLog.id))
        )

        # Apply cursor pagination
        if cursor:
            cursor_entry = await self.db.get(AgentAuditLog, cursor)
            if cursor_entry:
                query = query.where(
                    or_(
                        AgentAuditLog.timestamp < cursor_entry.timestamp,
                        and_(
                            AgentAuditLog.timestamp == cursor_entry.timestamp,
                            AgentAuditLog.id < cursor_entry.id,
                        ),
                    )
                )

        # Apply filters
        if agent_type:
            query = query.where(AgentAuditLog.agent_type == agent_type)

        if escalated is not None:
            query = query.where(AgentAuditLog.escalated == escalated)

        if min_confidence is not None:
            query = query.where(AgentAuditLog.confidence >= min_confidence)

        if from_date:
            query = query.where(AgentAuditLog.timestamp >= from_date)

        if to_date:
            query = query.where(AgentAuditLog.timestamp <= to_date)

        if search:
            # Full-text search using PostgreSQL tsvector
            search_query = func.to_tsquery("english", search)
            query = query.where(
                func.to_tsvector(
                    "english",
                    func.coalesce(AgentAuditLog.input_summary, "")
                    + " "
                    + func.coalesce(AgentAuditLog.output_summary, ""),
                ).op("@@")(search_query)
            )

        # Fetch limit + 1 to check if there are more results
        result = await self.db.execute(query.limit(limit + 1))
        logs = list(result.scalars().all())

        # Determine if there are more results
        has_more = len(logs) > limit
        if has_more:
            logs = logs[:limit]

        # Get next cursor
        next_cursor = logs[-1].id if logs and has_more else None

        return logs, next_cursor, has_more

    async def get_log_by_id(
        self, log_id: UUID, user_id: UUID
    ) -> Optional[AgentAuditLog]:
        """
        Get a specific audit log entry by ID.

        Args:
            log_id: The log entry ID
            user_id: The user's ID (for authorization)

        Returns:
            AgentAuditLog entry or None if not found or not authorized
        """
        query = select(AgentAuditLog).where(
            and_(
                AgentAuditLog.id == log_id,
                AgentAuditLog.user_id == user_id,
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def mark_rolled_back(
        self, log_id: UUID, user_id: UUID
    ) -> Optional[AgentAuditLog]:
        """
        Mark an audit log entry as rolled back.

        Args:
            log_id: The log entry ID
            user_id: The user's ID (for authorization)

        Returns:
            Updated AgentAuditLog entry or None if not found
        """
        log = await self.get_log_by_id(log_id, user_id)
        if log:
            log.rolled_back = True
            log.updated_at = datetime.now(timezone.utc)
            await self.db.flush()

        return log

    async def get_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get statistics about agent actions for a user.

        Args:
            user_id: The user's ID

        Returns:
            Dict with statistics (total_actions, by_agent, escalation_rate, etc.)
        """
        # Total actions
        total_query = select(func.count(AgentAuditLog.id)).where(
            AgentAuditLog.user_id == user_id
        )
        total_result = await self.db.execute(total_query)
        total_actions = total_result.scalar_one()

        # Actions by agent type
        by_agent_query = (
            select(AgentAuditLog.agent_type, func.count(AgentAuditLog.id))
            .where(AgentAuditLog.user_id == user_id)
            .group_by(AgentAuditLog.agent_type)
        )
        by_agent_result = await self.db.execute(by_agent_query)
        by_agent = {row[0]: row[1] for row in by_agent_result.all()}

        # Escalation count
        escalated_query = select(func.count(AgentAuditLog.id)).where(
            and_(
                AgentAuditLog.user_id == user_id,
                AgentAuditLog.escalated == True,  # noqa: E712
            )
        )
        escalated_result = await self.db.execute(escalated_query)
        escalated_count = escalated_result.scalar_one()

        # Average confidence
        avg_confidence_query = select(func.avg(AgentAuditLog.confidence)).where(
            and_(
                AgentAuditLog.user_id == user_id,
                AgentAuditLog.confidence.isnot(None),
            )
        )
        avg_confidence_result = await self.db.execute(avg_confidence_query)
        avg_confidence = avg_confidence_result.scalar_one()

        return {
            "total_actions": total_actions,
            "by_agent": by_agent,
            "escalated_count": escalated_count,
            "escalation_rate": (
                escalated_count / total_actions if total_actions > 0 else 0
            ),
            "average_confidence": float(avg_confidence) if avg_confidence else None,
        }
