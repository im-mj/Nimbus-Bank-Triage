# Step 0 — Project Overview (What We Are Building and Why)

## The Problem

Nimbus Bank receives thousands of customer support tickets every day. Some are simple questions ("What are your wire transfer fees?"), others are urgent ("Someone stole my card and charged $800"). Right now, a human agent has to read each ticket, figure out what kind of issue it is, look up the relevant policy, write a response, and decide if it needs to be escalated to a specialist. This takes 3-8 minutes per ticket just for categorization and hours for a first response.

## The Solution

We are building an AI-powered triage system that handles this entire workflow in under 15 seconds. It does not replace human agents — it does the repetitive work of reading, categorizing, looking up policies, and drafting responses so humans can focus on the cases that actually need human judgment.

## How It Works (The Pipeline)

A customer submits a ticket, and it flows through five specialized AI agents in sequence, like an assembly line:

1. **Security Guard** — Strips out sensitive data (card numbers, SSNs, phone numbers) and checks if the message is trying to trick the AI. Wraps the cleaned text in safety markers.

2. **Classifier** — Reads the cleaned ticket and decides: Is this Fraud, a Dispute, an Access Issue, or a General Inquiry? How urgent is it? Is the customer angry, distressed, or calm? How confident is the classification?

3. **Knowledge Retriever** — Searches the bank's policy library to find the 3-5 most relevant articles for this specific ticket.

4. **Response Drafter** — Writes a polite, empathetic customer response based on the retrieved policies. Adjusts tone to match the customer's emotional state.

5. **Compliance Critic** — Reviews the draft to make sure it does not promise anything the bank cannot deliver (specific refund amounts, guaranteed timelines). Decides whether it is safe to send directly or must go to a human.

6. **Security Guard (again)** — Does one final check for any sensitive data that might have slipped into the response, then writes an audit log.

## The Two Outcomes

Every ticket ends in exactly one of two places:

- **Auto-Response** — Safe, routine tickets (like fee inquiries) get answered directly. The customer sees the response immediately.
- **Human Escalation** — Risky, complex, or sensitive tickets (fraud, disputes, anything the AI is not confident about) go to a human agent with the AI's draft as a starting suggestion. The human decides what to send.

## The Key Safety Principle

The system is designed so that **the worst thing it can do is send a ticket to a human unnecessarily**. It can never send a wrong answer to a customer silently, because every uncertain or risky case gets escalated. Over-caution is cheap; a wrong answer to a fraud victim is expensive.
