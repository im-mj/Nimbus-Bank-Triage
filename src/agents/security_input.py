"""
Nimbus Bank Triage — Security Input Agent

First agent in the pipeline. Performs:
1. PII redaction (regex-based)
2. Prompt injection detection (Haiku classifier)
3. Delimiter wrapping for downstream safety
"""

import json
import os

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from src.utils.pii import redact_pii
from src.utils.models import get_fast_llm, invoke_structured_with_retry


# ── Load injection detection prompt ──────────────────────────
_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "injection.md"
)
with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
    INJECTION_SYSTEM_PROMPT = f.read()


# ── Structured output schema ────────────────────────────────
class InjectionResult(BaseModel):
    is_injection: bool = Field(description="Whether the input is a prompt injection attempt")
    score: float = Field(ge=0.0, le=1.0, description="Injection probability 0.0-1.0")
    reason: str = Field(description="Brief explanation")


def security_agent_input(state: dict) -> dict:
    """
    Security Input Agent node function.

    Takes raw ticket text from state, redacts PII, checks for
    injection, and wraps the sanitized text in safety delimiters.

    Args:
        state: Current TriageState dict

    Returns:
        Partial state update with security fields populated.
    """
    raw_ticket = state.get("raw_ticket", "")
    errors = list(state.get("errors", []))

    # ── Step 1: PII Redaction ────────────────────────────────
    sanitized_ticket, pii_flags, pii_details = redact_pii(raw_ticket)

    # ── Step 2: Injection Detection ──────────────────────────
    injection_score = 0.0
    try:
        llm = get_fast_llm()
        result = invoke_structured_with_retry(
            llm=llm,
            messages=[
                SystemMessage(content=INJECTION_SYSTEM_PROMPT),
                HumanMessage(content=sanitized_ticket),
            ],
            schema=InjectionResult,
        )
        injection_score = result.get("score", 0.0)
    except Exception as e:
        # If injection check fails, default to cautious (moderate score)
        # and log the error. Don't block the pipeline for a classifier failure.
        injection_score = 0.5
        errors.append(f"injection_classifier_error: {type(e).__name__}: {e}")

    # ── Step 3: Delimiter Wrapping ───────────────────────────
    wrapped_payload = (
        "<untrusted_user_content>\n"
        f"{sanitized_ticket}\n"
        "</untrusted_user_content>"
    )

    return {
        "sanitized_ticket": sanitized_ticket,
        "pii_flags_input": pii_flags,
        "pii_details_input": pii_details,
        "injection_score": injection_score,
        "wrapped_payload": wrapped_payload,
        "errors": errors,
    }
