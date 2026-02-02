"""
Gmail service for InvoicePilot.

Handles:
- Scanning inbox for sent emails with invoice attachments
- Sending reminder emails
- Extracting PDF attachments
- Tracking message IDs
"""

import base64
import io
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import IntegrationNotFoundError
from src.services.gmail_oauth import GmailOAuthService
from src.services.token_encryption import TokenEncryptionService


class InvoiceEmail:
    """Represents an email with potential invoice attachment."""

    def __init__(
        self,
        message_id: str,
        thread_id: str,
        subject: str,
        to: List[str],
        cc: Optional[List[str]],
        date: datetime,
        snippet: str,
        has_attachments: bool,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ):
        self.message_id = message_id
        self.thread_id = thread_id
        self.subject = subject
        self.to = to
        self.cc = cc or []
        self.date = date
        self.snippet = snippet
        self.has_attachments = has_attachments
        self.attachments = attachments or []


class InvoicePilotGmailService:
    """
    Gmail service for InvoicePilot operations.

    Provides methods to:
    - Scan sent folder for emails with PDF attachments
    - Extract PDF attachments from emails
    - Send reminder emails to clients
    - Track sent message IDs
    """

    GMAIL_API_BASE = "https://www.googleapis.com/gmail/v1"

    def __init__(
        self,
        db: AsyncSession,
        user_id: UUID,
        gmail_oauth_service: Optional[GmailOAuthService] = None,
    ):
        """
        Initialize the Gmail service for InvoicePilot.

        Args:
            db: Database session
            user_id: User ID for Gmail integration
            gmail_oauth_service: Gmail OAuth service (optional, will create if not provided)
        """
        self.db = db
        self.user_id = user_id
        self.gmail_oauth = gmail_oauth_service or GmailOAuthService(
            db=db,
            redis_client=None,  # Not needed for API calls
            encryption_service=TokenEncryptionService(),
        )

    async def scan_sent_folder(
        self,
        days_back: int = 30,
        max_results: int = 100,
        only_with_attachments: bool = True,
    ) -> List[InvoiceEmail]:
        """
        Scan Gmail sent folder for emails with attachments.

        Args:
            days_back: Number of days to look back (default 30)
            max_results: Maximum number of emails to retrieve
            only_with_attachments: Only return emails with PDF attachments

        Returns:
            List of InvoiceEmail objects
        """
        access_token = await self.gmail_oauth.get_access_token(self.user_id)

        # Build query
        query_parts = ["in:sent"]

        if only_with_attachments:
            query_parts.append("has:attachment")
            query_parts.append("filename:pdf")

        # Date filter
        after_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y/%m/%d")
        query_parts.append(f"after:{after_date}")

        query = " ".join(query_parts)

        # Call Gmail API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GMAIL_API_BASE}/users/me/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": query,
                    "maxResults": max_results,
                },
            )

            if response.status_code != 200:
                raise Exception(f"Gmail API error: {response.text}")

            data = response.json()
            message_ids = [msg["id"] for msg in data.get("messages", [])]

        # Fetch full message details
        emails = []
        for msg_id in message_ids:
            email = await self._fetch_message_details(access_token, msg_id)
            if email:
                emails.append(email)

        return emails

    async def get_attachment(
        self,
        message_id: str,
        attachment_id: str,
    ) -> bytes:
        """
        Download a specific attachment from a Gmail message.

        Args:
            message_id: Gmail message ID
            attachment_id: Attachment ID from message

        Returns:
            Attachment data as bytes
        """
        access_token = await self.gmail_oauth.get_access_token(self.user_id)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GMAIL_API_BASE}/users/me/messages/{message_id}/attachments/{attachment_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                raise Exception(f"Gmail API error: {response.text}")

            data = response.json()
            attachment_data = data.get("data", "")

            # Decode base64url
            return base64.urlsafe_b64decode(attachment_data)

    async def send_reminder_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        reply_to_message_id: Optional[str] = None,
        reply_to_thread_id: Optional[str] = None,
    ) -> str:
        """
        Send a reminder email to a client.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (HTML supported)
            cc: CC recipients
            reply_to_message_id: Original message ID to reply to
            reply_to_thread_id: Thread ID to continue conversation

        Returns:
            Sent message ID
        """
        access_token = await self.gmail_oauth.get_access_token(self.user_id)

        # Create MIME message
        message = MIMEMultipart()
        message["To"] = to
        message["Subject"] = subject

        if cc:
            message["Cc"] = ", ".join(cc)

        # Add thread headers if replying
        if reply_to_message_id:
            message["In-Reply-To"] = reply_to_message_id
            message["References"] = reply_to_message_id

        # Add body
        message.attach(MIMEText(body, "html"))

        # Encode message
        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        # Prepare request body
        request_body = {"raw": raw_message}

        if reply_to_thread_id:
            request_body["threadId"] = reply_to_thread_id

        # Send via Gmail API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.GMAIL_API_BASE}/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json=request_body,
            )

            if response.status_code != 200:
                raise Exception(f"Gmail API error: {response.text}")

            data = response.json()
            return data["id"]

    async def get_message_details(
        self,
        message_id: str,
    ) -> Optional[InvoiceEmail]:
        """
        Get details for a specific message.

        Args:
            message_id: Gmail message ID

        Returns:
            InvoiceEmail object or None if not found
        """
        access_token = await self.gmail_oauth.get_access_token(self.user_id)
        return await self._fetch_message_details(access_token, message_id)

    async def check_bounce_status(
        self,
        message_id: str,
    ) -> Dict[str, Any]:
        """
        Check if a sent email bounced or had delivery issues.

        Args:
            message_id: Gmail message ID

        Returns:
            Dictionary with bounce status information
        """
        access_token = await self.gmail_oauth.get_access_token(self.user_id)

        # Get the thread for this message
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GMAIL_API_BASE}/users/me/messages/{message_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "full"},
            )

            if response.status_code != 200:
                return {"bounced": False, "error": None}

            data = response.json()
            thread_id = data.get("threadId")

            # Check for bounce messages in the same thread
            thread_response = await client.get(
                f"{self.GMAIL_API_BASE}/users/me/threads/{thread_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "metadata"},
            )

            if thread_response.status_code != 200:
                return {"bounced": False, "error": None}

            thread_data = thread_response.json()
            messages = thread_data.get("messages", [])

            # Look for bounce indicators
            for msg in messages:
                if msg["id"] == message_id:
                    continue

                # Check for delivery failure headers
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

                from_header = headers.get("From", "").lower()
                subject = headers.get("Subject", "").lower()

                # Common bounce indicators
                bounce_indicators = [
                    "mailer-daemon",
                    "postmaster",
                    "delivery failed",
                    "undelivered",
                    "bounce",
                    "returned mail",
                ]

                if any(indicator in from_header or indicator in subject for indicator in bounce_indicators):
                    return {
                        "bounced": True,
                        "bounce_message_id": msg["id"],
                        "subject": subject,
                    }

            return {"bounced": False, "error": None}

    # =========================================================================
    # Private methods
    # =========================================================================

    async def _fetch_message_details(
        self,
        access_token: str,
        message_id: str,
    ) -> Optional[InvoiceEmail]:
        """Fetch full message details including attachments."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GMAIL_API_BASE}/users/me/messages/{message_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"format": "full"},
            )

            if response.status_code != 200:
                return None

            data = response.json()

            # Parse headers
            headers = {
                h["name"]: h["value"]
                for h in data.get("payload", {}).get("headers", [])
            }

            # Extract basic info
            subject = headers.get("Subject", "")
            to = self._parse_email_list(headers.get("To", ""))
            cc = self._parse_email_list(headers.get("Cc", ""))
            date_str = headers.get("Date", "")

            # Parse date
            try:
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_str)
            except Exception:
                date = datetime.now(timezone.utc)

            # Extract attachments
            attachments = []
            payload = data.get("payload", {})
            self._extract_attachments(payload, attachments)

            # Check if has PDF attachments
            has_pdf = any(att.get("filename", "").lower().endswith(".pdf") for att in attachments)

            return InvoiceEmail(
                message_id=message_id,
                thread_id=data.get("threadId", ""),
                subject=subject,
                to=to,
                cc=cc,
                date=date,
                snippet=data.get("snippet", ""),
                has_attachments=len(attachments) > 0,
                attachments=attachments if has_pdf else [],
            )

    def _extract_attachments(
        self,
        payload: Dict[str, Any],
        attachments: List[Dict[str, Any]],
    ) -> None:
        """Recursively extract attachments from message payload."""
        # Check if this part is an attachment
        if "body" in payload and "attachmentId" in payload["body"]:
            filename = payload.get("filename", "")
            mime_type = payload.get("mimeType", "")

            if filename:  # Only include named attachments
                attachments.append({
                    "filename": filename,
                    "mimeType": mime_type,
                    "attachmentId": payload["body"]["attachmentId"],
                    "size": payload["body"].get("size", 0),
                })

        # Recursively check parts
        for part in payload.get("parts", []):
            self._extract_attachments(part, attachments)

    def _parse_email_list(self, email_str: str) -> List[str]:
        """Parse comma-separated email list."""
        if not email_str:
            return []

        # Simple parsing - could be enhanced with email.utils.getaddresses
        emails = [e.strip() for e in email_str.split(",")]

        # Extract email from "Name <email>" format
        cleaned = []
        for email in emails:
            if "<" in email and ">" in email:
                email = email[email.index("<") + 1:email.index(">")]
            cleaned.append(email.strip())

        return cleaned
