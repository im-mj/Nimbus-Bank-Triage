# Step 13 — Security Output Agent (The Exit Checkpoint)

## What This Does

The Security Output Agent is the last stop before any text leaves the system. It performs two final jobs: scrubbing the response for any PII the Drafter might have inadvertently included, and assembling the structured audit log entry for compliance records.

If the Security Input Agent is the front door guard, the Security Output Agent is the exit checkpoint — making sure nothing leaves the building that should not.

## How It Works in Plain English

**Final PII Scrub:**
Even though the Drafter works with sanitized text, there is a small chance it could reconstruct or echo something that looks like sensitive data. The output agent runs the same PII redaction patterns one more time on the final response. If anything is caught, it is replaced with placeholders and flagged in the audit log.

**Audit Log Assembly:**
The agent gathers metadata from the entire pipeline — the ticket ID, classification, which KB articles were used, the Critic's decision, what PII was found, how long the process took — and writes a single structured log entry. Critically, this log contains only approved metadata fields. The raw ticket text, the raw response, and any customer data are deliberately excluded.

**Action Label:**
The response is tagged with a clear label indicating what happened:
- "auto_responded" — The response was sent directly to the customer.
- "escalated_fraud" / "escalated_dispute" — Sent to a human agent's queue by category.
- "escalated_injection" — Flagged for security review.
- "escalated_system_error" — Something went wrong technically.

## Why This Design

- **Two-pass scrubbing.** PII is checked on the way in and on the way out. This belt-and-suspenders approach means a missed pattern on one side might be caught on the other.
- **Metadata-only logging.** The audit log proves what decisions were made and why, without storing any data that could be a liability. A compliance officer can reconstruct the flow without seeing customer data.
- **Single exit point.** Every possible outcome (auto-response, escalation, error) passes through this agent. There is no way for text to leave the system without being scrubbed and logged.
