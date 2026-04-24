# Step 2 — The Knowledge Base (The Bank's Policy Library)

## What This Does

When a customer writes in with a question or problem, the AI cannot just make up answers — it needs to refer to actual bank policies. The knowledge base is Nimbus Bank's internal library of 20 policy and FAQ articles that the system searches through to find the right information before writing a response.

Think of it like a well-organized filing cabinet that a human support agent would flip through to find the right answer. Except here, the AI searches it in milliseconds.

## What's Inside

The 20 articles are organized into four categories, matching the four types of tickets the system handles:

**Fraud (5 articles)** — What to do when someone uses your card without permission. Covers reporting steps, federal timelines (Regulation E), liability rules, and prevention tips.

**Disputes (4 articles)** — What to do when you made a purchase but want your money back. Covers the chargeback process, timelines, goods-not-received claims, and duplicate charges.

**Access Issues (6 articles)** — What to do when you can't get into your account. Covers password resets, PIN recovery, account lockouts, mobile app problems, two-factor authentication setup, and forgotten usernames.

**General Inquiries (5 articles)** — Everyday banking questions. Covers fees, account types, transfer limits, branch hours, and how to download statements.

## How It Works in Plain English

Each article is stored with its text content plus metadata tags — its category, subcategory, relevant keywords, and whether it requires human escalation. When a customer ticket comes in, the system converts the ticket text into a mathematical representation (called an embedding) and finds the articles whose representations are most similar. This is how the system "searches by meaning" rather than by exact keyword match — so a customer saying "someone stole my card" correctly matches the fraud articles even though the word "fraud" never appears in the ticket.

## Why This Design

- **Grounded responses.** The AI can only cite information that exists in these articles, which prevents it from making up policies or promising things the bank doesn't offer.
- **Auditable.** Every response references specific article IDs, so a compliance officer can verify exactly what policy the AI relied on.
- **All synthetic.** These are fabricated articles for a fictional bank — no real bank data is used anywhere.
- **Easy to update.** Adding a new policy is just adding a new article to the JSON file and re-indexing.
