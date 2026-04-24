# Step 16 — Graph Flow Visualization (The Pipeline Map)

## What This Does

This is a visual map of how tickets flow through the system. Every possible path a ticket can take is shown here — from the moment it enters to the moment it exits.

## The Flow

```
START
  │
  ▼
┌─────────────┐
│ security_in  │  ← PII redaction + injection detection
└──────┬───────┘
       │
       ├──── injection_score > 0.80 ────────────────────┐
       │                                                 │
       ▼                                                 │
┌─────────────┐                                          │
│  classifier  │  ← category, urgency, sentiment         │
└──────┬───────┘                                          │
       │                                                 │
       ▼                                                 │
┌─────────────┐                                          │
│  retriever   │  ← search KB, return top-5 articles     │
└──────┬───────┘                                          │
       │                                                 │
       ▼                                                 │
┌─────────────┐                                          │
│   drafter    │  ← write customer response      ◄──┐   │
└──────┬───────┘                                     │   │
       │                                             │   │
       ▼                                             │   │
┌─────────────┐                                      │   │
│    critic    │  ← compliance check                 │   │
└──────┬───────┘                                      │   │
       │                                             │   │
       ├── safe_to_send = true ──────────┐           │   │
       │                                 │           │   │
       ├── fixable + iteration ≤ 1 ──────┘ (revise) │   │
       │                                             │   │
       ├── not fixable / cap exceeded ──┐            │   │
       │                                │                │
       ▼                                ▼            ▼   │
                              ┌─────────────┐            │
                              │ security_out │ ◄─────────┘
                              └──────┬───────┘
                                     │
                                     ▼
                                    END
```

## The Three Paths

**Path 1: Auto-Response (Happy Path)**
`security_in → classifier → retriever → drafter → critic (safe) → security_out → END`
The ticket is a simple inquiry, the response passes compliance, and the customer gets an immediate answer.

**Path 2: Escalation**
`security_in → classifier → retriever → drafter → critic (not safe) → security_out → END`
The ticket involves fraud, a dispute, or the draft had an unfixable issue. It goes to a human agent with the AI's draft as a starting suggestion.

**Path 3: Injection Short-Circuit**
`security_in → security_out → END`
The ticket is a suspected prompt injection attack. It skips the entire pipeline and goes straight to a security review queue.

**Path 4: Revision Loop (Rare)**
`... → drafter → critic (fixable) → drafter → critic → security_out → END`
The first draft had a minor issue (like mentioning a dollar amount). The Critic sends it back once. If the second draft passes, it auto-sends. If not, it escalates.

## Key Guarantee

Every possible path ends at `security_out → END`. There is no way for a ticket to get stuck in an infinite loop, skip the exit checkpoint, or leave the system without being logged.
