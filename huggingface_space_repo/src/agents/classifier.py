"""
Nimbus Bank Triage — Classifier Agent

Reads the sanitized ticket and produces a structured classification:
category, urgency, sentiment, confidence, and reasoning.
Uses Claude Haiku at temperature 0.0 for deterministic results.
"""

import os
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from src.utils.models import get_fast_llm, invoke_structured_with_retry


# ── Load classifier prompt ───────────────────────────────────
_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "classifier.md"
)
with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
    CLASSIFIER_SYSTEM_PROMPT = f.read()

# Confidence threshold — below this, ticket is flagged for human triage
CONFIDENCE_THRESHOLD = int(os.environ.get("CLASSIFIER_CONFIDENCE_THRESHOLD", "70"))


# ── Structured output schema ────────────────────────────────
class ClassificationResult(BaseModel):
    category: Literal["Fraud", "Dispute", "Access_Issue", "Inquiry"] = Field(
        description="Ticket category"
    )
    urgency: Literal["Critical", "High", "Medium", "Low"] = Field(
        description="Urgency level"
    )
    sentiment: Literal["Angry", "Distressed", "Neutral", "Positive"] = Field(
        description="Customer sentiment"
    )
    confidence: int = Field(ge=0, le=100, description="Classification confidence 0-100")
    reasoning: str = Field(description="Short explanation for the audit log")


def classify_ticket(state: dict) -> dict:
    """
    Classifier Agent node function.

    Reads the wrapped payload from state and produces a structured
    classification with category, urgency, sentiment, and confidence.

    Args:
        state: Current TriageState dict

    Returns:
        Partial state update with classification fields.
    """
    wrapped_payload = state.get("wrapped_payload", "")
    errors = list(state.get("errors", []))

    try:
        llm = get_fast_llm()
        result = invoke_structured_with_retry(
            llm=llm,
            messages=[
                SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
                HumanMessage(content=f"Classify this support ticket:\n\n{wrapped_payload}"),
            ],
            schema=ClassificationResult,
        )

        return {
            "category": result["category"],
            "urgency": result["urgency"],
            "sentiment": result["sentiment"],
            "classifier_confidence": result["confidence"],
            "classifier_reasoning": result["reasoning"],
            "errors": errors,
        }

    except Exception as e:
        # Classification failure → low confidence forces human triage
        errors.append(f"classifier_error: {type(e).__name__}: {e}")
        return {
            "category": "Inquiry",
            "urgency": "High",
            "sentiment": "Neutral",
            "classifier_confidence": 0,
            "classifier_reasoning": f"Classification failed: {type(e).__name__}",
            "errors": errors,
        }
