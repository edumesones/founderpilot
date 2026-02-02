"""Reminder draft generation prompts for LLM."""

# Simple format-based prompt for reminder drafting
REMINDER_DRAFT_PROMPT = """Draft a payment reminder email for the following invoice:

**Invoice Details:**
- Invoice Number: {invoice_number}
- Client Name: {client_name}
- Amount: {amount}
- Due Date: {due_date}
- Days Overdue: {days_overdue}

**Reminder Context:**
- This is reminder #{reminder_count}
- Suggested tone: {tone}

**Instructions:**
- Use a {tone} tone appropriate for this reminder
- Be clear about the amount due and payment deadline
- Keep it concise (2-3 short paragraphs)
- Include a clear call-to-action

Respond with valid JSON only:
{{
  "subject": "Email subject line",
  "body": "Full email body with greeting, context, ask, details, closing",
  "confidence": 0.0-1.0
}}
"""

REMINDER_DRAFT_SYSTEM_PROMPT = """You are a payment reminder assistant for freelancers and small businesses.

Your job is to draft polite, professional payment reminder emails based on invoice status and reminder history.

## Reminder Tone Guidelines:

### 1. FRIENDLY (First reminder, 0-3 days overdue)
- Warm and understanding tone
- Assume good faith (client may have forgotten)
- Include "no rush" or "when you have a moment"
- Focus on helpfulness

### 2. PROFESSIONAL (Second reminder, 4-7 days overdue)
- More direct but still polite
- Clear ask for payment
- Include payment instructions
- Mention due date explicitly

### 3. FIRM (Third+ reminder, 8+ days overdue)
- Clear and businesslike
- Express concern about delay
- Request immediate action or explanation
- Mention potential consequences (politely)

## Email Structure:

1. **Subject Line**: Short, clear, includes invoice number
2. **Greeting**: Personalized with client name
3. **Context**: Reference the invoice and service provided
4. **Ask**: Clear request for payment
5. **Details**: Amount, invoice number, due date
6. **Payment Instructions**: How to pay (if applicable)
7. **Closing**: Professional sign-off

## Output Format:

Respond with valid JSON only:
{
  "subject": "Email subject line",
  "body": "Full email body with greeting, context, ask, details, closing",
  "tone": "friendly" | "professional" | "firm",
  "confidence": 0.0-1.0
}

## Confidence Guidelines:
- 0.9-1.0: All context available, clear tone match
- 0.7-0.9: Most context available, appropriate tone
- 0.5-0.7: Some context missing, generic draft
- 0.0-0.5: Critical context missing, cannot draft effectively
"""


def build_reminder_prompt(invoice_data: dict, reminder_context: dict) -> str:
    """Build the user prompt for reminder generation.

    Args:
        invoice_data: Invoice details (number, amount, client, dates)
        reminder_context: Context about reminder history and overdue days

    Returns:
        Formatted prompt string
    """
    # Extract invoice details
    invoice_number = invoice_data.get("invoice_number", "N/A")
    client_name = invoice_data.get("client_name", "Client")
    amount = invoice_data.get("amount_total", 0)
    currency = invoice_data.get("currency", "USD")
    due_date = invoice_data.get("due_date", "N/A")

    # Extract reminder context
    days_overdue = reminder_context.get("days_overdue", 0)
    reminder_count = reminder_context.get("reminder_count", 0)
    previous_reminder_date = reminder_context.get("previous_reminder_date")

    # Determine suggested tone
    if reminder_count == 0:
        suggested_tone = "friendly"
    elif reminder_count == 1:
        suggested_tone = "professional"
    else:
        suggested_tone = "firm"

    prompt = f"""Draft a payment reminder email for the following invoice:

**Invoice Details:**
- Invoice Number: {invoice_number}
- Client Name: {client_name}
- Amount: {currency} {amount}
- Due Date: {due_date}
- Days Overdue: {days_overdue}

**Reminder Context:**
- This is reminder #{reminder_count + 1}
- Previous reminder sent: {previous_reminder_date or 'N/A (first reminder)'}

**Instructions:**
- Use a {suggested_tone} tone appropriate for reminder #{reminder_count + 1}
- Be clear about the amount due and payment deadline
- Keep it concise (2-3 short paragraphs)
- Include a clear call-to-action

Generate the reminder email in JSON format.
"""

    return prompt


ESCALATION_NOTIFICATION_TEMPLATE = """⚠️ **Payment Issue Escalation**

**Invoice:** {invoice_number}
**Client:** {client_name}
**Amount:** {currency} {amount}
**Days Overdue:** {days_overdue}
**Reminders Sent:** {reminder_count}

**Pattern Detected:** {pattern_type}

This invoice has had {reminder_count} reminders sent without payment or response.

**Recommended Actions:**
1. Direct phone call to client
2. Review contract terms and escalation procedures
3. Consider late payment fees or service suspension
4. If high amount, consult with legal advisor

**Invoice Details:** {invoice_url}
"""
