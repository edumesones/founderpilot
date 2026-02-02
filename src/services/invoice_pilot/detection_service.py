"""Invoice detection service for scanning Gmail and extracting invoice data."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
import logging
import re

from sqlalchemy.orm import Session

from src.models.invoice_pilot.invoice import Invoice
from src.services.invoice_pilot.invoice_service import InvoiceService
from src.services.invoice_pilot.gmail_service import InvoicePilotGmailService, InvoiceEmail
from src.services.invoice_pilot.pdf_parser import get_pdf_parser, PDFParseError
from src.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class InvoiceDetectionService:
    """
    Service for detecting invoices in Gmail and extracting data.

    This service orchestrates the invoice detection workflow:
    1. Scan Gmail for sent emails with attachments (potential invoices)
    2. Call LLM to detect if email contains an invoice
    3. Extract invoice data from PDF using multimodal LLM
    4. Calculate confidence score
    5. Create invoice record via InvoiceService
    """

    # Minimum confidence threshold for auto-confirmation
    CONFIDENCE_THRESHOLD = 0.8

    def __init__(
        self,
        db: Session,
        user_id: UUID,
        invoice_service: Optional[InvoiceService] = None,
        gmail_service: Optional[InvoicePilotGmailService] = None,
    ):
        self.db = db
        self.user_id = user_id
        self.invoice_service = invoice_service or InvoiceService(db)
        self.gmail_service = gmail_service or InvoicePilotGmailService(db, user_id)
        self.pdf_parser = get_pdf_parser()

    # --- Gmail Scanning ---

    async def scan_gmail_for_invoices(
        self,
        tenant_id: UUID,
        days_back: int = 30,
        max_results: int = 50,
    ) -> List[Invoice]:
        """
        Scan Gmail sent folder for potential invoices.

        Args:
            tenant_id: Tenant ID
            days_back: Number of days to look back
            max_results: Maximum number of emails to process

        Returns:
            List of created Invoice objects
        """
        logger.info(f"Scanning Gmail for invoices (last {days_back} days)")

        # Scan Gmail
        emails = await self.gmail_service.scan_sent_folder(
            days_back=days_back,
            max_results=max_results,
            only_with_attachments=True,
        )

        logger.info(f"Found {len(emails)} emails with PDF attachments")

        invoices = []
        for email in emails:
            try:
                # Process each email
                invoice = await self.process_email_for_invoice(tenant_id, email)
                if invoice:
                    invoices.append(invoice)
            except Exception as e:
                logger.error(f"Error processing email {email.message_id}: {e}")
                continue

        logger.info(f"Created {len(invoices)} invoices from Gmail scan")
        return invoices

    async def process_email_for_invoice(
        self,
        tenant_id: UUID,
        email: InvoiceEmail,
    ) -> Optional[Invoice]:
        """
        Process a single email to detect and extract invoice data.

        Args:
            tenant_id: Tenant ID
            email: InvoiceEmail object from Gmail scan

        Returns:
            Created Invoice object or None if not an invoice
        """
        # Check if already processed
        existing = self.invoice_service.get_by_gmail_message_id(tenant_id, email.message_id)
        if existing:
            logger.debug(f"Email {email.message_id} already processed")
            return None

        # Extract PDF attachments
        pdf_attachments = [
            att for att in email.attachments
            if att.get("filename", "").lower().endswith(".pdf")
        ]

        if not pdf_attachments:
            logger.debug(f"Email {email.message_id} has no PDF attachments")
            return None

        # Process first PDF attachment (usually invoices are single-page or first attachment)
        attachment = pdf_attachments[0]
        pdf_bytes = await self.gmail_service.get_attachment(
            email.message_id,
            attachment["attachmentId"],
        )

        # Validate PDF
        if not self.pdf_parser.is_valid_invoice_pdf(pdf_bytes):
            logger.warning(f"PDF from {email.message_id} is invalid or too large")
            return None

        # Extract data from PDF
        try:
            pdf_data = self.pdf_parser.extract_structured_data(pdf_bytes, prefer_images=False)
        except PDFParseError as e:
            logger.error(f"Failed to parse PDF from {email.message_id}: {e}")
            return None

        # TODO: Call LLM to detect and extract invoice data
        # For now, return None (this will be implemented in the agent)
        logger.info(f"PDF extracted from {email.message_id}, ready for LLM processing")

        # Placeholder for LLM detection result
        # This will be called from the LangGraph agent in production
        return None

    # --- Detection Workflow ---

    def detect_and_create_invoice(
        self,
        tenant_id: UUID,
        gmail_message_id: str,
        email_data: dict,
        llm_detection_result: dict,
    ) -> Invoice:
        """
        Create an invoice from LLM detection results.

        Args:
            tenant_id: Tenant ID
            gmail_message_id: Gmail message ID
            email_data: Email metadata (sender, subject, etc)
            llm_detection_result: LLM extraction result containing invoice data

        Returns:
            Created Invoice object

        Expected llm_detection_result format:
        {
            "is_invoice": true,
            "confidence": 0.95,
            "invoice_number": "INV-001",
            "client_name": "Acme Corp",
            "client_email": "billing@acme.com",
            "amount_total": "1500.00",
            "currency": "USD",
            "issue_date": "2024-01-15",
            "due_date": "2024-02-15",
            "pdf_url": "https://storage.../invoice.pdf",
            "notes": "Extracted from PDF attachment"
        }
        """
        # Validate detection result
        if not llm_detection_result.get("is_invoice"):
            raise ValidationError("Email does not contain an invoice")

        # Extract and validate fields
        try:
            invoice_number = llm_detection_result.get("invoice_number")
            client_name = llm_detection_result["client_name"]
            client_email = llm_detection_result["client_email"]
            amount_total = Decimal(str(llm_detection_result["amount_total"]))
            currency = llm_detection_result.get("currency", "USD").upper()
            issue_date = self._parse_date(llm_detection_result["issue_date"])
            due_date = self._parse_date(llm_detection_result["due_date"])
            confidence = float(llm_detection_result.get("confidence", 0.0))
            pdf_url = llm_detection_result.get("pdf_url")
            notes = llm_detection_result.get("notes")

        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Invalid detection result format: {e}")
            raise ValidationError(f"Invalid detection result: {e}")

        # Validate currency code (basic check for 3-letter ISO code)
        if not self._validate_currency(currency):
            logger.warning(f"Invalid currency code: {currency}, defaulting to USD")
            currency = "USD"

        # Validate dates
        if issue_date > due_date:
            logger.warning(
                f"Issue date {issue_date} is after due date {due_date}, swapping"
            )
            issue_date, due_date = due_date, issue_date

        # Validate amount
        if amount_total <= 0:
            raise ValidationError(f"Invalid amount: {amount_total}")

        # Determine initial status based on confidence
        if confidence >= self.CONFIDENCE_THRESHOLD:
            status = "pending"  # Auto-confirmed
        else:
            status = "detected"  # Needs human confirmation

        # Create invoice
        invoice = self.invoice_service.create(
            tenant_id=tenant_id,
            gmail_message_id=gmail_message_id,
            invoice_number=invoice_number,
            client_name=client_name,
            client_email=client_email,
            amount_total=amount_total,
            currency=currency,
            issue_date=issue_date,
            due_date=due_date,
            confidence=confidence,
            pdf_url=pdf_url,
            notes=notes,
            status=status,
        )

        logger.info(
            f"Created invoice {invoice.id} from email {gmail_message_id} "
            f"with confidence {confidence:.2f}"
        )

        return invoice

    def calculate_confidence(
        self,
        extraction_data: dict,
        email_context: dict,
    ) -> float:
        """
        Calculate confidence score for invoice extraction.

        Factors:
        - Required fields present (invoice_number, amount, dates)
        - Email sender matches client email
        - PDF attachment present
        - Amount format valid
        - Dates logical (issue < due)
        - Currency code valid

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        total_checks = 8

        # Required fields present
        required_fields = [
            "client_name",
            "client_email",
            "amount_total",
            "issue_date",
            "due_date",
        ]
        if all(extraction_data.get(field) for field in required_fields):
            score += 1.0

        # Invoice number present (nice to have but not required)
        if extraction_data.get("invoice_number"):
            score += 1.0

        # Email sender matches client email
        sender_email = email_context.get("sender_email", "")
        client_email = extraction_data.get("client_email", "")
        if sender_email and client_email and sender_email.lower() == client_email.lower():
            score += 1.0

        # PDF attachment present
        if extraction_data.get("pdf_url"):
            score += 1.0

        # Amount is valid
        try:
            amount = Decimal(str(extraction_data.get("amount_total", 0)))
            if amount > 0:
                score += 1.0
        except (ValueError, TypeError):
            pass

        # Dates are logical
        try:
            issue_date = self._parse_date(extraction_data.get("issue_date"))
            due_date = self._parse_date(extraction_data.get("due_date"))
            if issue_date and due_date and issue_date <= due_date:
                score += 1.0
        except (ValueError, TypeError):
            pass

        # Currency code valid
        currency = extraction_data.get("currency", "USD")
        if self._validate_currency(currency):
            score += 1.0

        # Client email format valid
        if client_email and self._validate_email(client_email):
            score += 1.0

        return score / total_checks

    # --- Validation Helpers ---

    def _parse_date(self, date_str: str) -> date:
        """
        Parse date string in various formats.

        Supports:
        - ISO format: 2024-01-15
        - US format: 01/15/2024
        - EU format: 15/01/2024
        - Long format: January 15, 2024
        """
        if isinstance(date_str, date):
            return date_str

        if isinstance(date_str, datetime):
            return date_str.date()

        # Try ISO format first
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

        # Try US format
        try:
            return datetime.strptime(date_str, "%m/%d/%Y").date()
        except ValueError:
            pass

        # Try EU format
        try:
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        except ValueError:
            pass

        # Try long format
        try:
            return datetime.strptime(date_str, "%B %d, %Y").date()
        except ValueError:
            pass

        raise ValueError(f"Unable to parse date: {date_str}")

    def _validate_currency(self, currency: str) -> bool:
        """Validate ISO 4217 currency code (basic check)."""
        if not currency:
            return False

        # Must be 3 uppercase letters
        if not re.match(r"^[A-Z]{3}$", currency):
            return False

        # Common currency codes
        common_currencies = {
            "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
            "CNY", "INR", "BRL", "MXN", "ZAR", "SEK", "NOK", "DKK",
            "SGD", "HKD", "KRW", "TRY", "RUB", "PLN", "THB", "MYR",
        }

        return currency in common_currencies

    def _validate_email(self, email: str) -> bool:
        """Basic email validation."""
        if not email:
            return False

        # Simple regex for email validation
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    # --- Data Extraction Helpers ---

    def extract_client_info_from_email(self, email_data: dict) -> dict:
        """
        Extract client information from email metadata.

        Useful as fallback if LLM extraction fails or as validation.

        Args:
            email_data: Email metadata dict with 'to', 'from', 'subject'

        Returns:
            Dict with client_email and client_name
        """
        # For sent emails, 'to' field contains client info
        to_field = email_data.get("to", "")

        # Extract email and name from "Name <email@domain.com>" format
        match = re.match(r"^(.*?)\s*<(.+?)>$", to_field)
        if match:
            client_name = match.group(1).strip()
            client_email = match.group(2).strip()
        else:
            # Just email address
            client_email = to_field.strip()
            client_name = client_email.split("@")[0]  # Use email prefix as name

        return {
            "client_name": client_name,
            "client_email": client_email,
        }

    def extract_amount_from_text(self, text: str) -> Optional[Decimal]:
        """
        Extract monetary amount from text using regex.

        Looks for patterns like:
        - $1,500.00
        - 1500.00 USD
        - Total: 1,500.00

        Returns:
            Decimal amount or None if not found
        """
        # Patterns for amounts
        patterns = [
            r"\$\s*([0-9,]+\.?[0-9]*)",  # $1,500.00
            r"([0-9,]+\.?[0-9]*)\s*(?:USD|EUR|GBP)",  # 1500.00 USD
            r"Total:?\s*\$?\s*([0-9,]+\.?[0-9]*)",  # Total: $1,500.00
            r"Amount:?\s*\$?\s*([0-9,]+\.?[0-9]*)",  # Amount: $1,500.00
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    return Decimal(amount_str)
                except ValueError:
                    continue

        return None
