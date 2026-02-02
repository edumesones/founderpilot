# FEAT-004: InvoicePilot - Implementation Tasks

## Pre-Implementation Checklist
- [x] spec.md complete and approved
- [ ] design.md complete and approved
- [x] Branch created: `feat/FEAT-004`
- [x] status.md updated

---

## Phase 1: Data Models & Migrations (Backend Foundation)

- [x] **T1.1**: Create Invoice model in `src/models/invoice.py`
  - Schema: id, tenant_id, gmail_message_id, invoice_number, client_name, client_email
  - Fields: amount_total, amount_paid, currency, issue_date, due_date, status
  - Fields: pdf_url, confidence, notes, created_at, updated_at
  - Relationships: to InvoiceReminder, InvoiceAction

- [x] **T1.2**: Create InvoiceReminder model in `src/models/invoice.py`
  - Schema: id, invoice_id, scheduled_at, sent_at, type, status
  - Fields: draft_message, final_message, approved_by, response_received
  - Relationship: FK to Invoice

- [x] **T1.3**: Create InvoiceAction model in `src/models/invoice.py`
  - Schema: id, invoice_id, workflow_id, action_type, actor, details, timestamp
  - For audit trail

- [x] **T1.4**: Create Alembic migration for Invoice tables
  - Tables: invoices, invoice_reminders, invoice_actions
  - Indexes: tenant_id, status, due_date, gmail_message_id (unique per tenant)

---

## Phase 2: LangGraph Agent (Core Intelligence)

- [x] **T2.1**: Create InvoicePilotAgent skeleton in `src/agents/invoice_pilot.py`
  - StateGraph setup
  - State classes: InvoiceState, DetectionState, ReminderState

- [x] **T2.2**: Implement detection flow nodes
  - scan_inbox: Fetch sent emails from Gmail API
  - detect_invoice: LLM-based invoice detection
  - extract_data: LLM multimodal extraction from PDF

- [x] **T2.3**: Implement confirmation flow
  - needs_confirmation: Check if confidence < 80%
  - confirm_invoice: Handle human approval via Slack
  - store_invoice: Save to DB with audit log

- [x] **T2.4**: Implement reminder flow nodes
  - check_reminders_due: Daily check for due reminders
  - draft_reminder: Generate reminder message with LLM
  - await_approval: Slack approval for reminder
  - send_reminder: Send via Gmail API
  - log_action: Audit trail

- [x] **T2.5**: Implement escalation flow
  - detect_problem_pattern: Check for 3+ reminders without payment
  - escalate_to_slack: Notify founder of morose client

- [x] **T2.6**: Create LLM prompt templates
  - Invoice detection prompt
  - Data extraction prompt (with structured output)
  - Reminder draft prompt (customizable tone)

---

## Phase 3: Service Layer (Business Logic)

- [x] **T3.1**: Create InvoiceService in `src/services/invoice_service.py`
  - CRUD operations: create, get, list, update, delete
  - Filters: by status, date range, client, amount
  - Mark as paid (total or partial)
  - Confirm/reject detected invoice

- [x] **T3.2**: Create ReminderService in `src/services/reminder_service.py`
  - Schedule reminders based on due_date and config
  - Approve/edit/skip reminder
  - Track reminder history per invoice

- [x] **T3.3**: Create InvoiceDetectionService in `src/services/invoice_detection_service.py`
  - Scan Gmail for invoice emails
  - Call LLM for detection and extraction
  - Handle PDF parsing
  - Confidence scoring

- [x] **T3.4**: Create validation logic
  - Validate invoice data (amount > 0, dates valid, etc)
  - Validate currency codes (ISO 4217)
  - Sanitize LLM inputs/outputs

---

## Phase 4: API Endpoints

- [x] **T4.1**: Create invoice router in `src/api/v1/invoices.py`
  - GET /api/v1/invoices (list with filters)
  - GET /api/v1/invoices/:id (details + reminders)
  - POST /api/v1/invoices/:id/confirm
  - POST /api/v1/invoices/:id/reject
  - POST /api/v1/invoices/:id/mark-paid

- [x] **T4.2**: Create reminder endpoints
  - GET /api/v1/invoices/:id/reminders
  - POST /api/v1/invoices/:id/reminders/:reminder_id/approve
  - POST /api/v1/invoices/:id/reminders/:reminder_id/edit
  - POST /api/v1/invoices/:id/reminders/:reminder_id/skip

- [x] **T4.3**: Create settings endpoints
  - GET /api/v1/invoices/settings
  - PUT /api/v1/invoices/settings (reminder schedule, tone)

- [x] **T4.4**: Create Pydantic schemas in `src/schemas/invoice.py`
  - InvoiceCreate, InvoiceResponse, InvoiceList
  - ReminderCreate, ReminderResponse
  - InvoiceSettings

- [x] **T4.5**: Add error handling and validation
  - 404 for not found
  - 422 for validation errors
  - 403 for cross-tenant access
  - Rate limiting

---

## Phase 5: Celery Tasks (Automation)

- [x] **T5.1**: Create Celery task for invoice scanning
  - Task: scan_invoices_for_all_tenants (every 5 min)
  - Call InvoicePilotAgent.scan_inbox() per tenant

- [x] **T5.2**: Create Celery task for reminders
  - Task: check_invoice_reminders (daily at 9am)
  - Call InvoicePilotAgent.check_reminders_due() per tenant

- [x] **T5.3**: Create Celery task for escalation
  - Task: check_problem_patterns (daily at 10am)
  - Call InvoicePilotAgent.detect_problem_pattern() per tenant

- [x] **T5.4**: Configure Celery beat schedule
  - Add tasks to celeryconfig.py

---

## Phase 6: Slack Integration

- [x] **T6.1**: Create Slack notification templates
  - Low confidence invoice detected
  - Reminder ready for approval
  - Problem pattern escalation

- [x] **T6.2**: Create Slack action handlers
  - Handle confirm/reject invoice
  - Handle approve/edit/skip reminder
  - Handle escalation actions

- [x] **T6.3**: Add Slack message formatting
  - Rich formatting with blocks
  - Inline buttons for actions
  - Context information (client, amount, days overdue)

---

## Phase 7: Gmail Integration

- [x] **T7.1**: Create Gmail inbox scanner
  - Fetch sent emails with attachments
  - Filter by date (last 30 days for initial scan)
  - Extract PDF attachments

- [x] **T7.2**: Create Gmail reminder sender
  - Send reminder email to client
  - Track sent message ID
  - Handle bounces and errors

- [x] **T7.3**: Add PDF parsing utility
  - Extract text from PDF
  - Convert to image for multimodal LLM
  - Handle corrupted/unreadable PDFs

---

## Phase 8: Testing

- [x] **T8.1**: Unit tests for models
  - Test Invoice, InvoiceReminder, InvoiceAction models
  - Test status transitions
  - Test relationships

- [x] **T8.2**: Unit tests for services
  - Test InvoiceService CRUD
  - Test ReminderService scheduling
  - Test InvoiceDetectionService logic
  - Mock LLM calls

- [ ] **T8.3**: Integration tests for API
  - Test all endpoints
  - Test authentication and authorization
  - Test validation and error handling

- [ ] **T8.4**: Integration tests for agent
  - Test detection flow (mock Gmail)
  - Test reminder flow (mock Slack)
  - Test escalation flow
  - Mock LLM responses

- [ ] **T8.5**: E2E test for main flow
  - Send invoice email → Detect → Extract → Confirm → Schedule → Send reminder → Mark paid
  - Use test Gmail account and test Slack workspace

---

## Phase 9: Configuration & DevOps

- [ ] **T9.1**: Add environment variables
  - INVOICE_PILOT_ENABLED (feature flag)
  - INVOICE_CONFIDENCE_THRESHOLD (default 0.8)
  - INVOICE_REMINDER_SCHEDULE (default: -3,3,7,14)
  - INVOICE_SCAN_INTERVAL (default: 5min)
  - Add to .env.example

- [ ] **T9.2**: Update Docker configuration
  - Add Celery beat container if not exists
  - Add volumes for PDF storage

- [ ] **T9.3**: Run migrations
  - Test migration up/down
  - Seed test data for development

---

## Phase 10: Documentation

- [x] **T10.1**: Update main router to include invoice routes
  - Import and mount invoice router in src/api/main.py

- [ ] **T10.2**: Add docstrings
  - All agent nodes
  - All service methods
  - All API endpoints

- [ ] **T10.3**: Update API documentation
  - Add InvoicePilot endpoints to OpenAPI spec
  - Add examples for request/response

- [ ] **T10.4**: Create user guide
  - How to enable InvoicePilot
  - How to configure reminder schedule
  - How to handle Slack notifications
  - How to mark invoices as paid

---

## Progress Tracking

### Status Legend
| Symbol | Meaning |
|--------|---------|
| `- [ ]` | ⬜ Pending |
| `- [🟡]` | 🟡 In Progress |
| `- [x]` | ✅ Completed |
| `- [🔴]` | 🔴 Blocked |
| `- [⏭️]` | ⏭️ Skipped |

### Current Progress

| Phase | Done | Total | % |
|-------|------|-------|---|
| Phase 1: Models & Migrations | 4 | 4 | 100% |
| Phase 2: LangGraph Agent | 6 | 6 | 100% |
| Phase 3: Service Layer | 4 | 4 | 100% |
| Phase 4: API Endpoints | 5 | 5 | 100% |
| Phase 5: Celery Tasks | 4 | 4 | 100% |
| Phase 6: Slack Integration | 3 | 3 | 100% |
| Phase 7: Gmail Integration | 3 | 3 | 100% |
| Phase 8: Testing | 0 | 5 | 0% |
| Phase 9: Config & DevOps | 0 | 3 | 0% |
| Phase 10: Documentation | 1 | 4 | 25% |
| **TOTAL** | **30** | **41** | **73%** |

---

## Implementation Strategy

### Priority Order (MVP)
1. **Phase 1**: Models & Migrations (foundation)
2. **Phase 3**: Service Layer (business logic)
3. **Phase 4**: API Endpoints (user interface)
4. **Phase 2**: LangGraph Agent (can be stubbed initially)
5. **Phase 7**: Gmail Integration (critical for detection)
6. **Phase 5**: Celery Tasks (automation)
7. **Phase 6**: Slack Integration (notifications)
8. **Phase 8**: Testing (quality assurance)
9. **Phase 9**: Config & DevOps (deployment)
10. **Phase 10**: Documentation (polish)

### Can Be Parallelized
- Phase 1 + Phase 4 (schemas)
- Phase 3 + Phase 7 (services + integrations)
- Phase 5 + Phase 6 (Celery + Slack)
- Phase 8 (all tests can be written in parallel)

### Critical Path
Phase 1 → Phase 3 → Phase 4 → Phase 7 → Phase 2 → Phase 5

---

## Notes

### Assumptions
- Gmail API integration already exists from FEAT-003 (InboxPilot)
- Slack integration framework exists from FEAT-006
- LLM provider infrastructure exists (ADR-007)
- LangGraph setup exists (ADR-001)
- Tenant isolation working properly

### Dependencies to Verify
- [ ] Verify Gmail API scopes include sending emails
- [ ] Verify Slack app has required permissions
- [ ] Verify LLM provider supports structured output
- [ ] Verify S3 or file storage for PDFs

### Risks
- LLM extraction accuracy (mitigated by confidence threshold)
- Gmail API rate limits (mitigated by batch processing)
- PDF parsing failures (mitigated by escalation to human)
- Reminder email deliverability (mitigated by bounce handling)

---

*Created: 2026-02-02*
*Last updated: 2026-02-02*
