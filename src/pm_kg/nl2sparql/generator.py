"""Generate SPARQL from natural language using an LLM (Claude)."""

from __future__ import annotations

import re

from ..config import settings
from .prompt import build_prompt

_SPARQL_BLOCK = re.compile(r"```(?:sparql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _extract_sparql(text: str) -> str:
    """Pull the SPARQL out of a fenced code block, or return the text as-is."""
    match = _SPARQL_BLOCK.search(text)
    return (match.group(1) if match else text).strip()


def generate_sparql(question: str, model: str | None = None) -> str:
    """Ask the LLM to convert ``question`` into a SPARQL query.

    Requires ``ANTHROPIC_API_KEY``. Raises RuntimeError with a clear message if
    the key or the SDK is missing.
    """
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Export it to use natural-language "
            "questions, or pass raw SPARQL with `pm-kg query`."
        )

    try:
        from anthropic import Anthropic
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "The 'anthropic' package is required. Install with: pip install anthropic"
        ) from exc

    client = Anthropic(api_key=settings.anthropic_api_key)
    prompt = build_prompt(question)

    response = client.messages.create(
        model=model or settings.model,
        max_tokens=settings.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return _extract_sparql(text)
