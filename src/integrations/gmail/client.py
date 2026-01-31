"""Gmail API client wrapper."""

import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.core.config import settings


class GmailClient:
    """Wrapper for Gmail API operations.

    Handles:
    - Fetching messages with thread context
    - Sending replies
    - Archiving messages
    - Managing labels
    - Setting up push notifications
    """

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        token_expires_at: datetime | None = None,
        user_email: str | None = None,
    ):
        """Initialize Gmail client with user credentials.

        Args:
            access_token: OAuth2 access token
            refresh_token: OAuth2 refresh token
            token_expires_at: Token expiration time
            user_email: User's email address
        """
        self.credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=self.SCOPES,
        )
        self.user_email = user_email
        self._service = None

    @property
    def service(self):
        """Get or create Gmail API service."""
        if self._service is None:
            self._service = build("gmail", "v1", credentials=self.credentials)
        return self._service

    async def get_message(
        self,
        message_id: str,
        include_thread: bool = True,
        thread_limit: int = 5,
    ) -> dict:
        """Fetch a complete email message.

        Args:
            message_id: Gmail message ID
            include_thread: Whether to include thread context
            thread_limit: Max number of previous messages to include

        Returns:
            Parsed email data
        """
        # Get the message
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        # Parse headers
        headers = {h["name"].lower(): h["value"] for h in message["payload"]["headers"]}

        # Parse body
        body = self._extract_body(message["payload"])

        # Get thread context if requested
        thread_messages = []
        if include_thread:
            thread_id = message.get("threadId")
            if thread_id:
                thread_messages = await self._get_thread_context(
                    thread_id, message_id, thread_limit
                )

        # Parse attachments (metadata only)
        attachments = self._extract_attachments(message["payload"])

        return {
            "message_id": message_id,
            "thread_id": message.get("threadId"),
            "sender": headers.get("from", ""),
            "sender_name": self._parse_sender_name(headers.get("from", "")),
            "subject": headers.get("subject", ""),
            "body": body,
            "snippet": message.get("snippet", ""),
            "received_at": headers.get("date", ""),
            "thread_messages": thread_messages,
            "attachments": attachments,
            "labels": message.get("labelIds", []),
        }

    async def send_reply(
        self,
        message_id: str,
        body: str,
        thread_id: str | None = None,
    ) -> dict:
        """Send a reply to an email.

        Args:
            message_id: Original message ID to reply to
            body: Reply body text
            thread_id: Thread ID (optional, fetched if not provided)

        Returns:
            Sent message data
        """
        # Get original message for headers
        original = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="metadata")
            .execute()
        )

        headers = {h["name"].lower(): h["value"] for h in original["payload"]["headers"]}
        thread_id = thread_id or original.get("threadId")

        # Create reply
        reply_to = headers.get("reply-to") or headers.get("from")
        subject = headers.get("subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        message = MIMEText(body)
        message["to"] = reply_to
        message["subject"] = subject
        message["In-Reply-To"] = headers.get("message-id")
        message["References"] = headers.get("message-id")

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        sent = (
            self.service.users()
            .messages()
            .send(userId="me", body={"raw": raw, "threadId": thread_id})
            .execute()
        )

        return sent

    async def archive(self, message_id: str) -> None:
        """Archive a message by removing INBOX label.

        Args:
            message_id: Message ID to archive
        """
        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["INBOX"]},
        ).execute()

    async def add_label(self, message_id: str, label_name: str) -> None:
        """Add a label to a message.

        Creates the label if it doesn't exist.

        Args:
            message_id: Message ID to label
            label_name: Label name to add
        """
        # Get or create label
        label_id = await self._get_or_create_label(label_name)

        # Add label to message
        self.service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id]},
        ).execute()

    async def setup_watch(self, topic_name: str | None = None) -> dict:
        """Set up Gmail push notifications.

        Args:
            topic_name: Pub/Sub topic name (defaults to settings)

        Returns:
            Watch response with historyId and expiration
        """
        topic = topic_name or settings.gmail_pubsub_topic

        result = (
            self.service.users()
            .watch(
                userId="me",
                body={
                    "topicName": topic,
                    "labelIds": ["INBOX"],
                    "labelFilterBehavior": "INCLUDE",
                },
            )
            .execute()
        )

        return {
            "history_id": result.get("historyId"),
            "expiration": datetime.fromtimestamp(int(result.get("expiration", 0)) / 1000),
        }

    async def stop_watch(self) -> None:
        """Stop Gmail push notifications."""
        self.service.users().stop(userId="me").execute()

    async def get_history(
        self,
        start_history_id: str,
        history_types: list[str] | None = None,
    ) -> list[dict]:
        """Get history of mailbox changes.

        Args:
            start_history_id: History ID to start from
            history_types: Types to include (default: messageAdded)

        Returns:
            List of history events
        """
        history_types = history_types or ["messageAdded"]

        try:
            response = (
                self.service.users()
                .history()
                .list(
                    userId="me",
                    startHistoryId=start_history_id,
                    historyTypes=history_types,
                )
                .execute()
            )

            return response.get("history", [])

        except HttpError as e:
            if e.resp.status == 404:
                # History ID too old, need full sync
                return []
            raise

    # Private helpers

    def _extract_body(self, payload: dict) -> str:
        """Extract text body from message payload."""
        if "body" in payload and payload["body"].get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    if part["body"].get("data"):
                        return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                            "utf-8"
                        )
                elif part["mimeType"].startswith("multipart/"):
                    body = self._extract_body(part)
                    if body:
                        return body

        return ""

    def _extract_attachments(self, payload: dict) -> list[dict]:
        """Extract attachment metadata from message payload."""
        attachments = []

        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("filename"):
                    attachments.append(
                        {
                            "filename": part["filename"],
                            "mimeType": part.get("mimeType", "application/octet-stream"),
                            "size": part["body"].get("size", 0),
                        }
                    )
                elif part["mimeType"].startswith("multipart/"):
                    attachments.extend(self._extract_attachments(part))

        return attachments

    def _parse_sender_name(self, from_header: str) -> str | None:
        """Extract sender name from From header."""
        if "<" in from_header:
            return from_header.split("<")[0].strip().strip('"')
        return None

    async def _get_thread_context(
        self,
        thread_id: str,
        current_message_id: str,
        limit: int,
    ) -> list[dict]:
        """Get previous messages in thread."""
        thread = (
            self.service.users()
            .threads()
            .get(userId="me", id=thread_id, format="metadata")
            .execute()
        )

        messages = []
        for msg in thread.get("messages", [])[-(limit + 1) :]:
            if msg["id"] == current_message_id:
                continue

            headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
            messages.append(
                {
                    "message_id": msg["id"],
                    "sender": headers.get("from", ""),
                    "subject": headers.get("subject", ""),
                    "snippet": msg.get("snippet", ""),
                    "date": headers.get("date", ""),
                }
            )

        return messages[-limit:]

    async def _get_or_create_label(self, label_name: str) -> str:
        """Get label ID, creating it if necessary."""
        # List existing labels
        labels = self.service.users().labels().list(userId="me").execute()

        for label in labels.get("labels", []):
            if label["name"] == label_name:
                return label["id"]

        # Create new label
        new_label = (
            self.service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )

        return new_label["id"]
