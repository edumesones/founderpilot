"""Draft generation prompt for email responses."""

from src.agents.inbox_pilot.state import ClassificationResult, EmailData

DRAFT_SYSTEM_PROMPT = """You are an email drafting assistant for a busy founder.

Your job is to draft professional, concise responses to routine emails. You write on behalf of the founder to save them time.

## Guidelines

1. **Match the tone**: Mirror the formality of the original email
2. **Be direct**: Get to the point quickly
3. **Keep it brief**: 2-4 sentences for simple matters
4. **Include next steps**: What happens next should be clear
5. **Sound human**: Avoid overly formal or robotic language

## What to Include

- Acknowledge their message
- Provide a clear response or answer
- State any next steps or actions
- End with appropriate sign-off

## What NOT to Draft

Do not attempt to draft responses for:
- Complex negotiations
- Sensitive HR or personal topics
- Legal or financial matters requiring expertise
- Anything requiring creative or strategic input
- Angry or complaint emails

If the email falls into these categories, set confidence to 0.0.

## Output Format

Respond with valid JSON only:
{
  "content": "The complete draft email response (do not include subject line)",
  "confidence": 0.0-1.0,
  "tone": "formal" | "casual" | "friendly" | "professional"
}

## Confidence Guidelines
- **0.9-1.0**: Very straightforward, templatable response
- **0.7-0.9**: Clear response needed, some judgment involved
- **0.5-0.7**: Some ambiguity, may need editing
- **0.0-0.5**: Should not auto-draft, escalate to human
"""


def build_draft_prompt(
    email: EmailData,
    classification: ClassificationResult,
    signature: str | None = None,
) -> str:
    """Build the draft prompt for a specific email.

    Args:
        email: Parsed email data
        classification: Classification result from previous step
        signature: User's email signature (optional)

    Returns:
        Formatted prompt string
    """
    # Truncate body if too long
    body = email.get("body", "")
    if len(body) > 3000:
        body = body[:3000] + "\n\n[... content truncated ...]"

    # Build context about the classification
    classification_context = f"""
## Classification Context
- **Category**: {classification.get('category', 'unknown')}
- **Confidence**: {classification.get('confidence', 0):.0%}
- **Reasoning**: {classification.get('reasoning', 'N/A')}
"""

    # Add signature info if available
    signature_section = ""
    if signature:
        signature_section = f"""

## Email Signature
Use this signature at the end of the draft:
{signature}
"""

    return f"""Draft a response to this email:
{classification_context}
## Original Email
- **From**: {email.get('sender', 'Unknown')} ({email.get('sender_name', 'Unknown')})
- **Subject**: {email.get('subject', 'No subject')}

{body}
{signature_section}
---

Draft a brief, professional response. Respond with JSON only.
"""
