"""
Nimbus Bank Triage — Structured Audit Logger

Allow-list based logger that only records approved metadata fields.
No raw ticket text, no PII, no customer content ever touches the log.
"""

import json
import time
from datetime import datetime, timezone
from typing import Any


# ── Allow-listed audit fields ────────────────────────────────
# Only these keys can appear in an audit log entry.

ALLOWED_FIELDS: set[str] = {
    "ticket_id",
    "timestamp",
    "category",
    "urgency",
    "sentiment",
    "classifier_confidence",
    "classifier_reasoning",
    "retrieved_kb_ids",
    "retrieval_top_score",
    "critic_decision",
    "blocked_rules",
    "escalation_reason",
    "pii_detected_input",
    "pii_details_input",
    "pii_detected_output",
    "pii_details_output",
    "injection_suspicion_score",
    "action_taken",
    "latency_ms",
    "token_usage",
    "draft_iteration",
    "errors",
}


class AuditLogger:
    """
    In-memory structured audit logger with allow-list enforcement.

    In production, this would write to a secure logging service
    (CloudWatch, Splunk, etc.). For the demo, logs are kept in memory
    and exposed through the Streamlit admin panel.
    """

    def __init__(self):
        self._logs: list[dict[str, Any]] = []

    def log(self, entry: dict[str, Any]) -> dict[str, Any]:
        """
        Record an audit entry. Only allow-listed fields are kept.
        Unknown fields are silently dropped.

        Returns the sanitized entry that was actually stored.
        """
        sanitized = {}
        for key, value in entry.items():
            if key in ALLOWED_FIELDS:
                sanitized[key] = value

        # Ensure timestamp is always present
        if "timestamp" not in sanitized:
            sanitized["timestamp"] = datetime.now(timezone.utc).isoformat()

        self._logs.append(sanitized)
        return sanitized

    def get_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent audit log entries."""
        return self._logs[-limit:]

    def get_log_by_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        """Look up the audit log for a specific ticket."""
        for entry in reversed(self._logs):
            if entry.get("ticket_id") == ticket_id:
                return entry
        return None

    def get_stats(self) -> dict[str, Any]:
        """Compute summary stats across all logged tickets."""
        if not self._logs:
            return {
                "total_tickets": 0,
                "by_category": {},
                "by_action": {},
                "avg_latency_ms": 0,
                "avg_confidence": 0,
            }

        by_category: dict[str, int] = {}
        by_action: dict[str, int] = {}
        latencies: list[float] = []
        confidences: list[int] = []

        for entry in self._logs:
            cat = entry.get("category", "Unknown")
            by_category[cat] = by_category.get(cat, 0) + 1

            action = entry.get("action_taken", "unknown")
            by_action[action] = by_action.get(action, 0) + 1

            if "latency_ms" in entry:
                latencies.append(entry["latency_ms"])
            if "classifier_confidence" in entry:
                confidences.append(entry["classifier_confidence"])

        return {
            "total_tickets": len(self._logs),
            "by_category": by_category,
            "by_action": by_action,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
            "avg_confidence": round(sum(confidences) / len(confidences), 1) if confidences else 0,
        }

    def to_json(self, limit: int = 50) -> str:
        """Export recent logs as formatted JSON string."""
        return json.dumps(self.get_logs(limit), indent=2, default=str)

    @property
    def count(self) -> int:
        return len(self._logs)


def build_audit_entry(state: dict, latency_ms: float) -> dict[str, Any]:
    """
    Build an audit log entry from a completed TriageState.
    Extracts only safe metadata — no raw text, no PII.
    """
    # Determine the action taken
    if state.get("errors"):
        action = "escalated_system_error"
    elif state.get("injection_score", 0) > 0.8:
        action = "escalated_injection"
    elif not state.get("safe_to_send", False):
        action = f"escalated_{state.get('category', 'unknown').lower()}"
    else:
        action = "auto_responded"

    return {
        "ticket_id": state.get("ticket_id", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": state.get("category", ""),
        "urgency": state.get("urgency", ""),
        "sentiment": state.get("sentiment", ""),
        "classifier_confidence": state.get("classifier_confidence", 0),
        "classifier_reasoning": state.get("classifier_reasoning", ""),
        "retrieved_kb_ids": [
            chunk.get("kb_id", "") for chunk in state.get("retrieved_chunks", [])
        ],
        "retrieval_top_score": state.get("retrieval_top_score", 0.0),
        "critic_decision": "ESCALATE" if not state.get("safe_to_send", False) else "AUTO_SEND",
        "blocked_rules": state.get("blocked_rules", []),
        "escalation_reason": state.get("escalation_reason"),
        "pii_detected_input": state.get("pii_flags_input", []),
        "pii_details_input": state.get("pii_details_input", []),
        "pii_detected_output": state.get("pii_flags_output", []),
        "pii_details_output": state.get("pii_details_output", []),
        "injection_suspicion_score": state.get("injection_score", 0.0),
        "action_taken": action,
        "latency_ms": round(latency_ms, 1),
        "draft_iteration": state.get("draft_iteration", 0),
        "errors": state.get("errors", []),
    }


# ── Global logger instance ───────────────────────────────────
audit_logger = AuditLogger()
