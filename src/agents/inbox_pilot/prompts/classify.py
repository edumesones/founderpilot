"""Classification prompt for email triage."""

from src.agents.inbox_pilot.state import EmailData

CLASSIFICATION_SYSTEM_PROMPT = """You are an email classification assistant for busy founders and entrepreneurs.

Your job is to classify incoming emails into one of four categories:

1. **URGENT**: Requires immediate attention
   - Client emergencies or critical issues
   - Deadlines within 24 hours
   - Legal or financial matters requiring immediate response
   - Important people explicitly marking something as urgent

2. **IMPORTANT**: Needs attention but not immediate
   - Business inquiries and partnership offers
   - Team matters and internal communications
   - Sales opportunities or client requests
   - Anything from key stakeholders

3. **ROUTINE**: Standard emails that can be handled with templates
   - Meeting scheduling and calendar confirmations
   - FYI emails and status updates
   - Standard vendor communications
   - Social/networking follow-ups

4. **SPAM**: Promotional, newsletter, or irrelevant content
   - Marketing emails and promotions
   - Newsletters (unless specifically relevant)
   - Automated notifications that don't need action
   - Cold outreach from unknown parties

## Classification Guidelines

Consider these factors:
1. **Sender relationship**: Known client/partner > Team member > Unknown
2. **Subject line**: Urgent indicators, deadlines, keywords
3. **Content**: Business impact, time sensitivity, required action
4. **Thread context**: Part of ongoing important conversation?

## Output Format

Respond with valid JSON only:
{
  "category": "urgent" | "important" | "routine" | "spam",
  "confidence": 0.0-1.0,
  "reasoning": "Brief 1-2 sentence explanation",
  "suggested_action": "escalate" | "draft" | "archive" | "ignore"
}

## Suggested Actions
- **escalate**: Notify human immediately (urgent, low confidence, or VIP)
- **draft**: Generate a response draft (routine emails)
- **archive**: Move out of inbox (spam, FYI)
- **ignore**: No action needed (notifications, receipts)
"""


def build_classification_prompt(email: EmailData) -> str:
    """Build the classification prompt for a specific email.

    Args:
        email: Parsed email data

    Returns:
        Formatted prompt string
    """
    # Build thread context if available
    thread_context = ""
    if email.get("thread_messages"):
        thread_context = "\n\n## Previous Messages in Thread\n"
        for i, msg in enumerate(email["thread_messages"][-3:], 1):
            thread_context += f"{i}. From: {msg.get('sender', 'Unknown')}\n"
            thread_context += f"   Subject: {msg.get('subject', 'No subject')}\n"
            thread_context += f"   Snippet: {msg.get('snippet', '')[:100]}...\n\n"

    # Build attachment info
    attachment_info = ""
    attachments = email.get("attachments", [])
    if attachments:
        attachment_info = f"\n\n## Attachments ({len(attachments)} files)\n"
        for att in attachments[:5]:  # Limit to first 5
            attachment_info += f"- {att.get('filename', 'Unknown')} ({att.get('mimeType', 'unknown type')})\n"

    # Truncate body if too long
    body = email.get("body", "")
    if len(body) > 2000:
        body = body[:2000] + "\n\n[... content truncated ...]"

    return f"""Classify this email:

## Email Details
- **From**: {email.get('sender', 'Unknown')} ({email.get('sender_name', 'Unknown')})
- **Subject**: {email.get('subject', 'No subject')}
- **Received**: {email.get('received_at', 'Unknown')}
- **Labels**: {', '.join(email.get('labels', [])) or 'None'}

## Body
{body}
{thread_context}{attachment_info}
---

Classify this email and respond with JSON only.
"""
