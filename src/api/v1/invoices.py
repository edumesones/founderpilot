"""
Invoice API endpoints for InvoicePilot.

The endpoints are synchronous (`def`, not `async def`) on purpose: InvoiceService
and ReminderService are synchronous SQLAlchemy services, so FastAPI runs these
handlers in its threadpool instead of blocking the event loop.
"""

import logging
import math
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.core.database import get_sync_db
from src.core.exceptions import NotFoundError, ValidationError
from src.models.user import User
from src.schemas.invoice import (
    InvoiceConfirm,
    InvoiceListResponse,
    InvoiceMarkPaid,
    InvoiceReject,
    InvoiceResponse,
    InvoiceStatus,
    InvoiceWithReminders,
    ReminderApprove,
    ReminderEdit,
    ReminderResponse,
    ReminderSkip,
)
from src.services.invoice_pilot.invoice_service import InvoiceService
from src.services.invoice_pilot.reminder_service import ReminderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoices", tags=["invoices"])


# ========== HELPERS ==========


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=detail)


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
    )


def _owned_invoice(service: InvoiceService, invoice_id: UUID, tenant_id: UUID):
    """Fetch an invoice or raise 404.

    The service scopes every lookup by tenant, so another tenant's invoice is
    indistinguishable from one that does not exist -- which is what we want.
    """
    try:
        return service.get(invoice_id, tenant_id)
    except NotFoundError:
        raise _not_found(f"Invoice {invoice_id} not found")


# ========== INVOICE ENDPOINTS ==========


@router.get("", response_model=InvoiceListResponse)
def list_invoices(
    status: Optional[InvoiceStatus] = Query(None, description="Filter by status"),
    client_email: Optional[str] = Query(None, description="Filter by client email"),
    date_from: Optional[date] = Query(None, description="Filter by due date from"),
    date_to: Optional[date] = Query(None, description="Filter by due date to"),
    amount_min: Optional[Decimal] = Query(None, ge=0, description="Minimum amount"),
    amount_max: Optional[Decimal] = Query(None, ge=0, description="Maximum amount"),
    overdue_only: bool = Query(False, description="Show only overdue invoices"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> InvoiceListResponse:
    """List the current tenant's invoices."""
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise _unprocessable("amount_min cannot be greater than amount_max")
    if date_from and date_to and date_from > date_to:
        raise _unprocessable("date_from cannot be after date_to")

    service = InvoiceService(db)
    invoices = service.list(
        tenant_id=user.id,
        status=status.value if status else None,
        client_email=client_email,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        is_overdue=True if overdue_only else None,
        limit=limit,
        offset=offset,
    )
    # `list` already applies the window; the unpaginated total needs its own count.
    total = len(
        service.list(
            tenant_id=user.id,
            status=status.value if status else None,
            client_email=client_email,
            date_from=date_from,
            date_to=date_to,
            amount_min=amount_min,
            amount_max=amount_max,
            is_overdue=True if overdue_only else None,
            limit=None,
            offset=0,
        )
    )

    return InvoiceListResponse(
        invoices=[InvoiceResponse.model_validate(i) for i in invoices],
        total=total,
        page=(offset // limit) + 1,
        page_size=limit,
        total_pages=max(1, math.ceil(total / limit)),
    )


@router.get("/{invoice_id}", response_model=InvoiceWithReminders)
def get_invoice(
    invoice_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> InvoiceWithReminders:
    """Get one invoice, with its reminders."""
    service = InvoiceService(db)
    invoice = _owned_invoice(service, invoice_id, user.id)
    reminders = ReminderService(db).list_reminders_for_invoice(invoice.id)

    return InvoiceWithReminders(
        **InvoiceResponse.model_validate(invoice).model_dump(),
        reminders=[ReminderResponse.model_validate(r) for r in reminders],
    )


@router.post("/{invoice_id}/confirm", response_model=InvoiceResponse)
def confirm_invoice(
    invoice_id: UUID,
    confirm_data: Optional[InvoiceConfirm] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> InvoiceResponse:
    """Confirm a detected invoice, optionally correcting what was extracted."""
    service = InvoiceService(db)
    _owned_invoice(service, invoice_id, user.id)

    if confirm_data:
        corrections = confirm_data.model_dump(exclude_none=True)
        if corrections:
            try:
                service.update(invoice_id, user.id, **corrections)
            except ValidationError as exc:
                raise _unprocessable(str(exc))

    try:
        invoice = service.confirm_invoice(
            invoice_id=invoice_id, tenant_id=user.id, actor=str(user.id)
        )
    except ValidationError as exc:
        raise _unprocessable(str(exc))

    logger.info("Invoice %s confirmed by user %s", invoice_id, user.id)
    return InvoiceResponse.model_validate(invoice)


@router.post("/{invoice_id}/reject", response_model=dict)
def reject_invoice(
    invoice_id: UUID,
    reject_data: InvoiceReject,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> dict:
    """Reject a detected invoice (a false positive)."""
    service = InvoiceService(db)
    _owned_invoice(service, invoice_id, user.id)

    service.reject_invoice(
        invoice_id=invoice_id,
        tenant_id=user.id,
        reason=reject_data.reason,
        actor=str(user.id),
    )
    logger.info(
        "Invoice %s rejected by user %s: %s", invoice_id, user.id, reject_data.reason
    )
    return {"message": "Invoice rejected successfully"}


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
def mark_invoice_paid(
    invoice_id: UUID,
    payment_data: InvoiceMarkPaid,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> InvoiceResponse:
    """Record a payment. Full payment marks the invoice paid, otherwise partial."""
    service = InvoiceService(db)
    _owned_invoice(service, invoice_id, user.id)

    try:
        invoice = service.mark_as_paid(
            invoice_id=invoice_id,
            tenant_id=user.id,
            amount_paid=payment_data.amount_paid,
            actor=str(user.id),
        )
    except ValidationError as exc:
        raise _unprocessable(str(exc))

    logger.info(
        "Invoice %s payment recorded by user %s: %s (%s)",
        invoice_id,
        user.id,
        payment_data.amount_paid,
        invoice.status,
    )
    return InvoiceResponse.model_validate(invoice)


# ========== REMINDER ENDPOINTS ==========


@router.get("/{invoice_id}/reminders", response_model=List[ReminderResponse])
def list_invoice_reminders(
    invoice_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> List[ReminderResponse]:
    """List every reminder (pending, approved, sent, skipped) for an invoice."""
    invoice = _owned_invoice(InvoiceService(db), invoice_id, user.id)
    reminders = ReminderService(db).list_reminders_for_invoice(invoice.id)
    return [ReminderResponse.model_validate(r) for r in reminders]


@router.post(
    "/{invoice_id}/reminders/{reminder_id}/approve", response_model=ReminderResponse
)
def approve_reminder(
    invoice_id: UUID,
    reminder_id: UUID,
    approve_data: Optional[ReminderApprove] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> ReminderResponse:
    """Approve a drafted reminder, optionally replacing the message."""
    _owned_invoice(InvoiceService(db), invoice_id, user.id)
    reminder_service = ReminderService(db)

    try:
        reminder = reminder_service.approve_reminder(
            reminder_id=reminder_id,
            approved_by=str(user.id),
            edited_message=approve_data.final_message if approve_data else None,
        )
    except NotFoundError:
        raise _not_found(f"Reminder {reminder_id} not found")
    except ValidationError as exc:
        raise _unprocessable(str(exc))

    logger.info("Reminder %s approved by user %s", reminder_id, user.id)
    return ReminderResponse.model_validate(reminder)


@router.post(
    "/{invoice_id}/reminders/{reminder_id}/edit", response_model=ReminderResponse
)
def edit_reminder(
    invoice_id: UUID,
    reminder_id: UUID,
    edit_data: ReminderEdit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> ReminderResponse:
    """Replace the message of a reminder that has not been sent yet."""
    _owned_invoice(InvoiceService(db), invoice_id, user.id)

    try:
        reminder = ReminderService(db).edit_reminder(
            reminder_id=reminder_id,
            edited_message=edit_data.new_message,
            edited_by=str(user.id),
        )
    except NotFoundError:
        raise _not_found(f"Reminder {reminder_id} not found")
    except ValidationError as exc:
        raise _unprocessable(str(exc))

    logger.info("Reminder %s edited by user %s", reminder_id, user.id)
    return ReminderResponse.model_validate(reminder)


@router.post("/{invoice_id}/reminders/{reminder_id}/skip", response_model=dict)
def skip_reminder(
    invoice_id: UUID,
    reminder_id: UUID,
    skip_data: Optional[ReminderSkip] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db),
) -> dict:
    """Skip a scheduled reminder so it is never sent."""
    _owned_invoice(InvoiceService(db), invoice_id, user.id)

    try:
        ReminderService(db).skip_reminder(
            reminder_id=reminder_id,
            skipped_by=str(user.id),
            reason=skip_data.reason if skip_data else None,
        )
    except NotFoundError:
        raise _not_found(f"Reminder {reminder_id} not found")
    except ValidationError as exc:
        raise _unprocessable(str(exc))

    logger.info("Reminder %s skipped by user %s", reminder_id, user.id)
    return {"message": "Reminder skipped successfully"}
