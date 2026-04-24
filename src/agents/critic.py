"""
Nimbus Bank Triage — Compliance Critic Agent

Reviews the Drafter's output against hard-block rules and soft signals.
Decides whether the response is safe to auto-send or must be escalated.
Can request one revision from the Drafter for fixable content issues.
Uses Claude Haiku at temperature 0.0 for deterministic compliance checks.
"""

import os
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from src.utils.models import get_fast_llm, invoke_structured_with_retry


# ── Load critic prompt ───────────────────────────────────────
_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "critic.md"
)
with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
    CRITIC_SYSTEM_PROMPT = f.read()

# Thresholds
CONFIDENCE_THRESHOLD = int(os.environ.get("CLASSIFIER_CONFIDENCE_THRESHOLD", "70"))
INJECTION_THRESHOLD = float(os.environ.get("INJECTION_SCORE_THRESHOLD", "0.80"))
MAX_DRAFT_ITERATIONS = int(os.environ.get("MAX_DRAFT_ITERATIONS", "1"))


# ── Structured output schema ────────────────────────────────
class CriticResult(BaseModel):
    safe_to_send: bool = Field(description="Whether the draft is safe for auto-send")
    blocked_rules: list[str] = Field(
        default_factory=list, description="List of rule descriptions that triggered"
    )
    escalation_reason: str = Field(
        default="", description="Reason for escalation (empty if safe)"
    )
    revision_feedback: str = Field(
        default="", description="Feedback for Drafter if a fixable issue was found"
    )
    confidence: int = Field(ge=0, le=100, description="Critic confidence 0-100")


def compliance_critic(state: dict) -> dict:
    """
    Compliance Critic Agent node function.

    Reviews the draft response against hard-block rules and soft signals.
    Decides safe_to_send and optionally provides revision feedback.

    Args:
        state: Current TriageState dict

    Returns:
        Partial state update with critic decision fields.
    """
    draft = state.get("draft_response", "")
    category = state.get("category", "")
    urgency = state.get("urgency", "")
    sentiment = state.get("sentiment", "")
    confidence = state.get("classifier_confidence", 100)
    injection_score = state.get("injection_score", 0.0)
    draft_iteration = state.get("draft_iteration", 0)
    errors = list(state.get("errors", []))

    # ── Pre-check: soft signals that force escalation ────────
    # These cannot be fixed by revising the draft
    soft_blocks: list[str] = []

    if category in ("Fraud", "Dispute"):
        soft_blocks.append(f"category_{category.lower()}_always_escalates")

    if urgency == "Critical":
        soft_blocks.append("urgency_critical")

    if confidence < CONFIDENCE_THRESHOLD:
        soft_blocks.append(f"low_classifier_confidence_{confidence}")

    if injection_score > INJECTION_THRESHOLD:
        soft_blocks.append(f"injection_score_{injection_score:.2f}")

    # If soft signals already force escalation, skip the LLM call
    if soft_blocks:
        return {
            "safe_to_send": False,
            "blocked_rules": soft_blocks,
            "escalation_reason": "; ".join(soft_blocks),
            "critic_feedback": None,
            "errors": errors,
        }

    # ── LLM-based content review ─────────────────────────────
    try:
        llm = get_fast_llm()

        context = (
            f"**Draft Response to Review:**\n{draft}\n\n"
            f"**Ticket Context:**\n"
            f"- Category: {category}\n"
            f"- Urgency: {urgency}\n"
            f"- Sentiment: {sentiment}\n"
            f"- Classifier Confidence: {confidence}\n"
            f"- Injection Score: {injection_score}\n"
            f"- Draft Iteration: {draft_iteration}"
        )

        result = invoke_structured_with_retry(
            llm=llm,
            messages=[
                SystemMessage(content=CRITIC_SYSTEM_PROMPT),
                HumanMessage(content=context),
            ],
            schema=CriticResult,
        )

        safe = result.get("safe_to_send", False)
        blocked = result.get("blocked_rules", [])
        reason = result.get("escalation_reason", "")
        feedback = result.get("revision_feedback", "")

        # If blocked but fixable, and we haven't exceeded revision cap
        if not safe and feedback and draft_iteration < MAX_DRAFT_ITERATIONS:
            return {
                "safe_to_send": False,
                "blocked_rules": blocked,
                "escalation_reason": reason,
                "critic_feedback": feedback,
                "errors": errors,
            }

        # Either safe, or blocked with no fix, or revision cap exceeded
        return {
            "safe_to_send": safe,
            "blocked_rules": blocked,
            "escalation_reason": reason if not safe else None,
            "critic_feedback": None,
            "errors": errors,
        }

    except Exception as e:
        # Critic failure → escalate to be safe
        errors.append(f"critic_error: {type(e).__name__}: {e}")
        return {
            "safe_to_send": False,
            "blocked_rules": ["critic_system_error"],
            "escalation_reason": f"Critic failed: {type(e).__name__}",
            "critic_feedback": None,
            "errors": errors,
        }
