# Step 9 — Classifier Agent (The Triage Nurse)

## What This Does

When a patient walks into a hospital emergency room, a triage nurse quickly assesses them: How serious is this? What department should handle it? How distressed is the patient? The Classifier Agent does the same thing for support tickets.

It reads the sanitized ticket and produces a structured assessment: what category the issue falls into, how urgent it is, what the customer's emotional state is, and how confident the classification is.

## How It Works in Plain English

The Classifier receives the ticket text (already cleaned of PII and wrapped in safety delimiters) and sends it to Claude Haiku — a fast, deterministic AI model. The model is given very specific instructions: read this ticket, classify it, and return a JSON object with exactly five fields.

**Category** — One of four buckets:
- *Fraud* — Someone used the customer's card or account without permission.
- *Dispute* — The customer made the purchase but wants their money back.
- *Access Issue* — The customer cannot log in, their app is broken, or their card is locked.
- *Inquiry* — A general question about fees, policies, or how something works.

**Urgency** — How quickly this needs attention (Critical, High, Medium, Low).

**Sentiment** — How the customer is feeling (Angry, Distressed, Neutral, Positive). This drives the tone of the response the Drafter will write.

**Confidence** — A number from 0 to 100 representing how sure the model is. If confidence falls below 70, the ticket is flagged for human triage regardless of what happens downstream. This is the system's way of saying "I'm not sure — let a human decide."

**Reasoning** — A short explanation that goes into the audit log, so anyone reviewing the decision later can understand why.

## Why This Design

- **Structured output, not free text.** The classifier returns exact JSON fields, not a paragraph. This makes routing decisions deterministic and testable.
- **Confidence threshold as a safety valve.** The system knows when it does not know. Low-confidence tickets always end up with a human, preventing the AI from confidently sending the wrong thing.
- **Temperature 0.0.** The model is completely deterministic — the same ticket always produces the same classification. This is critical for testing and auditability.
- **Single responsibility.** The Classifier does not write responses. It does not look up policies. It answers one question: "What is this ticket?"
