"""
Nimbus Bank Triage — Response Drafter Agent

Produces a customer-facing response using Claude Sonnet (temp 0.5).
Grounded in retrieved KB articles, calibrated to customer sentiment.
Supports one revision cycle based on Compliance Critic feedback.
"""

import os

from langchain_core.messages import SystemMessage, HumanMessage

from src.utils.models import get_drafter_llm, invoke_with_retry


# ── Load drafter prompt ──────────────────────────────────────
_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "drafter.md"
)
with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
    DRAFTER_SYSTEM_PROMPT = f.read()


def _build_context_message(state: dict) -> str:
    """
    Assemble the context message for the Drafter from the shared state.
    Includes classification, KB articles, and optional critic feedback.
    """
    parts = []

    # Classification context
    parts.append(
        f"**Ticket Classification:**\n"
        f"- Category: {state.get('category', 'Unknown')}\n"
        f"- Urgency: {state.get('urgency', 'Unknown')}\n"
        f"- Sentiment: {state.get('sentiment', 'Unknown')}\n"
        f"- Ticket ID: {state.get('ticket_id', 'N/A')}"
    )

    # Retrieved KB articles
    chunks = state.get("retrieved_chunks", [])
    if chunks:
        parts.append("\n**Retrieved Knowledge Base Articles:**")
        for i, chunk in enumerate(chunks, 1):
            parts.append(
                f"\n--- Article {i}: {chunk.get('title', 'Untitled')} "
                f"(ID: {chunk.get('kb_id', 'N/A')}, "
                f"Relevance: {chunk.get('similarity', 0):.2f}) ---\n"
                f"{chunk.get('content', '')}"
            )
    else:
        parts.append(
            "\n**No relevant knowledge base articles were found.** "
            "Acknowledge this gap in your response and route to a specialist."
        )

    # Critic feedback (revision pass)
    feedback = state.get("critic_feedback")
    if feedback:
        parts.append(
            f"\n**REVISION REQUIRED — Compliance Critic Feedback:**\n{feedback}\n"
            f"Please revise your response to address the above issues specifically."
        )

    # The ticket itself
    parts.append(f"\n**Customer Ticket:**\n{state.get('wrapped_payload', '')}")

    return "\n".join(parts)


def draft_response(state: dict) -> dict:
    """
    Response Drafter Agent node function.

    Writes a customer-facing response grounded in KB articles,
    calibrated to sentiment, and compliant with content rules.

    Args:
        state: Current TriageState dict

    Returns:
        Partial state update with draft_response and draft_iteration.
    """
    errors = list(state.get("errors", []))
    current_iteration = state.get("draft_iteration", 0)

    try:
        llm = get_drafter_llm()
        context = _build_context_message(state)

        response_text = invoke_with_retry(
            llm=llm,
            messages=[
                SystemMessage(content=DRAFTER_SYSTEM_PROMPT),
                HumanMessage(content=context),
            ],
        )

        return {
            "draft_response": response_text,
            "draft_iteration": current_iteration + 1,
            "errors": errors,
        }

    except Exception as e:
        errors.append(f"drafter_error: {type(e).__name__}: {e}")
        # Fallback draft that will force escalation
        fallback = (
            f"Thank you for contacting Nimbus Bank (Ticket: {state.get('ticket_id', 'N/A')}). "
            f"We were unable to generate an automated response for your inquiry. "
            f"A member of our support team will review your case and respond shortly. "
            f"We apologize for the delay.\n\n"
            f"Warm regards,\nNimbus Bank Support Team"
        )
        return {
            "draft_response": fallback,
            "draft_iteration": current_iteration + 1,
            "errors": errors,
        }
