"""InboxPilot service - business logic layer."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.inbox_pilot.agent import InboxPilotAgent
from src.core.llm import LLMRouter
from src.integrations.gmail.client import GmailClient
from src.integrations.slack.notifier import SlackNotifier
from src.models.inbox_pilot.agent_config import InboxPilotConfig
from src.models.inbox_pilot.email_record import EmailRecord
from src.models.user import User
from src.schemas.inbox_pilot.config import InboxPilotConfigUpdate


class InboxPilotService:
    """Business logic for InboxPilot operations."""

    def __init__(
        self,
        db: AsyncSession,
        llm_router: LLMRouter | None = None,
    ):
        """Initialize service.

        Args:
            db: Database session
            llm_router: LLM provider router (created if not provided)
        """
        self.db = db
        self.llm = llm_router or LLMRouter()

    async def process_email(
        self,
        user_id: UUID,
        message_id: str,
    ) -> EmailRecord:
        """Process a new email through the InboxPilot agent.

        Args:
            user_id: User ID
            message_id: Gmail message ID

        Returns:
            EmailRecord with processing results
        """
        # Check idempotency
        existing = await self._get_email_by_message_id(message_id)
        if existing:
            return existing

        # Get user and config
        user = await self._get_user(user_id)
        config = await self.get_or_create_config(user_id)

        # Check if agent is active
        if not config.is_active:
            raise ValueError("InboxPilot is paused for this user")

        # Create Gmail client
        gmail_client = GmailClient(
            access_token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_expires_at=user.google_token_expires_at,
            user_email=user.email,
        )

        # Create Slack notifier
        slack_notifier = SlackNotifier()

        # Create checkpointer
        # TODO: Set up PostgresSaver with connection pool
        checkpointer = None

        # Create agent
        agent = InboxPilotAgent(
            gmail_client=gmail_client,
            slack_notifier=slack_notifier,
            llm_router=self.llm,
            user_config=config,
            checkpointer=checkpointer,
        )

        # Run the agent
        result = await agent.run(message_id)

        # Create email record
        record = EmailRecord(
            user_id=user_id,
            gmail_message_id=message_id,
            thread_id=result.get("email", {}).get("thread_id", ""),
            sender=result.get("email", {}).get("sender", ""),
            sender_name=result.get("email", {}).get("sender_name"),
            subject=result.get("email", {}).get("subject", ""),
            snippet=result.get("email", {}).get("snippet"),
            received_at=datetime.fromisoformat(
                result.get("email", {}).get("received_at", datetime.utcnow().isoformat())
            ),
            category=result.get("classification", {}).get("category", "unknown"),
            confidence=result.get("classification", {}).get("confidence", 0),
            classification_reasoning=result.get("classification", {}).get("reasoning"),
            status="escalated" if result.get("needs_human_review") else "completed",
            draft_content=result.get("draft", {}).get("content") if result.get("draft") else None,
            draft_confidence=result.get("draft", {}).get("confidence") if result.get("draft") else None,
            draft_tone=result.get("draft", {}).get("tone") if result.get("draft") else None,
            action_taken=result.get("action_taken"),
            processed_at=datetime.utcnow(),
            escalated_at=datetime.utcnow() if result.get("needs_human_review") else None,
            completed_at=datetime.utcnow() if not result.get("needs_human_review") else None,
            trace_id=result.get("trace_id"),
        )

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        # Update stats
        config.total_emails_processed += 1
        if result.get("needs_human_review"):
            config.total_escalations += 1
        await self.db.commit()

        return record

    async def handle_slack_action(
        self,
        message_id: str,
        action: Literal["approve", "reject", "edit", "archive"],
        edited_content: str | None = None,
    ) -> EmailRecord:
        """Handle Slack action callback.

        Args:
            message_id: Gmail message ID
            action: User's action
            edited_content: Edited draft content (for edit action)

        Returns:
            Updated EmailRecord
        """
        record = await self._get_email_by_message_id(message_id)
        if not record:
            raise ValueError(f"Email record not found: {message_id}")

        user = await self._get_user(record.user_id)
        config = await self.get_or_create_config(record.user_id)

        # Create Gmail client
        gmail_client = GmailClient(
            access_token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            user_email=user.email,
        )

        # Create agent to resume workflow
        # TODO: Set up proper checkpointer
        agent = InboxPilotAgent(
            gmail_client=gmail_client,
            slack_notifier=SlackNotifier(),
            llm_router=self.llm,
            user_config=config,
            checkpointer=None,
        )

        # Resume workflow with human decision
        result = await agent.resume(
            message_id=message_id,
            human_decision=action,
            edited_content=edited_content,
        )

        # Update record
        record.human_decision = action
        record.human_edited_content = edited_content
        record.action_taken = result.get("action_taken")
        record.status = "completed"
        record.completed_at = datetime.utcnow()

        if result.get("action_taken") == "sent":
            config.total_drafts_sent += 1

        await self.db.commit()
        await self.db.refresh(record)

        return record

    async def get_or_create_config(self, user_id: UUID) -> InboxPilotConfig:
        """Get or create default config for user.

        Args:
            user_id: User ID

        Returns:
            InboxPilotConfig instance
        """
        stmt = select(InboxPilotConfig).where(InboxPilotConfig.user_id == user_id)
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            config = InboxPilotConfig(user_id=user_id)
            self.db.add(config)
            await self.db.commit()
            await self.db.refresh(config)

        return config

    async def update_config(
        self,
        user_id: UUID,
        updates: InboxPilotConfigUpdate,
    ) -> InboxPilotConfig:
        """Update user's config.

        Args:
            user_id: User ID
            updates: Config updates

        Returns:
            Updated config
        """
        config = await self.get_or_create_config(user_id)

        for field, value in updates.model_dump(exclude_unset=True).items():
            setattr(config, field, value)

        await self.db.commit()
        await self.db.refresh(config)

        return config

    async def list_emails(
        self,
        user_id: UUID,
        status: str | None = None,
        category: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[EmailRecord], int]:
        """List processed emails for user.

        Args:
            user_id: User ID
            status: Filter by status
            category: Filter by category
            page: Page number
            limit: Items per page

        Returns:
            Tuple of (records, total_count)
        """
        stmt = select(EmailRecord).where(EmailRecord.user_id == user_id)

        if status:
            stmt = stmt.where(EmailRecord.status == status)
        if category:
            stmt = stmt.where(EmailRecord.category == category)

        # Count total
        count_stmt = select(EmailRecord.id).where(EmailRecord.user_id == user_id)
        if status:
            count_stmt = count_stmt.where(EmailRecord.status == status)
        if category:
            count_stmt = count_stmt.where(EmailRecord.category == category)

        count_result = await self.db.execute(count_stmt)
        total = len(count_result.all())

        # Get page
        stmt = stmt.order_by(EmailRecord.received_at.desc())
        stmt = stmt.offset((page - 1) * limit).limit(limit)

        result = await self.db.execute(stmt)
        records = result.scalars().all()

        return list(records), total

    async def get_email(self, email_id: UUID) -> EmailRecord | None:
        """Get email record by ID.

        Args:
            email_id: Email record ID

        Returns:
            EmailRecord or None
        """
        stmt = select(EmailRecord).where(EmailRecord.id == email_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def setup_watch(self, user_id: UUID) -> dict:
        """Set up Gmail push notifications for user.

        Args:
            user_id: User ID

        Returns:
            Watch setup result
        """
        user = await self._get_user(user_id)

        gmail_client = GmailClient(
            access_token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            user_email=user.email,
        )

        result = await gmail_client.setup_watch()

        # Update user with new history_id
        user.gmail_history_id = result["history_id"]
        user.gmail_watch_expires_at = result["expiration"]
        await self.db.commit()

        return result

    async def stop_watch(self, user_id: UUID) -> None:
        """Stop Gmail push notifications.

        Args:
            user_id: User ID
        """
        user = await self._get_user(user_id)

        gmail_client = GmailClient(
            access_token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            user_email=user.email,
        )

        await gmail_client.stop_watch()

        user.gmail_history_id = None
        user.gmail_watch_expires_at = None
        await self.db.commit()

    # Private helpers

    async def _get_user(self, user_id: UUID) -> User:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User not found: {user_id}")

        return user

    async def _get_email_by_message_id(self, message_id: str) -> EmailRecord | None:
        """Get email record by Gmail message ID."""
        stmt = select(EmailRecord).where(EmailRecord.gmail_message_id == message_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
