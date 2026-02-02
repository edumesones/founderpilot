# InvoicePilot API Reference

## Base URL
```
/api/v1/invoices
```

## Authentication
All endpoints require JWT authentication via Bearer token in the Authorization header:
```
Authorization: Bearer <token>
```

## Endpoints

### 1. List Invoices
Retrieve a paginated list of invoices with optional filters.

**Endpoint**: `GET /api/v1/invoices`

**Query Parameters**:
| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `status` | string | No | Filter by status | `pending`, `paid`, `overdue` |
| `client_name` | string | No | Filter by client name (partial match) | `Acme Corp` |
| `date_from` | date | No | Filter invoices issued from this date | `2026-01-01` |
| `date_to` | date | No | Filter invoices issued until this date | `2026-02-01` |
| `amount_min` | decimal | No | Minimum invoice amount | `1000.00` |
| `amount_max` | decimal | No | Maximum invoice amount | `5000.00` |
| `page` | integer | No | Page number (default: 1) | `1` |
| `page_size` | integer | No | Items per page (default: 20, max: 100) | `20` |

**Response**: `200 OK`
```json
{
  "items": [
    {
      "id": "uuid-string",
      "tenant_id": "uuid-string",
      "invoice_number": "INV-2026-001",
      "client_name": "Acme Corporation",
      "client_email": "billing@acme.com",
      "amount_total": 5000.00,
      "amount_paid": 2500.00,
      "currency": "USD",
      "issue_date": "2026-01-15",
      "due_date": "2026-02-15",
      "status": "partially_paid",
      "pdf_url": "https://storage.example.com/invoices/...",
      "confidence": 0.95,
      "notes": "Q1 consulting services",
      "days_overdue": 0,
      "reminder_count": 1,
      "last_reminder_sent": "2026-02-10T09:00:00Z",
      "created_at": "2026-01-15T10:30:00Z",
      "updated_at": "2026-02-01T14:20:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or missing authentication token
- `422 Unprocessable Entity`: Invalid query parameters

---

### 2. Get Invoice Details
Retrieve full details of a specific invoice including reminder history.

**Endpoint**: `GET /api/v1/invoices/{invoice_id}`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_id` | UUID | Yes | Invoice identifier |

**Response**: `200 OK`
```json
{
  "id": "uuid-string",
  "tenant_id": "uuid-string",
  "gmail_message_id": "18d4b5c3f2a1b9e7",
  "invoice_number": "INV-2026-001",
  "client_name": "Acme Corporation",
  "client_email": "billing@acme.com",
  "amount_total": 5000.00,
  "amount_paid": 2500.00,
  "currency": "USD",
  "issue_date": "2026-01-15",
  "due_date": "2026-02-15",
  "status": "partially_paid",
  "pdf_url": "https://storage.example.com/invoices/...",
  "confidence": 0.95,
  "notes": "Q1 consulting services",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-02-01T14:20:00Z",
  "reminders": [
    {
      "id": "uuid-string",
      "scheduled_at": "2026-02-10T09:00:00Z",
      "sent_at": "2026-02-10T09:05:32Z",
      "type": "friendly",
      "status": "sent",
      "draft_message": "Hi, just a friendly reminder...",
      "final_message": "Hi, just a friendly reminder...",
      "approved_by": "uuid-string",
      "response_received": false
    }
  ],
  "actions": [
    {
      "id": "uuid-string",
      "action_type": "invoice_detected",
      "actor": "system",
      "details": {"confidence": 0.95},
      "timestamp": "2026-01-15T10:30:00Z"
    },
    {
      "id": "uuid-string",
      "action_type": "invoice_confirmed",
      "actor": "user-uuid",
      "details": {"via": "slack"},
      "timestamp": "2026-01-15T11:00:00Z"
    }
  ]
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Invoice belongs to different tenant
- `404 Not Found`: Invoice not found

---

### 3. Confirm Invoice
Confirm a detected invoice with low confidence.

**Endpoint**: `POST /api/v1/invoices/{invoice_id}/confirm`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_id` | UUID | Yes | Invoice identifier |

**Request Body** (optional):
```json
{
  "corrected_data": {
    "invoice_number": "INV-2026-001",
    "amount_total": 5000.00,
    "client_name": "Acme Corporation"
  },
  "notes": "Confirmed via Slack approval"
}
```

**Response**: `200 OK`
```json
{
  "id": "uuid-string",
  "status": "pending",
  "confidence": 0.95,
  "message": "Invoice confirmed successfully"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Invoice belongs to different tenant
- `404 Not Found`: Invoice not found
- `422 Unprocessable Entity`: Invalid data or invoice already confirmed

---

### 4. Reject Invoice
Reject a detected invoice (false positive).

**Endpoint**: `POST /api/v1/invoices/{invoice_id}/reject`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_id` | UUID | Yes | Invoice identifier |

**Request Body** (optional):
```json
{
  "reason": "Not an invoice - just a quote"
}
```

**Response**: `200 OK`
```json
{
  "id": "uuid-string",
  "status": "rejected",
  "message": "Invoice rejected successfully"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Invoice belongs to different tenant
- `404 Not Found`: Invoice not found

---

### 5. Mark Invoice as Paid
Mark an invoice as fully or partially paid.

**Endpoint**: `POST /api/v1/invoices/{invoice_id}/mark-paid`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_id` | UUID | Yes | Invoice identifier |

**Request Body**:
```json
{
  "amount_paid": 5000.00,
  "payment_date": "2026-02-01",
  "payment_method": "bank_transfer",
  "notes": "Full payment received via wire transfer"
}
```

**Request Body Schema**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount_paid` | decimal | Yes | Amount paid (must be > 0) |
| `payment_date` | date | No | Payment date (defaults to today) |
| `payment_method` | string | No | Payment method (e.g., `bank_transfer`, `card`, `cash`) |
| `notes` | string | No | Additional notes |

**Response**: `200 OK`
```json
{
  "id": "uuid-string",
  "amount_total": 5000.00,
  "amount_paid": 5000.00,
  "status": "paid",
  "message": "Invoice marked as paid successfully"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Invoice belongs to different tenant
- `404 Not Found`: Invoice not found
- `422 Unprocessable Entity`: Invalid payment amount (exceeds total or negative)

---

### 6. List Reminders
Retrieve all reminders for a specific invoice.

**Endpoint**: `GET /api/v1/invoices/{invoice_id}/reminders`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_id` | UUID | Yes | Invoice identifier |

**Response**: `200 OK`
```json
{
  "invoice_id": "uuid-string",
  "reminders": [
    {
      "id": "uuid-string",
      "scheduled_at": "2026-02-12T09:00:00Z",
      "sent_at": "2026-02-12T09:03:21Z",
      "type": "friendly",
      "status": "sent",
      "draft_message": "Hi, just a friendly reminder that invoice INV-2026-001 is due...",
      "final_message": "Hi, just a friendly reminder that invoice INV-2026-001 is due...",
      "approved_by": "user-uuid",
      "response_received": false
    },
    {
      "id": "uuid-string",
      "scheduled_at": "2026-02-18T09:00:00Z",
      "sent_at": null,
      "type": "firm",
      "status": "pending_approval",
      "draft_message": "This is a follow-up regarding invoice INV-2026-001...",
      "final_message": null,
      "approved_by": null,
      "response_received": false
    }
  ],
  "total": 2
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Invoice belongs to different tenant
- `404 Not Found`: Invoice not found

---

### 7. Approve Reminder
Approve a draft reminder to be sent.

**Endpoint**: `POST /api/v1/invoices/{invoice_id}/reminders/{reminder_id}/approve`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_id` | UUID | Yes | Invoice identifier |
| `reminder_id` | UUID | Yes | Reminder identifier |

**Request Body** (optional):
```json
{
  "send_immediately": true
}
```

**Response**: `200 OK`
```json
{
  "id": "uuid-string",
  "status": "approved",
  "message": "Reminder approved and queued for sending"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Invoice belongs to different tenant
- `404 Not Found`: Invoice or reminder not found
- `422 Unprocessable Entity`: Reminder already sent or skipped

---

### 8. Edit Reminder
Edit the draft message of a reminder before approval.

**Endpoint**: `POST /api/v1/invoices/{invoice_id}/reminders/{reminder_id}/edit`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_id` | UUID | Yes | Invoice identifier |
| `reminder_id` | UUID | Yes | Reminder identifier |

**Request Body**:
```json
{
  "message": "Updated reminder message with custom content..."
}
```

**Response**: `200 OK`
```json
{
  "id": "uuid-string",
  "draft_message": "Updated reminder message with custom content...",
  "message": "Reminder updated successfully"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Invoice belongs to different tenant
- `404 Not Found`: Invoice or reminder not found
- `422 Unprocessable Entity`: Reminder already sent or message empty

---

### 9. Skip Reminder
Skip a scheduled reminder (won't be sent).

**Endpoint**: `POST /api/v1/invoices/{invoice_id}/reminders/{reminder_id}/skip`

**Path Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_id` | UUID | Yes | Invoice identifier |
| `reminder_id` | UUID | Yes | Reminder identifier |

**Request Body** (optional):
```json
{
  "reason": "Client requested payment extension"
}
```

**Response**: `200 OK`
```json
{
  "id": "uuid-string",
  "status": "skipped",
  "message": "Reminder skipped successfully"
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid or missing authentication token
- `403 Forbidden`: Invoice belongs to different tenant
- `404 Not Found`: Invoice or reminder not found
- `422 Unprocessable Entity`: Reminder already sent

---

### 10. Get Settings
Retrieve current InvoicePilot settings for the tenant.

**Endpoint**: `GET /api/v1/invoices/settings`

**Response**: `200 OK`
```json
{
  "enabled": true,
  "confidence_threshold": 0.8,
  "reminder_schedule": [-3, 3, 7, 14],
  "reminder_tone": "friendly",
  "escalation_threshold": 3,
  "auto_approve_high_confidence": true,
  "scan_interval_minutes": 5,
  "notification_channels": ["slack", "email"]
}
```

**Field Descriptions**:
| Field | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Whether InvoicePilot is active |
| `confidence_threshold` | float | Minimum confidence for auto-confirmation (0.0-1.0) |
| `reminder_schedule` | array | Days relative to due_date (negative = before, positive = after) |
| `reminder_tone` | string | Tone of reminders: `friendly`, `professional`, `firm` |
| `escalation_threshold` | integer | Number of reminders before escalation |
| `auto_approve_high_confidence` | boolean | Auto-approve invoices with confidence ≥ threshold |
| `scan_interval_minutes` | integer | How often to scan Gmail for new invoices |
| `notification_channels` | array | Where to send notifications: `slack`, `email` |

**Error Responses**:
- `401 Unauthorized`: Invalid or missing authentication token

---

### 11. Update Settings
Update InvoicePilot settings for the tenant.

**Endpoint**: `PUT /api/v1/invoices/settings`

**Request Body**:
```json
{
  "enabled": true,
  "confidence_threshold": 0.85,
  "reminder_schedule": [-5, 0, 3, 7, 14, 21],
  "reminder_tone": "professional",
  "escalation_threshold": 4,
  "auto_approve_high_confidence": false
}
```

**Response**: `200 OK`
```json
{
  "enabled": true,
  "confidence_threshold": 0.85,
  "reminder_schedule": [-5, 0, 3, 7, 14, 21],
  "reminder_tone": "professional",
  "escalation_threshold": 4,
  "auto_approve_high_confidence": false,
  "scan_interval_minutes": 5,
  "notification_channels": ["slack", "email"],
  "message": "Settings updated successfully"
}
```

**Validation Rules**:
- `confidence_threshold`: Must be between 0.0 and 1.0
- `reminder_schedule`: Array of integers, max 10 entries
- `reminder_tone`: One of `friendly`, `professional`, `firm`
- `escalation_threshold`: Must be ≥ 1

**Error Responses**:
- `401 Unauthorized`: Invalid or missing authentication token
- `422 Unprocessable Entity`: Invalid settings values

---

## Data Models

### Invoice Status Values
- `pending`: Awaiting confirmation or payment
- `confirmed`: Invoice confirmed, payment expected
- `partially_paid`: Partial payment received
- `paid`: Fully paid
- `overdue`: Past due date without full payment
- `rejected`: False positive, not an actual invoice

### Reminder Types
- `friendly`: Polite, casual tone (before or near due date)
- `professional`: Formal business tone (shortly after due date)
- `firm`: Strong, urgent tone (significantly overdue)

### Reminder Status
- `scheduled`: Not yet due to be sent
- `pending_approval`: Draft ready, awaiting human approval
- `approved`: Approved, queued for sending
- `sent`: Successfully sent to client
- `skipped`: Manually skipped by user
- `failed`: Send attempt failed

### Action Types
- `invoice_detected`: System detected potential invoice
- `invoice_confirmed`: User confirmed invoice
- `invoice_rejected`: User rejected false positive
- `reminder_scheduled`: Reminder automatically scheduled
- `reminder_approved`: User approved reminder
- `reminder_sent`: Reminder sent to client
- `reminder_skipped`: User skipped reminder
- `payment_recorded`: Payment marked in system
- `escalation`: Escalated to founder for attention

---

## Rate Limiting
All endpoints are subject to rate limiting:
- **Per-user limit**: 100 requests per minute
- **Per-endpoint limit**: Varies by endpoint complexity

When rate limit is exceeded:
- **Response**: `429 Too Many Requests`
- **Headers**: `Retry-After` header with seconds to wait

---

## Webhooks (Future)
InvoicePilot will support webhooks for real-time notifications:
- `invoice.detected` - New invoice detected
- `invoice.confirmed` - Invoice confirmed
- `invoice.paid` - Invoice marked as paid
- `reminder.scheduled` - New reminder scheduled
- `reminder.sent` - Reminder sent to client
- `escalation.created` - Invoice escalated

---

## Common Error Codes

| HTTP Code | Error Code | Description |
|-----------|------------|-------------|
| 400 | `bad_request` | Malformed request syntax |
| 401 | `unauthorized` | Missing or invalid authentication |
| 403 | `forbidden` | Insufficient permissions |
| 404 | `not_found` | Resource not found |
| 422 | `validation_error` | Request validation failed |
| 429 | `rate_limit_exceeded` | Too many requests |
| 500 | `internal_error` | Server error |

---

## Example Workflows

### 1. Manual Invoice Entry
```bash
# 1. Create invoice manually (not implemented in current scope)
POST /api/v1/invoices
{
  "invoice_number": "INV-2026-001",
  "client_name": "Acme Corp",
  "client_email": "billing@acme.com",
  "amount_total": 5000.00,
  "due_date": "2026-03-15"
}

# 2. Schedule reminders automatically
# (happens automatically based on settings)

# 3. Mark as paid when payment received
POST /api/v1/invoices/{id}/mark-paid
{
  "amount_paid": 5000.00
}
```

### 2. Review Detected Invoice
```bash
# 1. List pending invoices
GET /api/v1/invoices?status=pending

# 2. Review invoice details
GET /api/v1/invoices/{id}

# 3. Confirm or reject
POST /api/v1/invoices/{id}/confirm
# or
POST /api/v1/invoices/{id}/reject
```

### 3. Manage Reminders
```bash
# 1. Check scheduled reminders
GET /api/v1/invoices/{id}/reminders

# 2. Edit reminder message
POST /api/v1/invoices/{id}/reminders/{reminder_id}/edit
{
  "message": "Custom message..."
}

# 3. Approve to send
POST /api/v1/invoices/{id}/reminders/{reminder_id}/approve
```

---

## Testing
The API includes interactive documentation:
- **Swagger UI**: Available at `/api/docs` (debug mode only)
- **ReDoc**: Available at `/api/redoc` (debug mode only)
- **OpenAPI JSON**: Available at `/api/openapi.json` (debug mode only)

Use these interfaces to explore and test endpoints interactively.

---

*Generated: 2026-02-02*
*Version: 1.0.0*
*Feature: FEAT-004-invoice-pilot*
