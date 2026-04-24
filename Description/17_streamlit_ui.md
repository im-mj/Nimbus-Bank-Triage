# Step 17 — Streamlit UI (The Customer & Agent Dashboard)

## What This Does

Everything we have built so far — the agents, the pipeline, the routing logic — runs in Python behind the scenes. The Streamlit UI is the visual layer that makes the system accessible to humans. It serves three audiences:

1. **Demo viewers** (the Wipro evaluators) who need to see the system work end to end.
2. **Simulated customers** who submit tickets and see responses.
3. **Simulated bank staff** who review escalated tickets and audit logs.

## How It Works in Plain English

The UI is organized into two main areas:

### The Ticket Submission Panel (Left Sidebar + Main Area)

The user types a support ticket into a text box (or picks from pre-loaded sample tickets for demo convenience). They click "Submit Ticket" and the system processes it in real time.

As each agent in the pipeline completes, the UI shows a live progress indicator:
- "Security scan complete..." 
- "Ticket classified as Fraud / Critical..."
- "Retrieved 4 knowledge base articles..."
- "Response drafted..."
- "Compliance review: ESCALATE..."
- "Audit log written."

When processing finishes, the UI displays the result:
- **For auto-responses:** A green badge saying "Auto-Response Sent" and the full customer response.
- **For escalations:** An orange/red badge saying "Escalated to Human Agent" with the reason, the AI's suggested draft, and the classification details.

### The Admin Panel (Expandable Sections)

Below the main response, collapsible sections show the inner workings:
- **Agent Trace** — What each agent produced, step by step.
- **Classification Details** — Category, urgency, sentiment, confidence score.
- **Retrieved Articles** — Which KB articles were matched and their similarity scores.
- **Compliance Decision** — The Critic's verdict, any blocked rules, escalation reason.
- **Security Report** — PII found in input, PII found in output, injection score.
- **Audit Log** — The full structured audit entry (metadata only, no PII).
- **Pipeline Stats** — Running averages across all submitted tickets.

## Why This Design

- **Transparency for the demo.** Evaluators need to see not just the output but *how* the system arrived at it. The expandable trace makes every agent's contribution visible.
- **Pre-loaded samples.** Demo time is limited. One-click sample tickets let you show the three key scenarios (auto-resolve, escalation, injection defense) without typing.
- **Real-time progress.** The streaming display proves the system is doing real work, not just returning a cached response. It also shows the sequential agent flow described in the architecture.
- **No fake data.** Everything displayed is the actual output from the pipeline running live. The audit log is real. The confidence scores are real. The latency is real.
