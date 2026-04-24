# Step 11 — Response Drafter Agent (The Empathetic Writer)

## What This Does

The Response Drafter is the only agent that produces text a customer will actually read. It takes everything the pipeline has gathered so far — the classified ticket, the retrieved policy articles, and the customer's emotional state — and writes a polished, empathetic, policy-grounded response.

This is where the system goes from "data processing" to "customer experience."

## How It Works in Plain English

The Drafter receives a rich context from the shared state:
- The sanitized ticket text (what the customer wrote, with PII removed)
- The classification (category, urgency, sentiment)
- The retrieved knowledge base articles (the relevant policies)
- Any feedback from the Compliance Critic (if this is a revision pass)

Using Claude Sonnet — the more capable AI model chosen specifically for its nuance with tone and empathy — the Drafter produces a response that follows strict rules:

**Tone calibration.** If the customer is angry, the response leads with a sincere apology and gets straight to action steps. If distressed, it is warm and reassuring. If neutral, professional and efficient. If positive, friendly and appreciative.

**Knowledge grounding.** Every factual claim in the response is drawn from the retrieved articles. The Drafter does not invent policies or make promises based on its general training. If no relevant articles were found, it honestly says so and routes the customer to a human specialist.

**Structural requirements.** Every response includes the ticket ID (so the customer can reference it later) and a clear next step (what to do or what to expect).

**Revision handling.** If the Compliance Critic found a problem with the first draft (like an accidental mention of a specific dollar amount), the Drafter gets one chance to fix it. The Critic's feedback is provided, and the Drafter revises specifically to address those points.

## Why This Design

- **Sonnet, not Haiku.** This is the one place where writing quality directly impacts the customer experience. The more capable model produces noticeably more natural, empathetic responses.
- **Temperature 0.5.** Low enough to stay consistent and grounded, high enough to avoid sounding robotic. Every response sounds human without being unpredictable.
- **Hard rules are not suggestions.** The Drafter's prompt explicitly lists six things it must never do (promise refunds, guarantee timelines, etc.). Even if it violates one, the Compliance Critic catches it downstream.
- **Maximum one revision.** If the first draft fails compliance and the revision also fails, the ticket escalates. This prevents endless loops and controls cost.
