"""
Invoice API endpoints for InvoicePilot
"""

import logging
from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.api.dependencies import get_db, get_current_user, CurrentUser, DbSession
from src.models.user import User
from src.services.invoice_service import InvoiceService
from src.services.reminder_service import ReminderService
from src.schemas.invoice import (
    InvoiceResponse,
    InvoiceWithReminders,
    InvoiceListResponse,
    InvoiceConfirm,
    InvoiceReject,
    InvoiceMarkPaid,
    InvoiceSettings,
    InvoiceSettingsUpdate,
    InvoiceStatus,
    ReminderResponse,
    ReminderApprove,
    ReminderEdit,
    ReminderSkip,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoices", tags=["invoices"])


# ========== ERROR HANDLING ==========


class InvoiceNotFoundError(Exception):
    """Raised when invoice is not found or doesn't belong to tenant."""
    pass


class ReminderNotFoundError(Exception):
    """Raised when reminder is not found or doesn't belong to tenant."""
    pass


class InvalidOperationError(Exception):
    """Raised when operation is not valid for current invoice state."""
    pass


def handle_service_errors(func):
    """Decorator to handle common service layer errors."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except InvoiceNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e) or "Invoice not found or access denied",
            )
        except ReminderNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e) or "Reminder not found or access denied",
            )
        except InvalidOperationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        except IntegrityError as e:
            logger.error(f"Database integrity error: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Operation conflicts with existing data",
            )
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred",
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred",
            )
    return wrapper


@router.get("", response_model=InvoiceListResponse)
@handle_service_errors
async def list_invoices(
    status: Optional[InvoiceStatus] = Query(None, description="Filter by status"),
    client_name: Optional[str] = Query(None, description="Filter by client name (partial match)"),
    client_email: Optional[str] = Query(None, description="Filter by client email"),
    currency: Optional[str] = Query(None, description="Filter by currency code (ISO 4217)"),
    min_amount: Optional[float] = Query(None, ge=0, description="Filter by minimum amount"),
    max_amount: Optional[float] = Query(None, ge=0, description="Filter by maximum amount"),
    issue_date_from: Optional[date] = Query(None, description="Filter by issue date from"),
    issue_date_to: Optional[date] = Query(None, description="Filter by issue date to"),
    due_date_from: Optional[date] = Query(None, description="Filter by due date from"),
    due_date_to: Optional[date] = Query(None, description="Filter by due date to"),
    overdue_only: bool = Query(False, description="Show only overdue invoices"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("due_date", description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order (asc/desc)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceListResponse:
    """
    List invoices with optional filters.

    Returns paginated list of invoices for the current tenant.
    """
    # Validate amount range
    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_amount cannot be greater than max_amount",
        )

    # Validate date ranges
    if issue_date_from and issue_date_to and issue_date_from > issue_date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="issue_date_from cannot be after issue_date_to",
        )

    if due_date_from and due_date_to and due_date_from > due_date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="due_date_from cannot be after due_date_to",
        )

    service = InvoiceService(db)

    # Build filters dict
    filters = {
        "status": status,
        "client_name": client_name,
        "client_email": client_email,
        "currency": currency,
        "min_amount": min_amount,
        "max_amount": max_amount,
        "issue_date_from": issue_date_from,
        "issue_date_to": issue_date_to,
        "due_date_from": due_date_from,
        "due_date_to": due_date_to,
        "overdue_only": overdue_only,
    }

    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}

    invoices, total = await service.list_invoices(
        tenant_id=user.tenant_id,
        filters=filters,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total_pages = (total + page_size - 1) // page_size

    return InvoiceListResponse(
        invoices=invoices,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{invoice_id}", response_model=InvoiceWithReminders)
@handle_service_errors
async def get_invoice(
    invoice_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceWithReminders:
    """
    Get invoice details with reminders.

    Returns full invoice information including all reminders.
    """
    service = InvoiceService(db)

    invoice = await service.get_invoice_with_reminders(
        invoice_id=invoice_id,
        tenant_id=user.tenant_id,
    )

    if not invoice:
        raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")

    return invoice


@router.post("/{invoice_id}/confirm", response_model=InvoiceResponse)
@handle_service_errors
async def confirm_invoice(
    invoice_id: int,
    confirm_data: InvoiceConfirm,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """
    Confirm a detected invoice.

    Confirms an invoice that was detected by InvoicePilot and moves it to confirmed status.
    This triggers reminder scheduling based on the due date.
    """
    service = InvoiceService(db)

    invoice = await service.confirm_invoice(
        invoice_id=invoice_id,
        tenant_id=user.tenant_id,
        notes=confirm_data.notes,
        confirmed_by=user.id,
    )

    if not invoice:
        raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")

    logger.info(f"Invoice {invoice_id} confirmed by user {user.id}")
    return invoice


@router.post("/{invoice_id}/reject", response_model=dict)
@handle_service_errors
async def reject_invoice(
    invoice_id: int,
    reject_data: InvoiceReject,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Reject a detected invoice.

    Marks an invoice as rejected (cancelled) and logs the reason.
    This is used when InvoicePilot incorrectly detects something as an invoice.
    """
    service = InvoiceService(db)

    success = await service.reject_invoice(
        invoice_id=invoice_id,
        tenant_id=user.tenant_id,
        reason=reject_data.reason,
        rejected_by=user.id,
    )

    if not success:
        raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")

    logger.info(f"Invoice {invoice_id} rejected by user {user.id}: {reject_data.reason}")
    return {"message": "Invoice rejected successfully"}


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
@handle_service_errors
async def mark_invoice_paid(
    invoice_id: int,
    payment_data: InvoiceMarkPaid,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """
    Mark an invoice as paid (fully or partially).

    Records a payment against the invoice. If the payment amount equals the remaining balance,
    the invoice status becomes 'paid'. Otherwise, it becomes 'partially_paid'.
    """
    service = InvoiceService(db)

    invoice = await service.mark_as_paid(
        invoice_id=invoice_id,
        tenant_id=user.tenant_id,
        amount=payment_data.amount,
        payment_date=payment_data.payment_date,
        notes=payment_data.notes,
        recorded_by=user.id,
    )

    if not invoice:
        raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")

    logger.info(
        f"Invoice {invoice_id} payment recorded by user {user.id}: "
        f"{payment_data.amount} ({invoice.status})"
    )
    return invoice


@router.get("/settings", response_model=InvoiceSettings)
@handle_service_errors
async def get_invoice_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceSettings:
    """
    Get InvoicePilot settings for the tenant.

    Returns configuration including reminder schedule, confidence threshold, etc.
    """
    service = InvoiceService(db)
    settings = await service.get_settings(tenant_id=user.tenant_id)
    return settings


@router.put("/settings", response_model=InvoiceSettings)
@handle_service_errors
async def update_invoice_settings(
    settings_update: InvoiceSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceSettings:
    """
    Update InvoicePilot settings for the tenant.

    Allows configuration of reminder schedule, confidence threshold, escalation rules, etc.
    """
    service = InvoiceService(db)

    settings = await service.update_settings(
        tenant_id=user.tenant_id,
        settings_update=settings_update,
    )

    logger.info(f"Invoice settings updated by user {user.id} for tenant {user.tenant_id}")
    return settings


# ========== REMINDER ENDPOINTS ==========


@router.get("/{invoice_id}/reminders", response_model=List[ReminderResponse])
@handle_service_errors
async def list_invoice_reminders(
    invoice_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ReminderResponse]:
    """
    Get all reminders for an invoice.

    Returns all reminders (scheduled, sent, skipped) for the specified invoice.
    """
    service = ReminderService(db)
    reminders = await service.get_reminders_for_invoice(
        invoice_id=invoice_id,
        tenant_id=user.tenant_id,
    )
    return reminders


@router.post("/{invoice_id}/reminders/{reminder_id}/approve", response_model=ReminderResponse)
@handle_service_errors
async def approve_reminder(
    invoice_id: int,
    reminder_id: int,
    approve_data: ReminderApprove,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """
    Approve a reminder for sending.

    Approves a draft reminder. The reminder will be sent at its scheduled time.
    Optionally allows editing the final message before approval.
    """
    service = ReminderService(db)

    reminder = await service.approve_reminder(
        reminder_id=reminder_id,
        invoice_id=invoice_id,
        tenant_id=user.tenant_id,
        final_message=approve_data.final_message,
        approved_by=user.id,
    )

    if not reminder:
        raise ReminderNotFoundError(f"Reminder {reminder_id} not found")

    logger.info(f"Reminder {reminder_id} for invoice {invoice_id} approved by user {user.id}")
    return reminder


@router.post("/{invoice_id}/reminders/{reminder_id}/edit", response_model=ReminderResponse)
@handle_service_errors
async def edit_reminder(
    invoice_id: int,
    reminder_id: int,
    edit_data: ReminderEdit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReminderResponse:
    """
    Edit a reminder message.

    Allows editing the message of a scheduled reminder before it is sent.
    """
    service = ReminderService(db)

    reminder = await service.edit_reminder(
        reminder_id=reminder_id,
        invoice_id=invoice_id,
        tenant_id=user.tenant_id,
        new_message=edit_data.message,
        edited_by=user.id,
    )

    if not reminder:
        raise ReminderNotFoundError(f"Reminder {reminder_id} not found")

    logger.info(f"Reminder {reminder_id} for invoice {invoice_id} edited by user {user.id}")
    return reminder


@router.post("/{invoice_id}/reminders/{reminder_id}/skip", response_model=dict)
@handle_service_errors
async def skip_reminder(
    invoice_id: int,
    reminder_id: int,
    skip_data: ReminderSkip,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Skip a scheduled reminder.

    Marks a reminder as skipped so it won't be sent. Useful when payment is received
    or when a reminder is no longer needed.
    """
    service = ReminderService(db)

    success = await service.skip_reminder(
        reminder_id=reminder_id,
        invoice_id=invoice_id,
        tenant_id=user.tenant_id,
        reason=skip_data.reason,
        skipped_by=user.id,
    )

    if not success:
        raise ReminderNotFoundError(f"Reminder {reminder_id} not found")

    logger.info(
        f"Reminder {reminder_id} for invoice {invoice_id} skipped by user {user.id}: "
        f"{skip_data.reason}"
    )
    return {"message": "Reminder skipped successfully"}
