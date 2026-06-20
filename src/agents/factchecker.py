"""Fact-checker agent: verifies each draft against its source summary."""

from __future__ import annotations

import asyncio

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from src.state import Story

_INSTRUCTIONS = (
    "You are the Fact-checker for a daily AI-news audio brief. "
    "Compare the draft narration to the source text provided. "
    "Flag any claim, number, name, date, or company that is not supported by the source, "
    "and anything that overstates or contradicts it. "
    "If all claims are supported (minor stylistic inference is fine), reply with exactly: APPROVED\n"
    "Otherwise reply with: REJECTED\n"
    "followed by a short numbered list of specific fixes needed. "
    "Be strict about facts but do not penalise reasonable journalistic framing."
)


async def _check(story: Story) -> str:
    prompt = (
        _INSTRUCTIONS
        + f"\n\nTitle: {story.title}"
        + f"\nSource URL: {story.url}"
        + f"\nSource text:\n{story.raw_summary}"
        + f"\n\nDraft narration:\n{story.draft}"
    )
    result_text = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(allowed_tools=[]),
    ):
        if isinstance(message, ResultMessage):
            result_text = message.result
    return result_text.strip()


def verify(story: Story) -> tuple[bool, str]:
    """Run fact-check on story.draft. Returns (approved, notes)."""
    raw = asyncio.run(_check(story))
    approved = raw.upper().startswith("APPROVED")
    return approved, raw
