"""Shared retry wrapper for Claude Agent SDK query() calls."""

from __future__ import annotations

import asyncio

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

_DELAYS = [2, 5, 10]


async def query_with_retry(prompt: str, options: ClaudeAgentOptions, max_retries: int = 3) -> str:
    """Call query() and retry on transient errors with exponential backoff."""
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            result_text = ""
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, ResultMessage):
                    result_text = message.result
            return result_text
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                wait = _DELAYS[min(attempt, len(_DELAYS) - 1)]
                print(f"  [retry {attempt + 1}/{max_retries}] transient error: {exc} — waiting {wait}s")
                await asyncio.sleep(wait)
    raise last_exc  # type: ignore[misc]
