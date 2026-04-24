"""
Nimbus Bank Triage — LangGraph StateGraph Assembly

Wires the six agents into a sequential pipeline with:
- An injection short-circuit after security_in
- A conditional Critic → Drafter revision loop (max 1 revision)
- A single exit point through security_out → END
"""

import os

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import TriageState
from src.agents.security_input import security_agent_input
from src.agents.classifier import classify_ticket
from src.agents.retriever import retrieve_kb
from src.agents.drafter import draft_response
from src.agents.critic import compliance_critic
from src.agents.security_output import security_agent_output

# ── Thresholds ───────────────────────────────────────────────
INJECTION_THRESHOLD = float(os.environ.get("INJECTION_SCORE_THRESHOLD", "0.80"))
MAX_DRAFT_ITERATIONS = int(os.environ.get("MAX_DRAFT_ITERATIONS", "1"))


# ── Router Functions ─────────────────────────────────────────

def route_after_security_in(state: dict) -> str:
    """
    After the Security Input Agent, decide whether to proceed
    with the pipeline or short-circuit on injection detection.

    Returns:
        "classifier" — normal flow, proceed to classification
        "security_out" — injection detected, skip to exit
    """
    injection_score = state.get("injection_score", 0.0)

    if injection_score > INJECTION_THRESHOLD:
        return "security_out"

    return "classifier"


def route_after_critic(state: dict) -> str:
    """
    After the Compliance Critic, decide the next step:

    Returns:
        "security_out" — safe to send OR escalation (no revision possible)
        "drafter" — critic wants a revision and we haven't exceeded the cap
    """
    safe = state.get("safe_to_send", False)
    feedback = state.get("critic_feedback")
    iteration = state.get("draft_iteration", 0)

    # Safe to send → exit
    if safe:
        return "security_out"

    # Critic provided fixable feedback and we haven't hit the revision cap
    if feedback and iteration <= MAX_DRAFT_ITERATIONS:
        return "drafter"

    # Not safe, no fixable feedback or cap exceeded → exit as escalation
    return "security_out"


# ── Graph Assembly ───────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Assemble the full triage pipeline as a LangGraph StateGraph.

    Pipeline flow:
        security_in → [injection check] → classifier → retriever
        → drafter → critic → [revision check] → security_out → END

    Returns:
        Compiled StateGraph ready for invocation.
    """
    workflow = StateGraph(TriageState)

    # ── Add nodes ────────────────────────────────────────────
    workflow.add_node("security_in", security_agent_input)
    workflow.add_node("classifier", classify_ticket)
    workflow.add_node("retriever", retrieve_kb)
    workflow.add_node("drafter", draft_response)
    workflow.add_node("critic", compliance_critic)
    workflow.add_node("security_out", security_agent_output)

    # ── Entry point ──────────────────────────────────────────
    workflow.set_entry_point("security_in")

    # ── Edges ────────────────────────────────────────────────

    # After security_in: conditional — normal flow or injection short-circuit
    workflow.add_conditional_edges(
        "security_in",
        route_after_security_in,
        {
            "classifier": "classifier",
            "security_out": "security_out",
        },
    )

    # Sequential: classifier → retriever → drafter → critic
    workflow.add_edge("classifier", "retriever")
    workflow.add_edge("retriever", "drafter")
    workflow.add_edge("drafter", "critic")

    # After critic: conditional — exit or revision loop
    workflow.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "security_out": "security_out",
            "drafter": "drafter",
        },
    )

    # Terminal edge
    workflow.add_edge("security_out", END)

    return workflow


def compile_graph():
    """
    Build and compile the graph with an in-memory checkpointer.

    Returns:
        A compiled LangGraph app ready for .invoke() or .stream()
    """
    workflow = build_graph()
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# ── Module-level compiled graph ──────────────────────────────
# Import this to use the pipeline:
#   from src.graph import triage_app
#   result = triage_app.invoke(initial_state, config={"configurable": {"thread_id": "..."}})

triage_app = compile_graph()
