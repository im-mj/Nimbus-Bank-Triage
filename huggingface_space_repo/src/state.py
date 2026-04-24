"""
Nimbus Bank Triage System — Shared State Definition

The TriageState is the single source of truth for the entire pipeline.
Every agent reads from and writes to this typed dictionary.
"""

from __future__ import annotations

from typing import TypedDict, Literal
from datetime import datetime


class RetrievedChunk(TypedDict):
    """A single chunk retrieved from the knowledge base."""
    kb_id: str
    title: str
    content: str
    similarity: float


class TriageState(TypedDict, total=False):
    """
    Shared state that flows through every node of the LangGraph.
    Uses total=False so agents can return partial updates.
    """

    # ── Input ────────────────────────────────────────────────
    ticket_id: str
    raw_ticket: str                 # never logged, never embedded in prompts
    customer_id: str
    submitted_at: str               # ISO-8601 timestamp string

    # ── Security Agent (Input) outputs ───────────────────────
    sanitized_ticket: str
    pii_flags_input: list[str]
    pii_details_input: list[str]    # masked PII for demo: ["card: 4532-****-****-9012"]
    injection_score: float
    wrapped_payload: str            # the <untrusted_user_content> block

    # ── Classifier outputs ───────────────────────────────────
    category: Literal["Fraud", "Dispute", "Access_Issue", "Inquiry"]
    urgency: Literal["Critical", "High", "Medium", "Low"]
    sentiment: Literal["Angry", "Distressed", "Neutral", "Positive"]
    classifier_confidence: int
    classifier_reasoning: str

    # ── Retriever outputs ────────────────────────────────────
    retrieved_chunks: list[RetrievedChunk]
    retrieval_top_score: float

    # ── Drafter outputs ──────────────────────────────────────
    draft_response: str
    draft_iteration: int            # 0 on first pass, 1 after revision
    critic_feedback: str | None     # populated on revision

    # ── Critic outputs ───────────────────────────────────────
    safe_to_send: bool
    blocked_rules: list[str]
    escalation_reason: str | None

    # ── Security Agent (Output) outputs ──────────────────────
    final_response: str             # customer-facing or escalation-suggestion
    pii_flags_output: list[str]
    pii_details_output: list[str]   # masked PII found in output (should be empty)

    # ── Audit & Errors ───────────────────────────────────────
    audit_log: dict
    errors: list[str]
