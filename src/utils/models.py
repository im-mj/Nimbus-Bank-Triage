"""
Nimbus Bank Triage — LLM Client Wrappers

Centralized model configuration for Claude Haiku (fast tasks)
and Claude Sonnet (quality drafting), with retry logic.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

# Load env vars
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(ROOT_DIR, ".env"))

# ── Model IDs ────────────────────────────────────────────────
FAST_MODEL = os.environ.get("FAST_MODEL", "claude-haiku-4-5-20251001")
# Default the drafter to the same known-working model unless overridden by env.
DRAFTER_MODEL = os.environ.get("DRAFTER_MODEL", "claude-haiku-4-5-20251001")


def _get_anthropic_api_key() -> str:
    """Return a non-empty Anthropic API key or raise a clear config error."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not configured. Add it to your environment or Hugging Face Space secrets, then restart the app."
        )
    return api_key


def anthropic_api_key_configured() -> bool:
    """Whether a non-empty Anthropic API key is currently configured."""
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


@lru_cache(maxsize=4)
def _build_llm(model: str, temperature: float, max_tokens: int, api_key: str) -> ChatAnthropic:
    """Build and cache Anthropic chat clients by model settings and API key."""
    return ChatAnthropic(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
    )


@lru_cache(maxsize=1)
def get_fast_llm() -> ChatAnthropic:
    """
    Claude Haiku — used for classification, compliance checks,
    and injection detection. Low latency, low cost, deterministic.
    """
    return _build_llm(
        model=FAST_MODEL,
        temperature=0.0,
        max_tokens=1024,
        api_key=_get_anthropic_api_key(),
    )


@lru_cache(maxsize=1)
def get_drafter_llm() -> ChatAnthropic:
    """
    Claude Sonnet — used only by the Response Drafter.
    Higher quality for nuanced, empathetic customer responses.
    """
    return _build_llm(
        model=DRAFTER_MODEL,
        temperature=0.5,
        max_tokens=2048,
        api_key=_get_anthropic_api_key(),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def invoke_with_retry(llm: ChatAnthropic, messages: list) -> str:
    """
    Invoke an LLM with automatic retry on transient failures.
    Exponential backoff: 1s, 2s, 4s. Max 3 attempts.

    Returns the string content of the response.
    """
    response = llm.invoke(messages)
    return response.content


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def invoke_structured_with_retry(
    llm: ChatAnthropic,
    messages: list,
    schema: type,
) -> dict:
    """
    Invoke an LLM with structured output (Pydantic schema) and retry.
    Uses LangChain's with_structured_output for type-safe responses.

    Returns a dict matching the schema.
    """
    structured_llm = llm.with_structured_output(schema)
    response = structured_llm.invoke(messages)

    # Pydantic model -> dict
    if hasattr(response, "model_dump"):
        return response.model_dump()
    return response
