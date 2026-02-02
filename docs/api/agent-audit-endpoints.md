# Agent Audit API Endpoints

## Overview

The Agent Audit API provides comprehensive monitoring and oversight of AI agent actions across InboxPilot, InvoicePilot, and MeetingPilot.

**Base Path:** `/api/v1/audit`

**Authentication:** Bearer token required (JWT)

## Endpoints

### 1. List Audit Logs

```
GET /api/v1/audit
```

Retrieve paginated audit logs with optional filtering.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent` | string | No | Filter by agent type (`inbox_pilot`, `invoice_pilot`, `meeting_pilot`) |
| `from` | datetime (ISO 8601) | No | Start date filter |
| `to` | datetime (ISO 8601) | No | End date filter |
| `min_confidence` | float (0.0-1.0) | No | Minimum confidence level |
| `escalated` | boolean | No | Filter by escalation status |
| `search` | string | No | Full-text search in input/output (max 200 chars) |
| `cursor` | UUID | No | Pagination cursor from previous response |
| `limit` | integer | No | Number of results (1-100, default 50) |

**Response:**
```json
{
  "entries": [
    {
      "id": "uuid",
      "timestamp": "2026-02-02T10:30:00Z",
      "user_id": "uuid",
      "workflow_id": "uuid",
      "agent_type": "inbox_pilot",
      "action": "classify_email",
      "input_summary": "Email subject and preview...",
      "output_summary": "Classification result...",
      "decision": "Archive email",
      "confidence": 0.95,
      "escalated": false,
      "authorized_by": "agent",
      "trace_id": "trace_001",
      "rolled_back": false
    }
  ],
  "next_cursor": "uuid",
  "has_more": true
}
```

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Invalid or missing authentication token
- `422 Unprocessable Entity` - Invalid query parameters

---

### 2. Get Audit Log Detail

```
GET /api/v1/audit/{log_id}
```

Retrieve detailed information for a specific audit log entry, including full metadata.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `log_id` | UUID | Yes | The audit log entry ID |

**Response:**
```json
{
  "id": "uuid",
  "timestamp": "2026-02-02T10:30:00Z",
  "user_id": "uuid",
  "workflow_id": "uuid",
  "agent_type": "inbox_pilot",
  "action": "classify_email",
  "input_summary": "Full email content truncated...",
  "output_summary": "Detailed classification result...",
  "decision": "Archive email - low priority",
  "confidence": 0.95,
  "escalated": false,
  "authorized_by": "agent",
  "trace_id": "trace_001",
  "metadata": {
    "email_id": "123",
    "subject": "Re: Meeting notes",
    "from": "colleague@example.com",
    "classification": "internal_discussion"
  },
  "rolled_back": false,
  "created_at": "2026-02-02T10:30:00Z",
  "updated_at": "2026-02-02T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Invalid or missing authentication token
- `404 Not Found` - Log entry not found or not authorized

---

### 3. Mark Log as Rolled Back

```
POST /api/v1/audit/{log_id}/rollback
```

Mark an audit log entry as rolled back for audit trail purposes.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `log_id` | UUID | Yes | The audit log entry ID |

**Response:**
```json
{
  "success": true,
  "log_id": "uuid",
  "message": "Audit log marked as rolled back"
}
```

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Invalid or missing authentication token
- `404 Not Found` - Log entry not found or not authorized

---

### 4. Get Statistics Summary

```
GET /api/v1/audit/stats/summary
```

Retrieve aggregate statistics about agent actions for the authenticated user.

**Response:**
```json
{
  "total_actions": 1523,
  "by_agent": {
    "inbox_pilot": 1200,
    "invoice_pilot": 250,
    "meeting_pilot": 73
  },
  "escalated_count": 45,
  "escalation_rate": 0.0295,
  "average_confidence": 0.87
}
```

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Invalid or missing authentication token

---

### 5. Export to CSV

```
GET /api/v1/audit/export/csv
```

Export filtered audit logs to CSV format for external analysis.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent` | string | No | Filter by agent type |
| `from` | datetime (ISO 8601) | No | Start date filter |
| `to` | datetime (ISO 8601) | No | End date filter |

**Response:**
- Content-Type: `text/csv`
- File download with filename: `agent_audit_logs_YYYYMMDD.csv`

**CSV Columns:**
- timestamp
- agent_type
- action
- input_summary
- output_summary
- decision
- confidence
- escalated
- authorized_by
- trace_id
- rolled_back

**Status Codes:**
- `200 OK` - Success (CSV file)
- `401 Unauthorized` - Invalid or missing authentication token
- `422 Unprocessable Entity` - Invalid query parameters

---

## Data Models

### Agent Types
- `inbox_pilot` - Email classification and response agent
- `invoice_pilot` - Invoice processing and payment agent
- `meeting_pilot` - Meeting scheduling and reminder agent

### Confidence Levels
- **High** (0.9 - 1.0): Green indicator, high confidence
- **Medium** (0.7 - 0.89): Yellow indicator, moderate confidence
- **Low** (0.0 - 0.69): Red indicator, low confidence

### Authorization Values
- `agent` - Action was automatically authorized by the agent
- `<user_id>` - Action was manually authorized by user

---

## Error Responses

All endpoints return error responses in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common status codes:
- `400 Bad Request` - Malformed request
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - User doesn't have permission
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

---

## Usage Examples

### Filter high-confidence logs
```bash
curl -X GET "https://api.example.com/api/v1/audit?min_confidence=0.9" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get escalated logs
```bash
curl -X GET "https://api.example.com/api/v1/audit?escalated=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Search logs
```bash
curl -X GET "https://api.example.com/api/v1/audit?search=invoice" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Export to CSV
```bash
curl -X GET "https://api.example.com/api/v1/audit/export/csv?from=2026-01-01&to=2026-01-31" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o audit_logs.csv
```

---

## Rate Limiting

- Standard rate limits apply: 100 requests per minute per user
- CSV export: 10 requests per hour per user

---

## Interactive Documentation

For interactive API documentation with try-it-out features:
- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc

---

*Last updated: 2026-02-02*
