# Step 18 — Evaluation & Testing (Proving the System Works)

## What This Does

Saying "the system works" is not enough — you have to prove it. This step builds a comprehensive test suite that verifies every layer of the system: individual agents, security defenses, routing logic, and end-to-end pipeline correctness.

The tests are designed so that most of them can run without calling real AI APIs (using mocked responses), while the evaluation dataset enables live integration testing when API keys are available.

## The Three Test Layers

### Layer 1: Unit Tests (test_agents.py)
Each agent is tested in isolation with fake inputs and mocked LLM responses. This verifies that:
- The Security Input Agent correctly redacts PII and wraps text in safety delimiters.
- The Classifier produces valid structured output with the expected fields.
- The Retriever returns chunks in the right format with similarity scores.
- The Drafter generates a response string and increments the draft iteration counter.
- The Critic correctly applies soft-signal rules (Fraud always escalates, low confidence always escalates).
- The Security Output Agent scrubs output and builds a valid audit log.

These tests run in milliseconds and catch structural bugs without any API calls.

### Layer 2: Security Tests (test_security.py)
Focused specifically on the safety guarantees:
- **PII completeness:** Known PII patterns (card numbers, SSNs, phones, emails, account numbers) are injected into test strings and verified as fully redacted.
- **No PII in output:** The scrubber catches PII that might appear in AI-generated responses.
- **Audit logger allow-list:** Attempting to log forbidden fields (like raw ticket text) results in those fields being silently dropped.
- **Injection payloads:** A suite of 10 known prompt injection patterns is tested to verify they are either caught by regex patterns or would be flagged by the injection classifier.

### Layer 3: Graph Tests (test_graph.py)
Verifies the orchestration logic:
- The graph compiles without errors.
- All 6 nodes are present and connected.
- The injection short-circuit router sends high-score tickets directly to security_out.
- The Critic router sends safe responses to security_out and fixable failures back to the drafter.
- The revision cap is enforced (iteration > max sends to security_out regardless of feedback).

## The 20-Ticket Evaluation Set

A curated JSON file of 20 synthetic tickets with ground-truth labels. Each ticket has:
- The ticket text (what the customer wrote).
- The expected category, urgency, and whether it should escalate.
- Whether it contains PII that should be caught.
- Whether it is an adversarial/injection attempt.

This set is designed to cover the full matrix: all 4 categories, all urgency levels, PII-heavy tickets, clean tickets, and adversarial inputs. When run against the live pipeline (with real API calls), it produces accuracy metrics that can be reported to evaluators.

## Why This Design

- **Mocked tests run without API keys.** Anyone who clones the repo can run the test suite immediately. No Anthropic or OpenAI account needed for basic verification.
- **Security tests are non-negotiable.** In a banking system, PII leakage or injection bypass is not a bug — it is a compliance failure. These tests exist to prove the defenses work.
- **The eval set is the scorecard.** The PRD promises 85% classification accuracy and 100% escalation correctness on Fraud/Dispute. The eval set is how we measure that promise.
