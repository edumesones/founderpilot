"""Generate brief node - creates meeting brief with LLM."""

from datetime import datetime
from typing import Any

from src.agents.meeting_pilot.state import MeetingState, BriefResult


async def generate_brief(
    state: MeetingState,
    llm_router: Any,  # LLMRouter
    system_prompt: str,
) -> dict:
    """Generate meeting brief using LLM.

    This node creates a contextual brief for the upcoming meeting
    based on participant history and meeting details.

    Args:
        state: Current agent state
        llm_router: LLM provider router
        system_prompt: System prompt for brief generation

    Returns:
        State updates with generated brief
    """
    step = {
        "node": "generate_brief",
        "timestamp": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }

    try:
        meeting = state.get("meeting")
        if not meeting:
            raise ValueError("No meeting data available")

        participant_contexts = state.get("participant_contexts", [])

        # Build the prompt
        user_prompt = _build_brief_prompt(meeting, participant_contexts)

        # Call LLM (using classify task type for speed/cost)
        response = await llm_router.call(
            task_type="generate",  # Use generate for quality
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        # Parse response and calculate confidence
        content, confidence, objectives, warnings = _parse_brief_response(
            response, participant_contexts
        )

        brief: BriefResult = {
            "content": content,
            "confidence": confidence,
            "participant_contexts": participant_contexts,
            "suggested_objectives": objectives,
            "warnings": warnings,
            "generated_at": datetime.utcnow().isoformat(),
        }

        step["result"] = {
            "content_length": len(content),
            "confidence": confidence,
            "objectives_count": len(objectives),
        }

        return {
            "brief": brief,
            "status": "brief_sent" if confidence >= 0.8 else "brief_sent",
            "needs_human_review": confidence < 0.8,
            "steps": state.get("steps", []) + [step],
        }

    except Exception as e:
        step["error"] = str(e)
        return {
            "error": f"Failed to generate brief: {e}",
            "status": "error",
            "steps": state.get("steps", []) + [step],
        }


def _build_brief_prompt(meeting: dict, contexts: list[dict]) -> str:
    """Build the user prompt for brief generation.

    Args:
        meeting: Meeting data
        contexts: Participant contexts

    Returns:
        Formatted prompt string
    """
    # Meeting details
    prompt_parts = [
        f"Meeting: {meeting['title']}",
        f"Time: {meeting['start_time']}",
        f"Duration: {meeting['duration_minutes']} minutes",
    ]

    if meeting.get("description"):
        prompt_parts.append(f"Description: {meeting['description']}")

    if meeting.get("location"):
        prompt_parts.append(f"Location: {meeting['location']}")

    # Participants
    prompt_parts.append("\nParticipants:")
    for ctx in contexts:
        name = ctx.get("name") or ctx["email"]
        if ctx.get("is_first_contact"):
            prompt_parts.append(f"- {name} ({ctx['email']}): First contact")
        else:
            email_count = ctx.get("email_count", 0)
            summary = ctx.get("summary", "No recent topics")
            prompt_parts.append(
                f"- {name} ({ctx['email']}): {email_count} emails, {summary}"
            )

    prompt_parts.append(
        "\nGenerate a concise meeting brief with:"
        "\n1. Key context about each participant"
        "\n2. Suggested objectives for this meeting"
        "\n3. Any relevant topics from past communications"
    )

    return "\n".join(prompt_parts)


def _parse_brief_response(
    response: str,
    contexts: list[dict],
) -> tuple[str, float, list[str], list[str]]:
    """Parse LLM response into brief components.

    Args:
        response: Raw LLM response
        contexts: Participant contexts for confidence calculation

    Returns:
        Tuple of (content, confidence, objectives, warnings)
    """
    content = response.strip()

    # Calculate confidence based on context quality
    # Higher confidence if we have email history
    has_context = sum(1 for c in contexts if not c.get("is_first_contact"))
    total = len(contexts) if contexts else 1

    if total == 0:
        confidence = 0.5
    elif has_context == total:
        confidence = 0.9
    elif has_context > 0:
        confidence = 0.7 + (0.2 * has_context / total)
    else:
        confidence = 0.6

    # Extract objectives (simple parsing - improve with structured output)
    objectives = []
    for line in content.split("\n"):
        if line.strip().startswith(("- ", "* ", "1.", "2.", "3.")):
            if "objective" in line.lower() or "goal" in line.lower():
                objectives.append(line.strip().lstrip("-*0123456789. "))

    # Generate warnings
    warnings = []
    if has_context == 0:
        warnings.append("No email history found for any participants")
    elif has_context < total:
        first_contacts = [c["email"] for c in contexts if c.get("is_first_contact")]
        warnings.append(f"First contact with: {', '.join(first_contacts)}")

    return content, confidence, objectives[:5], warnings
