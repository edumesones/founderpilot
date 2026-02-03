# InvoicePilot User Guide

## What is InvoicePilot?

InvoicePilot is an AI-powered invoice management assistant that automatically:
- 📧 Detects invoices in your sent emails
- 📊 Extracts key information (amount, due date, client)
- 📅 Schedules payment reminders
- 🔔 Notifies you via Slack for approvals
- 📤 Sends reminders to clients automatically
- 🚨 Escalates overdue invoices

**Think of it as your virtual billing assistant** - handling the tedious work of tracking invoices and following up with clients, so you can focus on your business.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [How InvoicePilot Works](#how-invoicepilot-works)
3. [Configuration](#configuration)
4. [Daily Workflow](#daily-workflow)
5. [Managing Invoices](#managing-invoices)
6. [Managing Reminders](#managing-reminders)
7. [Slack Integration](#slack-integration)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

---

## Getting Started

### Prerequisites
Before using InvoicePilot, ensure you have:
- ✅ Connected your Gmail account to FounderPilot
- ✅ Connected your Slack workspace to FounderPilot
- ✅ Completed onboarding and tenant setup

### Enable InvoicePilot

**Option 1: Via API**
```bash
curl -X PUT https://api.founderpilot.com/api/v1/invoices/settings \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

**Option 2: Via Dashboard** *(Coming Soon)*
1. Navigate to Settings → InvoicePilot
2. Toggle "Enable InvoicePilot" to ON
3. Click "Save Changes"

### Initial Setup (Recommended)

Configure your preferences:

```bash
curl -X PUT https://api.founderpilot.com/api/v1/invoices/settings \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "confidence_threshold": 0.8,
    "reminder_schedule": [-3, 3, 7, 14],
    "reminder_tone": "friendly",
    "escalation_threshold": 3,
    "auto_approve_high_confidence": true
  }'
```

**What these settings mean:**
- `confidence_threshold: 0.8` - Auto-confirm invoices with 80%+ confidence
- `reminder_schedule: [-3, 3, 7, 14]` - Send reminders 3 days before due date, then 3, 7, and 14 days after
- `reminder_tone: "friendly"` - Use a polite, casual tone in reminders
- `escalation_threshold: 3` - Escalate to you after 3 unanswered reminders
- `auto_approve_high_confidence: true` - Skip manual approval for high-confidence detections

---

## How InvoicePilot Works

### The Invoice Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. DETECTION                                                   │
│     Every 5 minutes, scan Gmail sent folder for invoices       │
│     ↓                                                           │
│  2. EXTRACTION                                                  │
│     AI extracts: client, amount, due date, invoice number      │
│     ↓                                                           │
│  3. CONFIRMATION (if confidence < 80%)                          │
│     Slack notification → Human approves/rejects                │
│     ↓                                                           │
│  4. STORAGE                                                     │
│     Invoice saved to database, reminders scheduled             │
│     ↓                                                           │
│  5. REMINDERS                                                   │
│     Draft reminders → Slack approval → Send to client          │
│     ↓                                                           │
│  6. ESCALATION (after 3+ reminders)                            │
│     Notify founder of problem client                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Detection Criteria

InvoicePilot considers an email to be an invoice if it:
- ✅ Is in your Gmail **sent** folder
- ✅ Has a PDF attachment
- ✅ Contains invoice-related keywords (invoice, bill, payment due, etc.)
- ✅ Includes monetary amounts and dates
- ✅ Has a recipient email address

### Confidence Scoring

Each detected invoice gets a confidence score (0-100%):
- **90-100%**: Very high confidence - clear invoice with all fields
- **80-89%**: High confidence - likely correct, minor ambiguity
- **60-79%**: Medium confidence - needs review
- **Below 60%**: Low confidence - likely false positive

**Default behavior:**
- ≥80% confidence → Auto-confirm (if enabled)
- <80% confidence → Request Slack approval

---

## Configuration

### Reminder Schedule

The `reminder_schedule` defines when reminders are sent **relative to the due date**:

**Example schedules:**

```json
// Conservative (early reminder + gentle follow-ups)
[-5, 3, 10]
// Sends: 5 days before due, 3 days after, 10 days after

// Standard (balanced)
[-3, 3, 7, 14]
// Sends: 3 days before due, then 3, 7, 14 days after

// Aggressive (frequent follow-ups)
[0, 2, 5, 7, 10, 14, 21]
// Sends: on due date, then every few days

// Late-only (no early reminders)
[3, 7, 14, 21, 28]
// Sends: only after invoice is overdue
```

**Tips:**
- Negative numbers = days **before** due date
- Positive numbers = days **after** due date
- Zero = **on** the due date
- Maximum 10 reminders per invoice

### Reminder Tone

Choose the tone for reminder messages:

| Tone | When to Use | Example |
|------|-------------|---------|
| `friendly` | Long-term clients, small amounts | "Hi! Just a friendly reminder about invoice INV-001..." |
| `professional` | Corporate clients, formal relationships | "This is a reminder that invoice INV-001 is now overdue..." |
| `firm` | Significantly overdue, unresponsive clients | "URGENT: Invoice INV-001 is 14 days overdue. Immediate payment required..." |

**Pro tip:** Start with `friendly` and let escalation handle the tone shift automatically.

### Confidence Threshold

Controls when manual approval is required:

```json
{
  "confidence_threshold": 0.8,  // 80%
  "auto_approve_high_confidence": true
}
```

**Recommended values:**
- `0.9` (90%) - Very cautious, more approvals needed
- `0.8` (80%) - **Recommended** - good balance
- `0.7` (70%) - Aggressive, fewer approvals (higher false positive risk)

### Scan Interval

How often InvoicePilot checks for new invoices:

```json
{
  "scan_interval_minutes": 5  // Check every 5 minutes
}
```

**Note:** This is configured at the system level and typically doesn't need changing.

---

## Daily Workflow

### Morning Routine (9:00 AM)

**What happens automatically:**
1. InvoicePilot checks all invoices for reminders due today
2. Generates draft reminder messages using AI
3. Sends Slack notifications for your approval

**Your action:**
1. Check Slack for reminder approvals
2. Review draft messages
3. Click "Approve", "Edit", or "Skip"

### Throughout the Day

**Invoice Detections:**
- When new invoice detected with low confidence → Slack notification
- Review invoice details in Slack message
- Click "Confirm" or "Reject"

**Payment Received:**
- When client pays → Mark invoice as paid via API or dashboard
- Reminders automatically stop

### End of Day (Optional)

Check dashboard for:
- 📊 Invoices due this week
- 🔴 Overdue invoices
- 📧 Reminders sent today

---

## Managing Invoices

### View All Invoices

```bash
# List all invoices
curl -X GET "https://api.founderpilot.com/api/v1/invoices" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by status
curl -X GET "https://api.founderpilot.com/api/v1/invoices?status=overdue" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by client
curl -X GET "https://api.founderpilot.com/api/v1/invoices?client_name=Acme" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filter by date range
curl -X GET "https://api.founderpilot.com/api/v1/invoices?date_from=2026-01-01&date_to=2026-01-31" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### View Invoice Details

```bash
curl -X GET "https://api.founderpilot.com/api/v1/invoices/{invoice_id}" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response includes:**
- Invoice details (amount, due date, client)
- Reminder history (scheduled, sent, skipped)
- Action log (detection, confirmations, payments)
- PDF URL

### Confirm a Detected Invoice

```bash
# Simple confirmation
curl -X POST "https://api.founderpilot.com/api/v1/invoices/{invoice_id}/confirm" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Confirm with corrections
curl -X POST "https://api.founderpilot.com/api/v1/invoices/{invoice_id}/confirm" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "corrected_data": {
      "amount_total": 5500.00,
      "client_name": "Acme Corporation Inc"
    }
  }'
```

### Reject a False Positive

```bash
curl -X POST "https://api.founderpilot.com/api/v1/invoices/{invoice_id}/reject" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "This is a quote, not an invoice"
  }'
```

### Mark Invoice as Paid

```bash
# Full payment
curl -X POST "https://api.founderpilot.com/api/v1/invoices/{invoice_id}/mark-paid" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_paid": 5000.00,
    "payment_date": "2026-02-01",
    "payment_method": "bank_transfer"
  }'

# Partial payment
curl -X POST "https://api.founderpilot.com/api/v1/invoices/{invoice_id}/mark-paid" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_paid": 2500.00,
    "notes": "First installment of $2,500"
  }'
```

**What happens:**
- Invoice status updates to `paid` (or `partially_paid`)
- Future reminders are cancelled
- Action logged in audit trail

---

## Managing Reminders

### View Scheduled Reminders

```bash
curl -X GET "https://api.founderpilot.com/api/v1/invoices/{invoice_id}/reminders" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Approve a Reminder

```bash
# Standard approval (sends at scheduled time)
curl -X POST "https://api.founderpilot.com/api/v1/invoices/{invoice_id}/reminders/{reminder_id}/approve" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Approve and send immediately
curl -X POST "https://api.founderpilot.com/api/v1/invoices/{invoice_id}/reminders/{reminder_id}/approve" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"send_immediately": true}'
```

### Edit a Reminder Message

```bash
curl -X POST "https://api.founderpilot.com/api/v1/invoices/{invoice_id}/reminders/{reminder_id}/edit" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hi Sarah,\n\nHope all is well! Just a quick reminder that invoice INV-2026-001 for $5,000 is due on Feb 15th.\n\nLet me know if you have any questions!\n\nBest,\nJohn"
  }'
```

**After editing:**
- Reminder remains in `pending_approval` status
- You'll need to approve it separately

### Skip a Reminder

```bash
curl -X POST "https://api.founderpilot.com/api/v1/invoices/{invoice_id}/reminders/{reminder_id}/skip" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Client requested payment extension until March 1st"
  }'
```

**When to skip:**
- Client requested extension
- Payment confirmed but not yet cleared
- Personal relationship makes reminder inappropriate
- You're handling it through other channels

---

## Slack Integration

### Notification Types

InvoicePilot sends 3 types of Slack notifications:

#### 1. Invoice Detected (Low Confidence)

```
🧾 New Invoice Detected (Needs Review)

Invoice: INV-2026-001
Client: Acme Corporation
Amount: $5,000.00 USD
Due Date: Feb 15, 2026
Confidence: 72%

[Confirm] [Reject] [View Details]
```

**Actions:**
- **Confirm** - Accept the invoice as correct
- **Reject** - Mark as false positive (not an invoice)
- **View Details** - See full invoice info and PDF

#### 2. Reminder Ready for Approval

```
📧 Reminder Ready to Send

Invoice: INV-2026-001 (Acme Corporation)
Amount: $5,000.00 USD | Due: Feb 15, 2026
Days Overdue: 3

Draft Message:
"Hi, just a friendly reminder that invoice INV-2026-001
for $5,000 is now 3 days overdue. Please let me know if
you have any questions. Thanks!"

[Approve] [Edit] [Skip]
```

**Actions:**
- **Approve** - Send the reminder as drafted
- **Edit** - Modify the message before sending
- **Skip** - Don't send this reminder

#### 3. Problem Pattern Detected

```
🚨 Invoice Escalation: Repeated Non-Payment

Invoice: INV-2026-001 (Acme Corporation)
Amount: $5,000.00 USD | Due: Jan 15, 2026
Days Overdue: 18

📊 History:
✓ 3 reminders sent (no response)
✗ 0 payments received

Action Needed:
Consider personal follow-up or formal collection process.

[View Invoice] [Mark as Paid] [Contact Client]
```

**When this happens:**
- 3+ reminders sent without response
- Invoice significantly overdue
- Requires personal intervention

### Customizing Notifications

**Change Slack channel:**
1. Invite `@FounderPilot` bot to your desired channel
2. In channel: `/founderpilot config invoice-channel`
3. Follow prompts to set as default

**Mute notifications temporarily:**
```bash
# Via API (disable for 7 days)
curl -X PUT "https://api.founderpilot.com/api/v1/invoices/settings" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notification_channels": ["email"]}'
```

---

## Best Practices

### 1. Set Realistic Reminder Schedules

**Don't:**
```json
// Too aggressive
{"reminder_schedule": [0, 1, 2, 3, 4, 5, 6, 7]}
```

**Do:**
```json
// Give clients reasonable time
{"reminder_schedule": [-3, 3, 7, 14]}
```

### 2. Review Low-Confidence Detections Promptly

- Check Slack notifications daily
- False positives degrade AI accuracy over time
- Corrections improve future detection

### 3. Customize Reminder Messages

- Add personal touch to important clients
- Include payment instructions or links
- Mention project/service context

### 4. Use Escalation Wisely

- When escalation notification arrives, reach out personally
- Consider phone call instead of email
- Document client response in notes

### 5. Keep Invoice Status Updated

- Mark as paid immediately when payment received
- Use partial payment feature for installments
- Add notes for context (e.g., "Waiting for bank transfer")

### 6. Monitor Your Metrics

Check periodically:
- Average days to payment
- Escalation rate
- False positive rate
- Reminder effectiveness

---

## Troubleshooting

### Invoice Not Detected

**Possible causes:**
- Email sent from different account
- No PDF attachment in email
- PDF doesn't look like an invoice
- Gmail API not properly connected

**Solutions:**
1. Verify Gmail connection: Check Settings → Integrations
2. Ensure PDF is attached to sent email
3. Check invoice format (should have clear amount, date, invoice number)
4. Manual entry: *(Coming soon in dashboard)*

### False Positives (Quotes, Estimates Detected)

**Solution:**
1. Reject via Slack: Click "Reject" button
2. Add reason: "Quote, not invoice" or "Estimate only"
3. AI learns from rejections to improve accuracy

### Reminder Not Sending

**Check:**
1. Is reminder approved? Status should be `approved`, not `pending_approval`
2. Is invoice already marked as paid?
3. Check Gmail API connection status
4. Review Celery worker logs (for admins)

### Slack Notifications Not Appearing

**Solutions:**
1. Check if `@FounderPilot` bot is in the channel
2. Verify Slack integration: Settings → Integrations
3. Check notification settings: `GET /api/v1/invoices/settings`
4. Re-authorize Slack app if needed

### Incorrect Invoice Data

**Fix:**
1. Confirm invoice with corrected data:
```bash
curl -X POST ".../invoices/{id}/confirm" \
  -d '{"corrected_data": {"amount_total": 5500.00}}'
```
2. AI learns from corrections for future detections

---

## FAQ

### Q: Can I manually add invoices?
**A:** Currently, InvoicePilot focuses on auto-detection from Gmail. Manual entry via dashboard is planned for a future release. As a workaround, send yourself an email with the invoice PDF attached.

### Q: What if I use a different email provider?
**A:** InvoicePilot currently supports Gmail only. Support for Microsoft 365 / Outlook is planned.

### Q: Can I see which reminders clients opened?
**A:** Not currently. Email read receipts are unreliable. Focus on payment status and client responses instead.

### Q: What happens if a client replies to a reminder?
**A:** Replies go to your Gmail inbox as normal. InvoicePilot doesn't automatically detect responses yet. Mark the invoice as paid manually when payment is confirmed.

### Q: Can I use different reminder schedules for different clients?
**A:** Not currently. All invoices use the global reminder schedule. Per-client customization is planned for future releases.

### Q: Is my invoice data secure?
**A:** Yes. All data is:
- Encrypted in transit (TLS)
- Encrypted at rest
- Isolated per tenant (you only see your data)
- Stored in compliance with SOC 2 standards

### Q: How much does InvoicePilot cost?
**A:** InvoicePilot is included in your FounderPilot subscription. Pricing details available at [founderpilot.com/pricing](https://founderpilot.com/pricing).

### Q: Can I export my invoice data?
**A:** Yes, via API:
```bash
curl -X GET "https://api.founderpilot.com/api/v1/invoices" \
  -H "Authorization: Bearer YOUR_TOKEN" > invoices.json
```
Dashboard export feature coming soon.

### Q: What languages are supported for reminders?
**A:** Currently English only. Multi-language support is planned based on user demand.

### Q: Can I disable InvoicePilot temporarily?
**A:** Yes:
```bash
curl -X PUT ".../invoices/settings" -d '{"enabled": false}'
```
This stops scanning and reminders but preserves existing data.

---

## Getting Help

### Support Channels
- 📧 Email: support@founderpilot.com
- 💬 Slack: Join #invoice-pilot in FounderPilot Community
- 📚 Documentation: https://docs.founderpilot.com/invoice-pilot
- 🐛 Bug Reports: https://github.com/founderpilot/issues

### Provide Feedback
We're actively improving InvoicePilot! Share your feedback:
- Feature requests: support@founderpilot.com
- UI/UX suggestions: #feedback Slack channel
- Bug reports: GitHub Issues

---

## Appendix: Complete Settings Reference

```json
{
  // Feature toggle
  "enabled": true,

  // Confidence threshold (0.0-1.0)
  // Invoices below this threshold require manual approval
  "confidence_threshold": 0.8,

  // Reminder schedule (days relative to due_date)
  // Negative = before, positive = after, 0 = on due date
  "reminder_schedule": [-3, 3, 7, 14],

  // Reminder tone: "friendly", "professional", "firm"
  "reminder_tone": "friendly",

  // Number of reminders before escalation (≥1)
  "escalation_threshold": 3,

  // Auto-approve high confidence detections
  "auto_approve_high_confidence": true,

  // How often to scan Gmail (minutes)
  "scan_interval_minutes": 5,

  // Notification channels: ["slack", "email"]
  "notification_channels": ["slack", "email"]
}
```

---

## Quick Start Checklist

- [ ] Enable InvoicePilot in settings
- [ ] Configure reminder schedule (default: `-3, 3, 7, 14`)
- [ ] Set reminder tone (default: `friendly`)
- [ ] Verify Gmail integration working
- [ ] Verify Slack integration working
- [ ] Send test invoice to yourself
- [ ] Confirm detection in Slack notification
- [ ] Approve test reminder
- [ ] Mark test invoice as paid
- [ ] Review dashboard to ensure all working

**Estimated setup time:** 10 minutes

---

*Generated: 2026-02-02*
*Version: 1.0.0*
*Feature: FEAT-004-invoice-pilot*

**Next Steps:** Ready to get started? Enable InvoicePilot now and let AI handle your invoice tracking!
