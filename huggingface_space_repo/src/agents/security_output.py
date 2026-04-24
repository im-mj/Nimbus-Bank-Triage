"""
Nimbus Bank Triage — Security Output Agent

Final agent in the pipeline. Performs:
1. PII scrub on the draft response (belt-and-suspenders)
2. Structured audit log assembly (metadata only, no raw content)
"""

import os
import time
from datetime import datetime, timezone

from src.utils.pii import scrub_output
from src.utils.logging import build_audit_entry, audit_logger

INJECTION_THRESHOLD = float(os.environ.get("INJECTION_SCORE_THRESHOLD", "0.80"))


def security_agent_output(state: dict) -> dict:
    """
    Security Output Agent node function.

    Scrubs the final response for PII and assembles the audit log.
    This is the single exit point — every ticket passes through here
    regardless of whether it was auto-responded or escalated.

    Args:
        state: Current TriageState dict

    Returns:
        Partial state update with final_response, pii_flags_output, and audit_log.
    """
    draft = state.get("draft_response", "")
    errors = list(state.get("errors", []))
    injection_score = state.get("injection_score", 0.0)
    ticket_id = state.get("ticket_id", "N/A")

    # ── Injection short-circuit: draft was never generated ────
    # When injection score exceeds threshold the graph routes directly here,
    # skipping classifier/retriever/drafter/critic. Build a safe refusal so
    # final_response is never empty.
    is_injection_block = (not draft) and (injection_score > INJECTION_THRESHOLD)
    if is_injection_block:
        draft = (
            f"Thank you for contacting Nimbus Bank (Ticket: {ticket_id}).\n\n"
            "Your request was flagged by our automated security system and could not "
            "be processed. If you believe this is an error, please reach us directly:\n\n"
            "- **Phone:** 1-800-NIMBUS-1 (24/7)\n"
            "- **Email:** support@nimbusbank.com\n\n"
            "Warm regards,\nNimbus Bank Support Team"
        )

    # ── Step 1: Final PII scrub (whitelists bank contact info) ─
    final_response, pii_flags_output, pii_details_output = scrub_output(draft)

    if pii_flags_output:
        errors.append(f"pii_leaked_to_output: {','.join(pii_flags_output)}")

    # ── Step 2: Compute latency ──────────────────────────────
    # submitted_at is set when the ticket enters the pipeline
    submitted_at = state.get("submitted_at", "")
    latency_ms = 0.0
    if submitted_at:
        try:
            start = datetime.fromisoformat(submitted_at)
            now = datetime.now(timezone.utc)
            latency_ms = (now - start).total_seconds() * 1000
        except (ValueError, TypeError):
            pass

    # ── Step 3: Build and store audit log ────────────────────
    # Merge in the final output fields before building the entry
    completed_state = {**state}
    completed_state["final_response"] = final_response
    completed_state["pii_flags_output"] = pii_flags_output
    completed_state["errors"] = errors

    audit_entry = build_audit_entry(completed_state, latency_ms)
    stored_entry = audit_logger.log(audit_entry)

    result = {
        "final_response": final_response,
        "pii_flags_output": pii_flags_output,
        "pii_details_output": pii_details_output,
        "audit_log": stored_entry,
        "errors": errors,
    }

    # Populate escalation fields that were never set (critic was skipped)
    if is_injection_block:
        result["safe_to_send"] = False
        result["blocked_rules"] = [f"injection_score_{injection_score:.2f}"]
        result["escalation_reason"] = (
            f"Prompt injection detected (score: {injection_score:.2f})"
        )

    return result
