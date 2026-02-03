"""
Invoice Pydantic Schemas

Defines request and response schemas for Invoice API endpoints.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr, field_validator
from enum import Enum


# ===== Enums =====

class InvoiceStatus(str, Enum):
    """Invoice status"""
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    SENT = "sent"
    OVERDUE = "overdue"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    CANCELLED = "cancelled"


class ReminderType(str, Enum):
    """Reminder type"""
    PRE_DUE = "pre_due"
    ON_DUE = "on_due"
    POST_DUE = "post_due"
    ESCALATION = "escalation"


class ReminderStatus(str, Enum):
    """Reminder status"""
    SCHEDULED = "scheduled"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"


class ActionType(str, Enum):
    """Invoice action type"""
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    PAYMENT_RECORDED = "payment_recorded"
    REMINDER_SCHEDULED = "reminder_scheduled"
    REMINDER_SENT = "reminder_sent"
    ESCALATED = "escalated"
    CANCELLED = "cancelled"


# ===== Base Schemas =====

class InvoiceBase(BaseModel):
    """Base invoice schema"""
    invoice_number: str = Field(..., min_length=1, max_length=100)
    client_name: str = Field(..., min_length=1, max_length=200)
    client_email: Optional[EmailStr] = None
    amount_total: Decimal = Field(..., gt=0, decimal_places=2)
    amount_paid: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    currency: str = Field(..., min_length=3, max_length=3)
    issue_date: date
    due_date: date
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Ensure currency is uppercase"""
        return v.upper()

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v: date, info) -> date:
        """Validate due date is after issue date"""
        issue_date = info.data.get('issue_date')
        if issue_date and v < issue_date:
            raise ValueError('due_date must be after issue_date')
        return v


# ===== Invoice Schemas =====

class InvoiceCreate(InvoiceBase):
    """Schema for creating an invoice manually"""
    gmail_message_id: Optional[str] = Field(None, max_length=255)
    pdf_url: Optional[str] = Field(None, max_length=500)
    confidence: Optional[float] = Field(None, ge=0, le=1)


class InvoiceUpdate(BaseModel):
    """Schema for updating an invoice"""
    invoice_number: Optional[str] = Field(None, min_length=1, max_length=100)
    client_name: Optional[str] = Field(None, min_length=1, max_length=200)
    client_email: Optional[EmailStr] = None
    amount_total: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    amount_paid: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    status: Optional[InvoiceStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)


class InvoiceConfirm(BaseModel):
    """Schema for confirming a detected invoice"""
    notes: Optional[str] = Field(None, max_length=1000)


class InvoiceReject(BaseModel):
    """Schema for rejecting a detected invoice"""
    reason: str = Field(..., min_length=1, max_length=500)


class InvoiceMarkPaid(BaseModel):
    """Schema for marking an invoice as paid"""
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payment_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)


class InvoiceResponse(InvoiceBase):
    """Schema for invoice response"""
    id: int
    tenant_id: int
    gmail_message_id: Optional[str] = None
    status: InvoiceStatus
    pdf_url: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvoiceWithReminders(InvoiceResponse):
    """Schema for invoice with reminders"""
    reminders: List['ReminderResponse'] = []


class InvoiceListResponse(BaseModel):
    """Schema for paginated invoice list"""
    invoices: List[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ===== Reminder Schemas =====

class ReminderBase(BaseModel):
    """Base reminder schema"""
    type: ReminderType
    scheduled_at: datetime


class ReminderCreate(ReminderBase):
    """Schema for creating a reminder"""
    invoice_id: int
    draft_message: Optional[str] = Field(None, max_length=2000)


class ReminderUpdate(BaseModel):
    """Schema for updating a reminder"""
    scheduled_at: Optional[datetime] = None
    draft_message: Optional[str] = Field(None, max_length=2000)
    final_message: Optional[str] = Field(None, max_length=2000)


class ReminderApprove(BaseModel):
    """Schema for approving a reminder"""
    final_message: Optional[str] = Field(None, max_length=2000)
    send_immediately: bool = Field(default=False)


class ReminderEdit(BaseModel):
    """Schema for editing a reminder"""
    message: str = Field(..., min_length=1, max_length=2000)
    scheduled_at: Optional[datetime] = None


class ReminderSkip(BaseModel):
    """Schema for skipping a reminder"""
    reason: Optional[str] = Field(None, max_length=500)


class ReminderResponse(ReminderBase):
    """Schema for reminder response"""
    id: int
    invoice_id: int
    status: ReminderStatus
    draft_message: Optional[str] = None
    final_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    response_received: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Action Schemas =====

class ActionResponse(BaseModel):
    """Schema for invoice action response"""
    id: int
    invoice_id: int
    workflow_id: Optional[str] = None
    action_type: ActionType
    actor: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

    class Config:
        from_attributes = True


# ===== Settings Schemas =====

class ReminderScheduleSettings(BaseModel):
    """Reminder schedule settings"""
    days_before_due: List[int] = Field(default=[-3], description="Days before due date to send reminders (negative)")
    days_after_due: List[int] = Field(default=[3, 7, 14], description="Days after due date to send reminders (positive)")
    max_reminders: int = Field(default=5, ge=1, le=10)


class InvoiceSettings(BaseModel):
    """Invoice pilot settings"""
    enabled: bool = Field(default=True)
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    auto_confirm_high_confidence: bool = Field(
        default=False,
        description="Auto-confirm invoices with confidence >= threshold"
    )
    reminder_schedule: ReminderScheduleSettings = Field(default_factory=ReminderScheduleSettings)
    reminder_tone: str = Field(
        default="professional",
        description="Tone for reminder messages: professional, friendly, firm"
    )
    escalation_threshold: int = Field(
        default=3,
        ge=2,
        le=10,
        description="Number of reminders before escalation"
    )
    scan_interval_minutes: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Interval for scanning inbox for new invoices"
    )
    lookback_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="How many days back to scan for invoices on first run"
    )


class InvoiceSettingsUpdate(BaseModel):
    """Schema for updating invoice settings"""
    enabled: Optional[bool] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    auto_confirm_high_confidence: Optional[bool] = None
    reminder_schedule: Optional[ReminderScheduleSettings] = None
    reminder_tone: Optional[str] = None
    escalation_threshold: Optional[int] = Field(None, ge=2, le=10)
    scan_interval_minutes: Optional[int] = Field(None, ge=1, le=60)
    lookback_days: Optional[int] = Field(None, ge=1, le=365)


# ===== Filter Schemas =====

class InvoiceFilters(BaseModel):
    """Schema for invoice list filters"""
    status: Optional[InvoiceStatus] = None
    client_name: Optional[str] = Field(None, max_length=200)
    client_email: Optional[EmailStr] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    issue_date_from: Optional[date] = None
    issue_date_to: Optional[date] = None
    due_date_from: Optional[date] = None
    due_date_to: Optional[date] = None
    overdue_only: bool = Field(default=False)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    sort_by: str = Field(default="due_date", pattern="^(due_date|issue_date|amount_total|created_at|updated_at)$")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$")


# Update forward references
InvoiceWithReminders.model_rebuild()
