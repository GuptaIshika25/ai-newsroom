"""Writer agent: drafts the lead segment and snippet narrations."""

from __future__ import annotations

import asyncio
from datetime import date

import time

from claude_agent_sdk import ClaudeAgentOptions

from src.state import DB, Story
from src.tools.retry import query_with_retry

_LEAD_INSTRUCTIONS = (
    "You are the Writer for a daily AI-news audio brief. "
    "Write a 3–5 minute spoken segment (450–750 words) on the story below. "
    "Cover: what happened, the context a busy professional lacks, why it matters, "
    "and the implication. "
    "Conversational, sharp, no hype, no bullet points — it will be read aloud by a voice AI. "
    "No headers, no lists. Just flowing spoken prose. "
    "Output only the narration text, nothing else."
)

_SNIPPET_INSTRUCTIONS = (
    "You are the Writer for a daily AI-news audio brief. "
    "Write a ~1-minute spoken snippet (120–150 words) on the story below. "
    "Cover: the headline fact, the gist, and why a busy professional should care. "
    "One tight paragraph, read-aloud friendly, no bullet points, no headers. "
    "Output only the narration text, nothing else."
)


async def _draft(instructions: str, story_block: str) -> str:
    result = await query_with_retry(
        instructions + "\n\nStory:\n" + story_block,
        ClaudeAgentOptions(allowed_tools=[]),
    )
    return result.strip()


def _story_block(s: Story) -> str:
    return f"Title: {s.title}\nSource: {s.source}\nURL: {s.url}\nSummary: {s.raw_summary}"


def run(run_date: str | None = None) -> tuple[Story, list[Story]]:
    """Draft lead and all snippets; returns (lead, [snippets]) with .draft populated."""
    today = run_date or date.today().isoformat()
    db = DB()

    ranked = db.by_date(today, status="ranked")
    if not ranked:
        db.close()
        raise RuntimeError(f"No ranked stories for {today}. Run Editor first.")

    lead = next((s for s in ranked if s.role == "lead"), None)
    snippets = sorted(
        [s for s in ranked if s.role == "snippet"],
        key=lambda s: s.score,
        reverse=True,
    )

    if lead is None:
        db.close()
        raise RuntimeError("No lead story found in ranked results.")

    # Draft the lead
    print(f"Writing lead: \"{lead.title[:60]}...\"")
    lead.draft = asyncio.run(_draft(_LEAD_INSTRUCTIONS, _story_block(lead)))
    lead.status = "drafted"
    db.upsert(lead)

    # Draft each snippet
    for i, s in enumerate(snippets, 1):
        time.sleep(1.5)
        print(f"Writing snippet {i}/{len(snippets)}: \"{s.title[:55]}...\"")
        s.draft = asyncio.run(_draft(_SNIPPET_INSTRUCTIONS, _story_block(s)))
        s.status = "drafted"
        db.upsert(s)

    db.close()
    return lead, snippets


if __name__ == "__main__":
    lead, snippets = run()

    words = len(lead.draft.split()) if lead.draft else 0
    print(f"\n{'='*60}")
    print(f"LEAD DRAFT  ({words} words)")
    print(f"{'='*60}")
    print(f"[{lead.source}] {lead.title}\n")
    print(lead.draft)

    if snippets:
        s = snippets[0]
        sw = len(s.draft.split()) if s.draft else 0
        print(f"\n{'='*60}")
        print(f"SAMPLE SNIPPET  ({sw} words) — snippet 1 of {len(snippets)}")
        print(f"{'='*60}")
        print(f"[{s.source}] {s.title}\n")
        print(s.draft)
