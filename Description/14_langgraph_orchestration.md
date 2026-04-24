# Step 14 — LangGraph Orchestration (The Assembly Line Controller)

## What This Does

The six agents we built are individual specialists. Each one knows how to do its job, but none of them knows about the others. The LangGraph orchestration layer is the controller that wires them together into a functioning pipeline — it decides which agent runs when, passes the shared state between them, and handles the one branching decision in the system.

Think of it as the factory floor manager who designed the assembly line. Workers stay at their stations. The manager controls the conveyor belt.

## How It Works in Plain English

The orchestration uses LangGraph's `StateGraph` to define a directed graph of processing steps:

**The Nodes (Agents):**
Each agent becomes a "node" in the graph. There are six nodes, one per agent:
1. `security_in` — The front door guard
2. `classifier` — The triage nurse
3. `retriever` — The policy librarian
4. `drafter` — The empathetic writer
5. `critic` — The compliance gatekeeper
6. `security_out` — The exit checkpoint

**The Edges (Connections):**
Most connections are simple straight lines — one agent finishes, the next one starts:
- `security_in` → `classifier` → `retriever` → `drafter` → `critic`

After the `critic`, something different happens.

**The Conditional Branch:**
After the Critic finishes its review, the system makes a routing decision:
- If the Critic said `safe_to_send = true` → go to `security_out` (the exit)
- If the Critic said `safe_to_send = false` AND provided revision feedback AND this is the first draft → go back to `drafter` for one more try
- If the Critic said `safe_to_send = false` with no fixable feedback, or the revision cap is reached → go to `security_out` (exit as escalation)

This is the only branching point in the entire pipeline. Every other connection is a straight line.

**The Injection Short-Circuit:**
There is one additional routing check: after the Security Input Agent, if the injection score exceeds the threshold (0.80), the pipeline skips straight to `security_out` without running the Classifier, Retriever, Drafter, or Critic. A suspected injection attack does not deserve AI processing — it goes directly to a human security queue.

**Termination:**
The graph has exactly one exit point: the edge from `security_out` to `END`. Every possible path through the graph — auto-response, escalation, injection short-circuit, error — ends here. There is no path by which the graph can run forever.

## Why This Design

- **Explicit control flow.** Every connection is visible in the code. There is no hidden routing, no implicit handoffs. If you want to know the order agents run in, you read the graph definition — it is a dozen lines of code.
- **Bounded loops.** The Critic→Drafter revision loop runs at most once. A counter in the state tracks iterations, and the router enforces the cap. This prevents runaway token costs and infinite processing.
- **Injection fast-path.** Malicious input should not be processed by the full pipeline. Short-circuiting saves cost, reduces risk, and gets the ticket to a human faster.
- **Easy to extend.** Adding a new agent (say, a Sentiment Analyzer between the Classifier and Retriever) means adding one node and two edges. No existing agent's code changes.
- **Auditable.** LangGraph emits structured events at every node transition. Combined with LangSmith tracing, you can see exactly which nodes ran, in what order, and what state they produced.
