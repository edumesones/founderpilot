"""
Invoice API endpoints for InvoicePilot
"""

import logging
from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

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
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    status: Optional[InvoiceStatus] = Query(None, description="Filter by status"),
    client_name: Optional[str] = Query(None, description="Filter by client name (partial match)"),
    client_email: Optional[str] = Query(None, description="Filter by client email"),
    currency: Optional[str] = Query(None, description="Filter by currency code"),
    min_amount: Optional[float] = Query(None, description="Filter by minimum amount"),
    max_amount: Optional[float] = Query(None, description="Filter by maximum amount"),
    issue_date_from: Optional[date] = Query(None, description="Filter by issue date from"),
    issue_date_to: Optional[date] = Query(None, description="Filter by issue date to"),
    due_date_from: Optional[date] = Query(None, description="Filter by due date from"),
    due_date_to: Optional[date] = Query(None, description="Filter by due date to"),
    overdue_only: bool = Query(False, description="Show only overdue invoices"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("due_date", description="Sort field"),
    sort_order: str = Query("asc", description="Sort order (asc/desc)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceListResponse:
    """
    List invoices with optional filters.

    Returns paginated list of invoices for the current tenant.
    """
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

    try:
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{invoice_id}", response_model=InvoiceWithReminders)
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

    try:
        invoice = await service.get_invoice_with_reminders(
            invoice_id=invoice_id,
            tenant_id=user.tenant_id,
        )

        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{invoice_id}/confirm", response_model=InvoiceResponse)
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

    try:
        invoice = await service.confirm_invoice(
            invoice_id=invoice_id,
            tenant_id=user.tenant_id,
            notes=confirm_data.notes,
            confirmed_by=user.id,
        )

        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        logger.info(f"Invoice {invoice_id} confirmed by user {user.id}")
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{invoice_id}/reject", response_model=dict)
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

    try:
        success = await service.reject_invoice(
            invoice_id=invoice_id,
            tenant_id=user.tenant_id,
            reason=reject_data.reason,
            rejected_by=user.id,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Invoice not found")

        logger.info(f"Invoice {invoice_id} rejected by user {user.id}: {reject_data.reason}")
        return {"message": "Invoice rejected successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
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

    try:
        invoice = await service.mark_as_paid(
            invoice_id=invoice_id,
            tenant_id=user.tenant_id,
            amount=payment_data.amount,
            payment_date=payment_data.payment_date,
            notes=payment_data.notes,
            recorded_by=user.id,
        )

        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        logger.info(
            f"Invoice {invoice_id} payment recorded by user {user.id}: "
            f"{payment_data.amount} ({invoice.status})"
        )
        return invoice
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/settings", response_model=InvoiceSettings)
async def get_invoice_settings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceSettings:
    """
    Get InvoicePilot settings for the tenant.

    Returns configuration including reminder schedule, confidence threshold, etc.
    """
    service = InvoiceService(db)

    try:
        settings = await service.get_settings(tenant_id=user.tenant_id)
        return settings
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/settings", response_model=InvoiceSettings)
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

    try:
        settings = await service.update_settings(
            tenant_id=user.tenant_id,
            settings_update=settings_update,
        )

        logger.info(f"Invoice settings updated by user {user.id} for tenant {user.tenant_id}")
        return settings
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
