"""
Nimbus Bank Triage — Graph Integration Tests

Tests graph compilation, routing logic, state flow,
and structural guarantees of the LangGraph pipeline.
"""

import pytest
from src.graph import (
    build_graph,
    compile_graph,
    route_after_security_in,
    route_after_critic,
    INJECTION_THRESHOLD,
    MAX_DRAFT_ITERATIONS,
)


# ═══════════════════════════════════════════════════════════════
# Graph Compilation Tests
# ═══════════════════════════════════════════════════════════════

class TestGraphCompilation:
    """Verify the graph compiles and has the expected structure."""

    def test_graph_builds_without_error(self):
        graph = build_graph()
        assert graph is not None

    def test_graph_compiles_without_error(self):
        app = compile_graph()
        assert app is not None

    def test_graph_has_all_nodes(self):
        graph = build_graph()
        expected_nodes = {
            "security_in", "classifier", "retriever",
            "drafter", "critic", "security_out",
        }
        actual_nodes = set(graph.nodes.keys())
        assert expected_nodes.issubset(actual_nodes), (
            f"Missing nodes: {expected_nodes - actual_nodes}"
        )

    def test_graph_has_six_agent_nodes(self):
        graph = build_graph()
        # Exclude __start__ and __end__ meta-nodes
        agent_nodes = [n for n in graph.nodes.keys() if not n.startswith("__")]
        assert len(agent_nodes) == 6

    def test_compiled_graph_has_entry_point(self):
        app = compile_graph()
        mermaid = app.get_graph().draw_mermaid()
        assert "__start__" in mermaid
        assert "security_in" in mermaid

    def test_compiled_graph_has_end_point(self):
        app = compile_graph()
        mermaid = app.get_graph().draw_mermaid()
        assert "__end__" in mermaid
        assert "security_out" in mermaid


# ═══════════════════════════════════════════════════════════════
# Routing: Security Input → Classifier or Short-Circuit
# ═══════════════════════════════════════════════════════════════

class TestSecurityInputRouting:
    """Test the injection short-circuit routing decision."""

    def test_low_injection_continues_to_classifier(self):
        state = {"injection_score": 0.1}
        assert route_after_security_in(state) == "classifier"

    def test_medium_injection_continues_to_classifier(self):
        state = {"injection_score": 0.5}
        assert route_after_security_in(state) == "classifier"

    def test_threshold_injection_continues_to_classifier(self):
        """Score exactly at threshold should NOT short-circuit."""
        state = {"injection_score": INJECTION_THRESHOLD}
        assert route_after_security_in(state) == "classifier"

    def test_high_injection_short_circuits(self):
        state = {"injection_score": 0.95}
        assert route_after_security_in(state) == "security_out"

    def test_just_above_threshold_short_circuits(self):
        state = {"injection_score": INJECTION_THRESHOLD + 0.01}
        assert route_after_security_in(state) == "security_out"

    def test_max_injection_short_circuits(self):
        state = {"injection_score": 1.0}
        assert route_after_security_in(state) == "security_out"

    def test_zero_injection_continues(self):
        state = {"injection_score": 0.0}
        assert route_after_security_in(state) == "classifier"

    def test_missing_injection_score_defaults_safe(self):
        state = {}
        assert route_after_security_in(state) == "classifier"


# ═══════════════════════════════════════════════════════════════
# Routing: Critic → Security Out or Drafter Revision
# ═══════════════════════════════════════════════════════════════

class TestCriticRouting:
    """Test the Critic's routing decision (exit vs. revision loop)."""

    def test_safe_to_send_exits(self):
        state = {"safe_to_send": True, "critic_feedback": None, "draft_iteration": 1}
        assert route_after_critic(state) == "security_out"

    def test_not_safe_no_feedback_exits(self):
        """No fixable feedback → escalate, don't revise."""
        state = {"safe_to_send": False, "critic_feedback": None, "draft_iteration": 1}
        assert route_after_critic(state) == "security_out"

    def test_not_safe_empty_feedback_exits(self):
        state = {"safe_to_send": False, "critic_feedback": "", "draft_iteration": 1}
        assert route_after_critic(state) == "security_out"

    def test_not_safe_with_feedback_first_draft_revises(self):
        """Fixable feedback on first draft → send back to drafter."""
        state = {
            "safe_to_send": False,
            "critic_feedback": "Remove the dollar amount in paragraph 2",
            "draft_iteration": 1,
        }
        assert route_after_critic(state) == "drafter"

    def test_not_safe_with_feedback_at_cap_exits(self):
        """Revision cap exceeded → escalate even with feedback."""
        state = {
            "safe_to_send": False,
            "critic_feedback": "Still has issues",
            "draft_iteration": MAX_DRAFT_ITERATIONS + 1,
        }
        assert route_after_critic(state) == "security_out"

    def test_not_safe_with_feedback_beyond_cap_exits(self):
        state = {
            "safe_to_send": False,
            "critic_feedback": "Needs more work",
            "draft_iteration": 10,
        }
        assert route_after_critic(state) == "security_out"

    def test_missing_safe_to_send_defaults_not_safe(self):
        state = {"critic_feedback": None, "draft_iteration": 1}
        assert route_after_critic(state) == "security_out"

    def test_missing_draft_iteration_defaults_zero(self):
        state = {
            "safe_to_send": False,
            "critic_feedback": "Fix something",
        }
        # draft_iteration defaults to 0, which is <= MAX_DRAFT_ITERATIONS
        assert route_after_critic(state) == "drafter"


# ═══════════════════════════════════════════════════════════════
# State Flow Invariants
# ═══════════════════════════════════════════════════════════════

class TestStateInvariants:
    """Test structural invariants of the pipeline state flow."""

    def test_injection_threshold_is_configured(self):
        assert 0.0 < INJECTION_THRESHOLD <= 1.0

    def test_max_iterations_is_bounded(self):
        assert 1 <= MAX_DRAFT_ITERATIONS <= 3

    def test_revision_loop_is_bounded(self):
        """Prove the revision loop cannot exceed the cap."""
        for iteration in range(10):
            state = {
                "safe_to_send": False,
                "critic_feedback": "Fix this",
                "draft_iteration": iteration,
            }
            result = route_after_critic(state)
            if iteration > MAX_DRAFT_ITERATIONS:
                assert result == "security_out", (
                    f"Revision loop not bounded at iteration {iteration}"
                )

    def test_all_critic_paths_terminate(self):
        """Every possible critic state resolves to a valid next node."""
        test_cases = [
            {"safe_to_send": True, "critic_feedback": None, "draft_iteration": 0},
            {"safe_to_send": True, "critic_feedback": "feedback", "draft_iteration": 0},
            {"safe_to_send": False, "critic_feedback": None, "draft_iteration": 0},
            {"safe_to_send": False, "critic_feedback": "", "draft_iteration": 0},
            {"safe_to_send": False, "critic_feedback": "fix", "draft_iteration": 0},
            {"safe_to_send": False, "critic_feedback": "fix", "draft_iteration": 1},
            {"safe_to_send": False, "critic_feedback": "fix", "draft_iteration": 2},
            {"safe_to_send": False, "critic_feedback": None, "draft_iteration": 99},
            {},
        ]
        valid_targets = {"security_out", "drafter"}
        for state in test_cases:
            result = route_after_critic(state)
            assert result in valid_targets, (
                f"Invalid routing target '{result}' for state {state}"
            )

    def test_all_security_paths_terminate(self):
        """Every possible security input state resolves to a valid next node."""
        test_cases = [
            {"injection_score": 0.0},
            {"injection_score": 0.5},
            {"injection_score": 0.79},
            {"injection_score": 0.80},
            {"injection_score": 0.81},
            {"injection_score": 1.0},
            {},
        ]
        valid_targets = {"classifier", "security_out"}
        for state in test_cases:
            result = route_after_security_in(state)
            assert result in valid_targets, (
                f"Invalid routing target '{result}' for state {state}"
            )
