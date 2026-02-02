"""
Invoice Validation Service

Provides validation logic for invoice data including:
- Invoice data validation (amounts, dates, etc)
- Currency code validation (ISO 4217)
- LLM input/output sanitization
"""

from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Dict, Any
import re


class InvoiceValidationError(Exception):
    """Raised when invoice validation fails"""
    pass


class InvoiceValidationService:
    """Service for validating invoice data"""

    # ISO 4217 currency codes (common ones)
    VALID_CURRENCIES = {
        'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD',
        'MXN', 'SGD', 'HKD', 'NOK', 'KRW', 'TRY', 'INR', 'RUB', 'BRL', 'ZAR',
        'DKK', 'PLN', 'TWD', 'THB', 'MYR', 'IDR', 'HUF', 'CZK', 'ILS', 'CLP',
        'PHP', 'AED', 'COP', 'SAR', 'RON', 'VND', 'ARS', 'EGP', 'PKR', 'BGN'
    }

    # Email validation regex (basic)
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    # Invoice number regex (alphanumeric with common separators)
    INVOICE_NUMBER_REGEX = re.compile(r'^[A-Za-z0-9\-_/]+$')

    @staticmethod
    def validate_invoice_data(
        invoice_number: Optional[str] = None,
        client_name: Optional[str] = None,
        client_email: Optional[str] = None,
        amount_total: Optional[float] = None,
        amount_paid: Optional[float] = None,
        currency: Optional[str] = None,
        issue_date: Optional[date] = None,
        due_date: Optional[date] = None,
        confidence: Optional[float] = None
    ) -> Dict[str, List[str]]:
        """
        Validate invoice data fields.

        Args:
            invoice_number: Invoice number
            client_name: Client name
            client_email: Client email
            amount_total: Total invoice amount
            amount_paid: Amount already paid
            currency: Currency code
            issue_date: Invoice issue date
            due_date: Invoice due date
            confidence: LLM confidence score

        Returns:
            Dict with 'errors' key containing list of validation errors
            Empty list if all validations pass
        """
        errors = []

        # Validate invoice number
        if invoice_number is not None:
            if not invoice_number or len(invoice_number.strip()) == 0:
                errors.append("Invoice number cannot be empty")
            elif len(invoice_number) > 100:
                errors.append("Invoice number too long (max 100 chars)")
            elif not InvoiceValidationService.INVOICE_NUMBER_REGEX.match(invoice_number):
                errors.append("Invoice number contains invalid characters")

        # Validate client name
        if client_name is not None:
            if not client_name or len(client_name.strip()) == 0:
                errors.append("Client name cannot be empty")
            elif len(client_name) > 200:
                errors.append("Client name too long (max 200 chars)")

        # Validate client email
        if client_email is not None:
            if client_email and not InvoiceValidationService.EMAIL_REGEX.match(client_email):
                errors.append(f"Invalid email format: {client_email}")
            elif client_email and len(client_email) > 255:
                errors.append("Email too long (max 255 chars)")

        # Validate amount_total
        if amount_total is not None:
            try:
                amount = Decimal(str(amount_total))
                if amount <= 0:
                    errors.append("Amount total must be greater than 0")
                elif amount > Decimal('999999999.99'):
                    errors.append("Amount total too large")
            except (InvalidOperation, ValueError):
                errors.append(f"Invalid amount total: {amount_total}")

        # Validate amount_paid
        if amount_paid is not None:
            try:
                paid = Decimal(str(amount_paid))
                if paid < 0:
                    errors.append("Amount paid cannot be negative")
                elif amount_total is not None and paid > Decimal(str(amount_total)):
                    errors.append("Amount paid cannot exceed total amount")
            except (InvalidOperation, ValueError):
                errors.append(f"Invalid amount paid: {amount_paid}")

        # Validate currency
        if currency is not None:
            if not currency:
                errors.append("Currency code cannot be empty")
            elif currency.upper() not in InvoiceValidationService.VALID_CURRENCIES:
                errors.append(f"Invalid currency code: {currency}")

        # Validate dates
        if issue_date is not None and due_date is not None:
            if due_date < issue_date:
                errors.append("Due date cannot be before issue date")

        if issue_date is not None:
            # Check if issue date is not too far in the future (max 30 days)
            if isinstance(issue_date, date):
                days_diff = (issue_date - date.today()).days
                if days_diff > 30:
                    errors.append("Issue date cannot be more than 30 days in the future")

        if due_date is not None:
            # Check if due date is not too far in the past (max 5 years)
            if isinstance(due_date, date):
                days_diff = (date.today() - due_date).days
                if days_diff > 1825:  # ~5 years
                    errors.append("Due date cannot be more than 5 years in the past")

        # Validate confidence score
        if confidence is not None:
            if not (0 <= confidence <= 1):
                errors.append(f"Confidence score must be between 0 and 1, got {confidence}")

        return {"errors": errors}

    @staticmethod
    def validate_currency_code(currency: str) -> bool:
        """
        Validate if currency code is valid ISO 4217.

        Args:
            currency: Currency code to validate

        Returns:
            True if valid, False otherwise
        """
        if not currency:
            return False
        return currency.upper() in InvoiceValidationService.VALID_CURRENCIES

    @staticmethod
    def sanitize_llm_input(text: str, max_length: int = 10000) -> str:
        """
        Sanitize text before sending to LLM.

        Args:
            text: Text to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Truncate to max length
        text = text[:max_length]

        # Remove null bytes
        text = text.replace('\x00', '')

        # Normalize whitespace
        text = ' '.join(text.split())

        return text.strip()

    @staticmethod
    def sanitize_llm_output(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize data received from LLM.

        Args:
            data: Dictionary of data from LLM

        Returns:
            Sanitized dictionary
        """
        sanitized = {}

        for key, value in data.items():
            # Remove None values
            if value is None:
                continue

            # Sanitize strings
            if isinstance(value, str):
                # Remove leading/trailing whitespace
                value = value.strip()

                # Remove null bytes
                value = value.replace('\x00', '')

                # Skip empty strings
                if not value:
                    continue

                sanitized[key] = value

            # Sanitize numbers
            elif isinstance(value, (int, float)):
                sanitized[key] = value

            # Sanitize lists
            elif isinstance(value, list):
                sanitized[key] = [
                    InvoiceValidationService.sanitize_llm_output(item)
                    if isinstance(item, dict) else item
                    for item in value
                ]

            # Recursively sanitize nested dicts
            elif isinstance(value, dict):
                sanitized[key] = InvoiceValidationService.sanitize_llm_output(value)

            else:
                sanitized[key] = value

        return sanitized

    @staticmethod
    def validate_and_sanitize_invoice_extraction(
        extraction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and sanitize invoice data extracted by LLM.

        Args:
            extraction: Raw extraction data from LLM

        Returns:
            Validated and sanitized extraction data

        Raises:
            InvoiceValidationError: If validation fails
        """
        # First sanitize
        sanitized = InvoiceValidationService.sanitize_llm_output(extraction)

        # Extract fields
        invoice_number = sanitized.get('invoice_number')
        client_name = sanitized.get('client_name')
        client_email = sanitized.get('client_email')
        amount_total = sanitized.get('amount_total')
        amount_paid = sanitized.get('amount_paid', 0)
        currency = sanitized.get('currency')
        issue_date = sanitized.get('issue_date')
        due_date = sanitized.get('due_date')
        confidence = sanitized.get('confidence')

        # Convert string dates to date objects if needed
        if isinstance(issue_date, str):
            try:
                issue_date = datetime.fromisoformat(issue_date).date()
                sanitized['issue_date'] = issue_date
            except (ValueError, AttributeError):
                pass

        if isinstance(due_date, str):
            try:
                due_date = datetime.fromisoformat(due_date).date()
                sanitized['due_date'] = due_date
            except (ValueError, AttributeError):
                pass

        # Validate
        validation_result = InvoiceValidationService.validate_invoice_data(
            invoice_number=invoice_number,
            client_name=client_name,
            client_email=client_email,
            amount_total=amount_total,
            amount_paid=amount_paid,
            currency=currency,
            issue_date=issue_date,
            due_date=due_date,
            confidence=confidence
        )

        if validation_result['errors']:
            raise InvoiceValidationError(
                f"Invoice validation failed: {', '.join(validation_result['errors'])}"
            )

        return sanitized
