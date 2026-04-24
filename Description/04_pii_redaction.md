# Step 4 — PII Redaction (The Privacy Shield)

## What This Does

Customers often include sensitive personal information in their support tickets — credit card numbers, Social Security numbers, phone numbers, email addresses. This information must never reach the AI models, must never appear in logs, and must never be included in any response sent back to the customer.

The PII redaction module is a set of pattern-matching rules that automatically finds and replaces sensitive data with safe placeholder tags before any AI agent ever sees the text.

## How It Works in Plain English

When a ticket comes in, the redaction module scans the text for specific patterns:

- **Credit/debit card numbers** — Any sequence of 13 to 19 digits, with or without dashes or spaces. Replaced with `[CARD_REDACTED]`.
- **Social Security numbers** — The pattern XXX-XX-XXXX or nine consecutive digits. Replaced with `[SSN_REDACTED]`.
- **Phone numbers** — Common US formats like (214) 555-0198, 214-555-0198, or +1 2145550198. Replaced with `[PHONE_REDACTED]`.
- **Email addresses** — Anything that looks like name@domain.com. Replaced with `[EMAIL_REDACTED]`.
- **Bank routing numbers** — Nine-digit sequences that match the routing number format. Replaced with `[ROUTING_REDACTED]`.
- **Account numbers** — Sequences of 8-17 digits that appear near words like "account" or "acct." Replaced with `[ACCOUNT_REDACTED]`.

The module returns two things: the cleaned text (safe to send to the AI) and a list of flags noting what types of PII were found (e.g., ["card_number", "phone"]). The flags go into the audit log so compliance knows what was in the ticket, but the actual values are gone forever from the pipeline.

## Why This Design

- **Runs before any AI sees the text.** The very first thing that happens to a ticket is PII removal. No LLM ever processes raw customer data.
- **Deterministic, not AI-based.** Regex patterns are predictable, fast, and auditable. You can prove exactly what they match and what they miss. An AI-based approach would be a black box.
- **Runs twice.** Once on the input (before the pipeline) and once on the output (before the response leaves the system). This catches any PII the Drafter might accidentally echo.
- **No false sense of security.** The module catches the most common PII patterns. It is not perfect — an unusual format might slip through. That is why it is one layer of defense, not the only one.
