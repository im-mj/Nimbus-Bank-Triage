"""
Nimbus Bank Triage — Pipeline Runner

Entry point for processing a support ticket through the full
multi-agent pipeline. Handles ticket ID generation, initial state
setup, graph invocation, and file-based logging of every run.
"""

import json
import os
import random
import traceback
import uuid
from datetime import datetime, timezone

from src.graph import triage_app

# ── Log directory ────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def _generate_ticket_id() -> str:
    """Generate a unique ticket ID: NB-XXXXX (short, no long digit sequences)."""
    random_part = uuid.uuid4().hex[:8].upper()
    return f"NB-{random_part}"


def _safe_serialize(obj):
    """Make objects JSON-serializable."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, set):
        return list(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return str(obj)


def _write_log(ticket_id: str, log_data: dict):
    """Write a run log to logs/ as a JSON file."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{ticket_id}.json"
    filepath = os.path.join(LOG_DIR, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                log_data,
                f,
                indent=2,
                ensure_ascii=False,
                default=_safe_serialize,
            )
    except Exception as e:
        # Don't let logging failures break the pipeline
        print(f"[LOG ERROR] Failed to write {filepath}: {e}")


def _build_run_log(
    ticket_id: str,
    customer_id: str,
    raw_ticket: str,
    agent_trace: list[dict],
    final_state: dict,
    error: str | None = None,
    elapsed_ms: float = 0,
) -> dict:
    """Build the full run log structure."""
    return {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": round(elapsed_ms, 1),
        "raw_ticket_length": len(raw_ticket),
        "error": error,
        "agent_trace": agent_trace,
        "final_state": {
            "category": final_state.get("category"),
            "urgency": final_state.get("urgency"),
            "sentiment": final_state.get("sentiment"),
            "classifier_confidence": final_state.get("classifier_confidence"),
            "injection_score": final_state.get("injection_score"),
            "retrieval_top_score": final_state.get("retrieval_top_score"),
            "retrieved_kb_ids": [
                c.get("kb_id") for c in final_state.get("retrieved_chunks", [])
            ],
            "safe_to_send": final_state.get("safe_to_send"),
            "blocked_rules": final_state.get("blocked_rules"),
            "escalation_reason": final_state.get("escalation_reason"),
            "draft_iteration": final_state.get("draft_iteration"),
            "pii_flags_input": final_state.get("pii_flags_input"),
            "pii_details_input": final_state.get("pii_details_input", []),
            "pii_flags_output": final_state.get("pii_flags_output"),
            "pii_details_output": final_state.get("pii_details_output", []),
            "errors": final_state.get("errors", []),
            "action_taken": final_state.get("audit_log", {}).get("action_taken"),
        },
        "draft_response_preview": (final_state.get("final_response") or "")[:500],
    }


def run_pipeline(
    ticket_text: str,
    customer_id: str = "anonymous",
    thread_id: str | None = None,
) -> dict:
    """
    Process a support ticket through the full triage pipeline.

    Args:
        ticket_text: Raw customer ticket text.
        customer_id: Customer identifier (default "anonymous").
        thread_id: Optional LangGraph thread ID for checkpointing.

    Returns:
        The final TriageState dict with all fields populated.
    """
    ticket_id = _generate_ticket_id()

    if thread_id is None:
        thread_id = str(uuid.uuid4())

    initial_state = {
        "ticket_id": ticket_id,
        "raw_ticket": ticket_text,
        "customer_id": customer_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "errors": [],
    }

    config = {"configurable": {"thread_id": thread_id}}

    start = datetime.now(timezone.utc)
    error_msg = None
    result = initial_state

    try:
        result = triage_app.invoke(initial_state, config=config)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        result["errors"] = result.get("errors", []) + [str(e)]

    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    log_data = _build_run_log(
        ticket_id=ticket_id,
        customer_id=customer_id,
        raw_ticket=ticket_text,
        agent_trace=[],
        final_state=result,
        error=error_msg,
        elapsed_ms=elapsed,
    )
    _write_log(ticket_id, log_data)

    return result


def stream_pipeline(
    ticket_text: str,
    customer_id: str = "anonymous",
    thread_id: str | None = None,
):
    """
    Stream a support ticket through the pipeline, yielding
    updates as each agent completes. Logs the full run to disk.

    Yields:
        Tuples of (node_name, partial_state_update) for each
        agent that runs.
    """
    ticket_id = _generate_ticket_id()

    if thread_id is None:
        thread_id = str(uuid.uuid4())

    initial_state = {
        "ticket_id": ticket_id,
        "raw_ticket": ticket_text,
        "customer_id": customer_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "errors": [],
    }

    config = {"configurable": {"thread_id": thread_id}}

    start = datetime.now(timezone.utc)
    agent_trace = []
    accumulated_state = dict(initial_state)
    error_msg = None

    try:
        for event in triage_app.stream(initial_state, config=config):
            for node_name, state_update in event.items():
                # Record agent trace
                agent_step = {
                    "agent": node_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "output_keys": list(state_update.keys()),
                }

                # Capture key metrics per agent (safe metadata only)
                if node_name == "security_in":
                    agent_step["pii_flags"] = state_update.get("pii_flags_input", [])
                    agent_step["pii_details"] = state_update.get("pii_details_input", [])
                    agent_step["injection_score"] = state_update.get("injection_score")
                elif node_name == "classifier":
                    agent_step["category"] = state_update.get("category")
                    agent_step["urgency"] = state_update.get("urgency")
                    agent_step["confidence"] = state_update.get("classifier_confidence")
                elif node_name == "retriever":
                    agent_step["chunks_returned"] = len(state_update.get("retrieved_chunks", []))
                    agent_step["top_score"] = state_update.get("retrieval_top_score")
                elif node_name == "drafter":
                    agent_step["iteration"] = state_update.get("draft_iteration")
                    agent_step["response_length"] = len(state_update.get("draft_response", ""))
                elif node_name == "critic":
                    agent_step["safe_to_send"] = state_update.get("safe_to_send")
                    agent_step["blocked_rules"] = state_update.get("blocked_rules")
                elif node_name == "security_out":
                    agent_step["pii_in_output"] = state_update.get("pii_flags_output", [])
                    agent_step["pii_details_output"] = state_update.get("pii_details_output", [])

                agent_trace.append(agent_step)
                accumulated_state.update(state_update)
                yield node_name, state_update

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        accumulated_state["errors"] = accumulated_state.get("errors", []) + [str(e)]

    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000

    log_data = _build_run_log(
        ticket_id=ticket_id,
        customer_id=customer_id,
        raw_ticket=ticket_text,
        agent_trace=agent_trace,
        final_state=accumulated_state,
        error=error_msg,
        elapsed_ms=elapsed,
    )
    _write_log(ticket_id, log_data)
