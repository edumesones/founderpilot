# InvoicePilot API Reference

## Overview

InvoicePilot provides automated invoice detection, tracking, and payment reminder capabilities through a RESTful API.

## Base URL

```
https://api.founderpilot.com/api/v1/invoices
```

All endpoints require authentication via JWT token in the `Authorization: Bearer <token>` header.

---

## Endpoints

### Invoice Management

#### List Invoices

```http
GET /api/v1/invoices
```

Retrieve a paginated list of invoices with optional filters.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status: `detected`, `pending`, `overdue`, `partial`, `paid`, `rejected` |
| `client_name` | string | Filter by client name (partial match) |
| `client_email` | string | Filter by exact client email |
| `currency` | string | Filter by ISO 4217 currency code (USD, EUR, GBP) |
| `min_amount` | float | Minimum invoice amount |
| `max_amount` | float | Maximum invoice amount |
| `issue_date_from` | date | Filter by issue date from (YYYY-MM-DD) |
| `issue_date_to` | date | Filter by issue date to (YYYY-MM-DD) |
| `due_date_from` | date | Filter by due date from (YYYY-MM-DD) |
| `due_date_to` | date | Filter by due date to (YYYY-MM-DD) |
| `overdue_only` | boolean | Show only overdue invoices (default: false) |
| `page` | integer | Page number (default: 1, min: 1) |
| `page_size` | integer | Items per page (default: 50, min: 1, max: 100) |
| `sort_by` | string | Sort field (default: `due_date`) |
| `sort_order` | string | Sort order: `asc` or `desc` (default: `asc`) |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "gmail_message_id": "string",
      "invoice_number": "INV-2026-001",
      "client_name": "Acme Corp",
      "client_email": "billing@acmecorp.com",
      "amount_total": 5000.00,
      "amount_paid": 0.00,
      "currency": "USD",
      "issue_date": "2026-01-15",
      "due_date": "2026-02-15",
      "status": "pending",
      "confidence": 0.95,
      "pdf_url": "/storage/pdfs/invoice-001.pdf",
      "notes": "Website redesign project",
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-01-15T10:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 50,
  "pages": 1
}
```

---

#### Get Invoice Details

```http
GET /api/v1/invoices/{invoice_id}
```

Retrieve detailed information about a specific invoice, including reminders.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_id` | UUID | The invoice ID |

**Response:**

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "gmail_message_id": "string",
  "invoice_number": "INV-2026-001",
  "client_name": "Acme Corp",
  "client_email": "billing@acmecorp.com",
  "amount_total": 5000.00,
  "amount_paid": 0.00,
  "currency": "USD",
  "issue_date": "2026-01-15",
  "due_date": "2026-02-15",
  "status": "pending",
  "confidence": 0.95,
  "pdf_url": "/storage/pdfs/invoice-001.pdf",
  "notes": "Website redesign project",
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-01-15T10:00:00Z",
  "reminders": [
    {
      "id": "uuid",
      "invoice_id": "uuid",
      "scheduled_at": "2026-02-12T09:00:00Z",
      "sent_at": null,
      "type": "pre_due",
      "status": "pending",
      "draft_message": "Gentle reminder...",
      "final_message": null,
      "approved_by": null,
      "response_received": false,
      "created_at": "2026-02-10T10:00:00Z",
      "updated_at": "2026-02-10T10:00:00Z"
    }
  ]
}
```

**Errors:**

- `404 Not Found` - Invoice not found or access denied

---

#### Confirm Invoice

```http
POST /api/v1/invoices/{invoice_id}/confirm
```

Confirm a detected invoice (for low confidence detections).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_id` | UUID | The invoice ID |

**Request Body:**

```json
{
  "invoice_number": "INV-2026-001",
  "client_name": "Acme Corp",
  "client_email": "billing@acmecorp.com",
  "amount_total": 5000.00,
  "currency": "USD",
  "issue_date": "2026-01-15",
  "due_date": "2026-02-15",
  "notes": "Confirmed details"
}
```

**Response:**

```json
{
  "id": "uuid",
  "status": "pending",
  "message": "Invoice confirmed successfully"
}
```

**Errors:**

- `404 Not Found` - Invoice not found
- `422 Unprocessable Entity` - Invoice cannot be confirmed (not in detected status)

---

#### Reject Invoice

```http
POST /api/v1/invoices/{invoice_id}/reject
```

Reject a detected invoice (false positive).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_id` | UUID | The invoice ID |

**Request Body:**

```json
{
  "reason": "Not an invoice, just a quote"
}
```

**Response:**

```json
{
  "id": "uuid",
  "status": "rejected",
  "message": "Invoice rejected successfully"
}
```

**Errors:**

- `404 Not Found` - Invoice not found
- `422 Unprocessable Entity` - Invoice cannot be rejected

---

#### Mark Invoice as Paid

```http
POST /api/v1/invoices/{invoice_id}/mark-paid
```

Mark an invoice as fully or partially paid.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_id` | UUID | The invoice ID |

**Request Body:**

```json
{
  "amount_paid": 5000.00,
  "payment_date": "2026-02-10",
  "payment_method": "bank_transfer",
  "notes": "Payment received via wire transfer"
}
```

**Response:**

```json
{
  "id": "uuid",
  "status": "paid",
  "amount_paid": 5000.00,
  "message": "Invoice marked as paid"
}
```

**Errors:**

- `404 Not Found` - Invoice not found
- `422 Unprocessable Entity` - Invalid payment amount or date

---

### Reminder Management

#### List Reminders

```http
GET /api/v1/invoices/{invoice_id}/reminders
```

Retrieve all reminders for a specific invoice.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_id` | UUID | The invoice ID |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "invoice_id": "uuid",
      "scheduled_at": "2026-02-12T09:00:00Z",
      "sent_at": null,
      "type": "pre_due",
      "status": "pending",
      "draft_message": "Gentle reminder...",
      "final_message": null,
      "approved_by": null,
      "response_received": false,
      "created_at": "2026-02-10T10:00:00Z",
      "updated_at": "2026-02-10T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

#### Approve Reminder

```http
POST /api/v1/invoices/{invoice_id}/reminders/{reminder_id}/approve
```

Approve a pending reminder to be sent.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_id` | UUID | The invoice ID |
| `reminder_id` | UUID | The reminder ID |

**Request Body:**

```json
{
  "message": "Hi team, just following up..."
}
```

**Response:**

```json
{
  "id": "uuid",
  "status": "approved",
  "message": "Reminder approved and will be sent"
}
```

---

#### Edit Reminder

```http
POST /api/v1/invoices/{invoice_id}/reminders/{reminder_id}/edit
```

Edit the message of a pending reminder.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_id` | UUID | The invoice ID |
| `reminder_id` | UUID | The reminder ID |

**Request Body:**

```json
{
  "message": "Updated reminder message..."
}
```

**Response:**

```json
{
  "id": "uuid",
  "status": "pending",
  "final_message": "Updated reminder message...",
  "message": "Reminder message updated"
}
```

---

#### Skip Reminder

```http
POST /api/v1/invoices/{invoice_id}/reminders/{reminder_id}/skip
```

Skip sending a specific reminder.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_id` | UUID | The invoice ID |
| `reminder_id` | UUID | The reminder ID |

**Request Body:**

```json
{
  "reason": "Client confirmed payment via phone"
}
```

**Response:**

```json
{
  "id": "uuid",
  "status": "skipped",
  "message": "Reminder skipped"
}
```

---

### Settings

#### Get Settings

```http
GET /api/v1/invoices/settings
```

Retrieve InvoicePilot settings for the current tenant.

**Response:**

```json
{
  "enabled": true,
  "confidence_threshold": 0.8,
  "reminder_schedule": [-3, 3, 7, 14],
  "reminder_tone": "professional",
  "auto_approve_high_confidence": true,
  "escalation_threshold": 3,
  "default_currency": "USD"
}
```

---

#### Update Settings

```http
PUT /api/v1/invoices/settings
```

Update InvoicePilot settings.

**Request Body:**

```json
{
  "enabled": true,
  "confidence_threshold": 0.85,
  "reminder_schedule": [-3, 3, 7, 14, 21],
  "reminder_tone": "friendly",
  "auto_approve_high_confidence": false,
  "escalation_threshold": 4,
  "default_currency": "EUR"
}
```

**Response:**

```json
{
  "message": "Settings updated successfully",
  "settings": {
    "enabled": true,
    "confidence_threshold": 0.85,
    "reminder_schedule": [-3, 3, 7, 14, 21],
    "reminder_tone": "friendly",
    "auto_approve_high_confidence": false,
    "escalation_threshold": 4,
    "default_currency": "EUR"
  }
}
```

---

## Data Models

### Invoice Status

| Status | Description |
|--------|-------------|
| `detected` | Invoice detected but not confirmed |
| `pending` | Invoice confirmed, payment pending |
| `overdue` | Payment past due date |
| `partial` | Partially paid |
| `paid` | Fully paid |
| `rejected` | False positive, not an invoice |

### Reminder Types

| Type | Description |
|------|-------------|
| `pre_due` | Sent 3 days before due date |
| `post_due_3d` | Sent 3 days after due date |
| `post_due_7d` | Sent 7 days after due date |
| `post_due_14d` | Sent 14 days after due date |
| `custom` | Manually scheduled reminder |

### Reminder Status

| Status | Description |
|--------|-------------|
| `pending` | Waiting for approval |
| `approved` | Approved, queued to send |
| `sent` | Successfully sent |
| `skipped` | Manually skipped |
| `rejected` | Rejected by user |
| `failed` | Failed to send |

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request |
| `401` | Unauthorized |
| `403` | Forbidden (cross-tenant access) |
| `404` | Not Found |
| `409` | Conflict (duplicate data) |
| `422` | Unprocessable Entity (validation error) |
| `429` | Too Many Requests (rate limited) |
| `500` | Internal Server Error |

---

## Rate Limits

- **Standard**: 100 requests per minute per tenant
- **Burst**: 20 requests per second per tenant

Rate limit headers are included in all responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

---

## Webhooks

InvoicePilot can send webhook notifications for key events:

### Events

- `invoice.detected` - New invoice detected
- `invoice.confirmed` - Invoice confirmed by user
- `invoice.paid` - Invoice marked as paid
- `reminder.sent` - Reminder sent to client
- `invoice.overdue` - Invoice became overdue
- `escalation.triggered` - Problem pattern detected

### Webhook Payload

```json
{
  "event": "invoice.detected",
  "timestamp": "2026-02-10T10:00:00Z",
  "data": {
    "invoice_id": "uuid",
    "tenant_id": "uuid",
    "invoice_number": "INV-2026-001",
    "client_name": "Acme Corp",
    "amount_total": 5000.00,
    "currency": "USD",
    "confidence": 0.95
  }
}
```

---

## SDK Examples

### Python

```python
from founderpilot import InvoicePilotClient

client = InvoicePilotClient(api_key="your-api-key")

# List invoices
invoices = client.invoices.list(status="overdue", page_size=10)

# Get invoice details
invoice = client.invoices.get("invoice-uuid")

# Mark as paid
client.invoices.mark_paid(
    "invoice-uuid",
    amount_paid=5000.00,
    payment_date="2026-02-10"
)

# Approve reminder
client.reminders.approve(
    "invoice-uuid",
    "reminder-uuid",
    message="Custom message..."
)
```

### JavaScript/TypeScript

```typescript
import { InvoicePilotClient } from '@founderpilot/sdk';

const client = new InvoicePilotClient({ apiKey: 'your-api-key' });

// List invoices
const invoices = await client.invoices.list({
  status: 'overdue',
  pageSize: 10
});

// Get invoice details
const invoice = await client.invoices.get('invoice-uuid');

// Mark as paid
await client.invoices.markPaid('invoice-uuid', {
  amountPaid: 5000.00,
  paymentDate: '2026-02-10'
});

// Approve reminder
await client.reminders.approve('invoice-uuid', 'reminder-uuid', {
  message: 'Custom message...'
});
```

---

## Support

For API support, contact: api-support@founderpilot.com

For bugs or feature requests, file an issue at: https://github.com/founderpilot/founderpilot/issues
