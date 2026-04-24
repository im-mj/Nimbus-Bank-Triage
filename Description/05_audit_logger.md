# Step 5 — Structured Audit Logger (The Compliance Record Keeper)

## What This Does

In a regulated bank, every decision the system makes must be traceable. If a compliance officer asks "show me every ticket where the AI suggested a refund last month," the system must be able to answer that question quickly and accurately.

The audit logger creates a clean, structured record for every ticket that passes through the system. It captures what happened, which agents were involved, what decisions were made, and how long it took — without ever storing the actual ticket text or any customer data.

## How It Works in Plain English

After a ticket finishes the entire pipeline, the logger assembles a record with only safe, pre-approved fields:

- **Ticket metadata** — The ticket ID, timestamp, and which category it was classified as.
- **Classification details** — The urgency level, customer sentiment, and how confident the classifier was.
- **Retrieval results** — Which knowledge base article IDs were used (just the IDs, not the content).
- **Critic decision** — Whether the response was auto-sent or escalated, and the specific rules that triggered escalation.
- **Security flags** — What types of PII were found in the input, whether any PII leaked into the output, and the injection suspicion score.
- **Performance** — How long the entire process took in milliseconds and how many LLM tokens were consumed.

The key discipline: the logger has an explicit allow-list of fields. If a field is not on the list, it cannot be written. This makes it structurally impossible to accidentally log a customer's card number or ticket content.

## Why This Design

- **Allow-list, not deny-list.** Instead of trying to block sensitive data from being logged (which requires knowing every possible form it could take), the logger only permits specific safe fields. Unknown data is rejected by default.
- **Structured JSON, not free text.** Every log entry has the same shape, making it easy to query, aggregate, and audit programmatically.
- **Metadata only.** A compliance officer can reconstruct every decision without ever seeing customer data. The raw ticket text and customer PII live only in memory during processing and are never persisted.
- **In-memory storage for this demo.** In production, these logs would go to a secure database or logging service. For the demo, they are kept in memory and displayed in the Streamlit admin panel.
