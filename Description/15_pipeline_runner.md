# Step 15 — Pipeline Runner (The Ticket Intake Window)

## What This Does

The Pipeline Runner is the simple entry point that takes a raw customer ticket — just the text and a customer ID — and feeds it into the full multi-agent pipeline. It handles the housekeeping that every ticket needs: generating a unique ticket ID, stamping the current time, setting up the initial state, and invoking the graph.

Think of it as the intake window at the bank's service counter. The customer hands over their request, and the clerk creates a case file with all the required fields before sending it through the system.

## How It Works in Plain English

When a ticket arrives, the runner does three things:

1. **Creates the ticket ID.** Every ticket gets a unique identifier in the format `T-20260423-XXXXX` (date + random 5-digit number). This ID follows the ticket through every agent and appears in the customer's response and the audit log.

2. **Builds the initial state.** The shared state object is initialized with the raw ticket text, customer ID, ticket ID, and timestamp. All other fields start empty — they will be filled in by each agent as the ticket flows through the pipeline.

3. **Invokes the graph.** The LangGraph pipeline is called with the initial state. The graph handles all routing, branching, and agent coordination automatically. The runner waits for the full pipeline to complete and returns the final state with all fields populated.

The runner also supports streaming — instead of waiting for the entire pipeline to finish, it can yield updates as each agent completes its work. This is used by the Streamlit UI to show real-time progress ("Security check complete... Classifying ticket... Retrieving policies...").

## Why This Design

- **Clean separation.** The runner knows nothing about what the agents do. It creates the initial state and calls the graph. All the intelligence is in the agents and the graph definition.
- **Unique ticket tracking.** Every ticket has an ID from the moment it enters the system. This makes debugging, auditing, and customer communication straightforward.
- **Streaming support.** The user sees the system working in real time instead of staring at a spinner for 10 seconds. Each agent's completion is a visible milestone.
