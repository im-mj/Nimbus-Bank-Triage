# Step 1 — The Shared State (The Ticket's Travel Document)

## What This Does

Every support ticket that enters Nimbus Bank's triage system needs a single, organized place to carry all the information it gathers as it moves through each agent. Think of it like a medical chart that follows a patient from reception to discharge — every doctor writes their notes on the same chart.

This is the **TriageState** — a structured record that every agent in the pipeline reads from and writes to.

## How It Works in Plain English

When a customer submits a support ticket, the system creates a fresh TriageState for that ticket. As the ticket flows through each agent, the state accumulates information:

1. **Intake fields** — The raw ticket text, a unique ticket ID, the customer ID, and a timestamp. This is what arrives at the front door.

2. **Security layer adds** — A cleaned version of the ticket with sensitive data removed, flags noting what personal information was found (card numbers, phone numbers, etc.), and a suspicion score for whether the message is trying to trick the AI.

3. **Classifier adds** — The ticket category (Fraud, Dispute, Access Issue, or Inquiry), how urgent it is, the customer's emotional tone, and how confident the classifier is in its decision.

4. **Retriever adds** — A list of the most relevant knowledge base articles that match this ticket, along with how closely each article matched.

5. **Drafter adds** — The written customer-facing response, which revision pass it's on, and any feedback the compliance reviewer gave.

6. **Critic adds** — A yes-or-no decision on whether the response is safe to send directly, and if not, the specific reasons why it must go to a human.

7. **Final security adds** — The scrubbed final response and the audit log entry for compliance records.

## Why This Design

- **Every agent sees only what it needs.** The Classifier doesn't care about the draft response. The Drafter doesn't care about PII flags. But all the information lives in one place so nothing gets lost.
- **Easy to debug.** If a response goes wrong, you can inspect the state and see exactly what each agent contributed.
- **Easy to audit.** Compliance officers can reconstruct every decision the system made for any ticket by looking at its state.
- **No agents talk directly to each other.** They only read and write to this shared document. This means you can swap out, add, or remove agents without breaking the others.
