"""
Nimbus Bank Triage — Security Output Agent

Final agent in the pipeline. Performs:
1. PII scrub on the draft response (belt-and-suspenders)
2. Structured audit log assembly (metadata only, no raw content)
"""

import time
from datetime import datetime, timezone

from src.utils.pii import scrub_output
from src.utils.logging import build_audit_entry, audit_logger


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

    return {
        "final_response": final_response,
        "pii_flags_output": pii_flags_output,
        "pii_details_output": pii_details_output,
        "audit_log": stored_entry,
        "errors": errors,
    }
