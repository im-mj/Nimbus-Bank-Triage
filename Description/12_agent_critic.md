# Step 12 — Compliance Critic Agent (The Final Gatekeeper)

## What This Does

Before any response leaves the system — whether to a customer directly or to a human agent's queue — the Compliance Critic reviews it. Its single job is to answer one question: "Is this response safe to send, or does it need a human to review it first?"

Think of it as the bank's compliance officer reading every outgoing letter before it gets mailed. The Critic has veto power over the entire pipeline.

## How It Works in Plain English

The Critic examines the Drafter's response against two sets of rules:

**Hard Block Rules (content violations):**
Any single violation forces escalation, no exceptions.
- The response mentions a specific refund amount ("we will refund $247.50").
- The response guarantees a resolution timeline ("this will be fixed within 24 hours").
- The response waives a fee or issues a credit.
- The response confirms or denies that a specific account exists (this is a security attack vector).
- The response makes a loan or credit decision.
- The response admits legal liability on behalf of the bank.

**Soft Signal Rules (situational escalation):**
Any single signal forces escalation, regardless of how good the response is.
- The ticket is categorized as Fraud or Dispute — these always require a human.
- The urgency is Critical.
- The Classifier's confidence is below 70.
- The Security Agent flagged a possible injection attempt.

**The Revision Option:**
If the draft fails only because of a fixable content issue (like accidentally mentioning a dollar amount), the Critic can send it back to the Drafter with specific feedback: "Remove the refund amount in paragraph 2." The Drafter gets one chance to fix it. If the revision also fails, the ticket escalates — no second chances.

## Why This Design

- **Low autonomy, high authority.** The Critic cannot rewrite the response. It cannot decide what to say. But it has absolute veto power over sending anything. Any uncertainty resolves to "send it to a human."
- **Rules, not judgment calls.** The hard block rules are explicit patterns, not subjective assessments. "Contains a dollar amount near the word refund" is a checkable rule. This makes the Critic predictable and auditable.
- **The bounded revision loop.** One retry, no more. This prevents the Drafter and Critic from going back and forth forever, which would be expensive and slow. Two failed drafts means escalation.
- **The safety default.** When in doubt, escalate. The worst outcome is a human reviews a ticket that could have been auto-answered. The best outcome is a human catches something the AI missed.
