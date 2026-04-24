# Step 6 — LLM Client Wrappers (The AI Connection Layer)

## What This Does

The system uses two different AI models from Anthropic for different tasks — a fast, cheap model (Claude Haiku) for quick decisions like classification and compliance checks, and a more capable model (Claude Sonnet) for the nuanced work of writing customer responses. It also uses an OpenAI model purely for converting text into searchable mathematical representations (embeddings).

The LLM client module provides clean, reusable connection wrappers so every agent in the system can call the right model without worrying about API keys, retry logic, or error handling.

## How It Works in Plain English

The module sets up three things:

1. **A fast model client (Claude Haiku)** — Used by the Classifier, the Compliance Critic, and the injection detection check. These tasks need speed and consistency more than creative writing ability. Haiku responds in under a second and costs a fraction of a cent per call. Temperature is set to 0.0 (completely deterministic — same input always gives the same output).

2. **A quality model client (Claude Sonnet)** — Used only by the Response Drafter. Writing an empathetic, well-toned customer response requires the stronger model's ability to handle nuance. Temperature is set to 0.5 (a balance between consistency and natural-sounding variation).

3. **Retry logic** — If the AI service is temporarily unavailable or returns an error, the client automatically retries with increasing wait times (exponential backoff). It tries a maximum of 2 times before giving up and escalating the ticket to a human instead.

All API keys are loaded from environment variables at startup — they never appear in the code.

## Why This Design

- **Right model for the right job.** Using the expensive model everywhere would be wasteful. Using the cheap model everywhere would produce robotic-sounding customer responses. Each model is matched to the task that suits its strengths.
- **Centralized configuration.** If we need to change which model is used for a task, we change it in one place, not in every agent file.
- **Built-in resilience.** API outages happen. The retry logic absorbs transient failures silently. Persistent failures escalate the ticket to a human — the system never hangs or crashes.
- **Cost awareness.** By separating the clients, we can track token usage per model and calculate the cost per ticket accurately.
