"""Critique loop: Writer → Fact-checker, with a MAX_REVISIONS cap and lead-promotion fallback."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from src.agents import factchecker
from src.state import DB, Story

MAX_REVISIONS = 2

_REVISE_INSTRUCTIONS = (
    "You are the Writer for a daily AI-news audio brief. "
    "The Fact-checker rejected your draft for the reasons listed below. "
    "Revise the narration to fix every issue, keeping the same conversational read-aloud style "
    "and staying within the original word-count range. "
    "Output only the revised narration text, nothing else."
)

_LEAD_RANGE = "450–750 words"
_SNIPPET_RANGE = "120–150 words"


@dataclass
class LoopResult:
    story: Story
    outcome: str          # "approved" | "dropped"
    revisions_made: int
    notes: str


async def _revise(story: Story, reject_notes: str) -> str:
    word_range = _LEAD_RANGE if story.role == "lead" else _SNIPPET_RANGE
    prompt = (
        _REVISE_INSTRUCTIONS
        + f"\n\nWord-count target: {word_range}"
        + f"\n\nFact-checker notes:\n{reject_notes}"
        + f"\n\nOriginal draft:\n{story.draft}"
        + f"\n\nSource:\n{story.raw_summary}"
    )
    result_text = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(allowed_tools=[]),
    ):
        if isinstance(message, ResultMessage):
            result_text = message.result
    return result_text.strip()


def run_story(story: Story, db: DB) -> LoopResult:
    """Run the Writer→Fact-checker loop for one story. Mutates story and persists."""
    label = f"[{story.role.upper()}] {story.title[:55]}..."

    for attempt in range(MAX_REVISIONS + 1):
        approved, notes = factchecker.verify(story)

        if approved:
            story.verified = True
            story.verify_notes = notes
            story.status = "verified"
            db.upsert(story)
            action = "approved on first check" if attempt == 0 else f"approved after {attempt} revision(s)"
            print(f"  PASS ({action}): {label}")
            return LoopResult(story=story, outcome="approved", revisions_made=attempt, notes=notes)

        # Rejected
        if attempt == MAX_REVISIONS:
            # Hit the cap — drop this story
            story.role = "dropped"
            story.verified = False
            story.verify_notes = notes
            story.status = "ranked"   # un-draft so it won't enter producer
            db.upsert(story)
            print(f"  DROP (failed after {MAX_REVISIONS} revision(s)): {label}")
            return LoopResult(story=story, outcome="dropped", revisions_made=attempt, notes=notes)

        # Send back to Writer for a revision
        print(f"  REJECT (revision {attempt + 1}/{MAX_REVISIONS}): {label}")
        revised = asyncio.run(_revise(story, notes))
        if revised:
            story.draft = revised
            story.revisions += 1
            db.upsert(story)

    # Unreachable, but satisfies type-checker
    return LoopResult(story=story, outcome="dropped", revisions_made=MAX_REVISIONS, notes="")


def run(run_date: str | None = None) -> list[LoopResult]:
    """Run the critique loop for all drafted stories; handle lead demotion if needed."""
    today = run_date or date.today().isoformat()
    db = DB()

    drafted = db.by_date(today, status="drafted")
    if not drafted:
        db.close()
        raise RuntimeError(f"No drafted stories for {today}. Run Writer first.")

    lead = next((s for s in drafted if s.role == "lead"), None)
    snippets = [s for s in drafted if s.role == "snippet"]

    results: list[LoopResult] = []

    # Check lead first
    if lead:
        print(f"\nChecking lead ...")
        r = run_story(lead, db)
        results.append(r)

        # If lead is dropped, promote top snippet
        if r.outcome == "dropped":
            ranked_snippets = sorted(snippets, key=lambda s: s.score, reverse=True)
            if ranked_snippets:
                promoted = ranked_snippets[0]
                snippets = ranked_snippets[1:]
                print(f"  PROMOTE snippet to lead: [{promoted.source}] {promoted.title[:55]}...")
                promoted.role = "lead"
                db.upsert(promoted)
                print(f"\nChecking (promoted) lead ...")
                r2 = run_story(promoted, db)
                results.append(r2)
            else:
                print("  WARNING: lead dropped and no snippets to promote.")

    # Check snippets
    for i, s in enumerate(snippets, 1):
        print(f"\nChecking snippet {i}/{len(snippets)} ...")
        results.append(run_story(s, db))

    db.close()
    return results


if __name__ == "__main__":
    results = run()

    approved = [r for r in results if r.outcome == "approved"]
    dropped  = [r for r in results if r.outcome == "dropped"]
    revised  = [r for r in results if r.revisions_made > 0 and r.outcome == "approved"]

    print(f"\n{'='*60}")
    print(f"CRITIQUE LOOP SUMMARY")
    print(f"{'='*60}")
    print(f"Total checked : {len(results)}")
    print(f"Approved      : {len(approved)}")
    print(f"Dropped       : {len(dropped)}")
    print(f"Needed revisions: {len(revised)}")

    if revised:
        print("\nRevised stories:")
        for r in revised:
            print(f"  ({r.revisions_made} rev) [{r.story.role}] {r.story.title[:60]}")

    if dropped:
        print("\nDropped stories:")
        for r in dropped:
            print(f"  [{r.story.role}] {r.story.title[:60]}")
            print(f"    Reason: {r.notes[:120]}")

    print(f"\nVerified line-up:")
    final = db_verified = None
    from src.state import DB
    _db = DB()
    verified_stories = _db.by_date(date.today().isoformat(), status="verified")
    _db.close()
    lead_v = next((s for s in verified_stories if s.role == "lead"), None)
    snippets_v = [s for s in verified_stories if s.role == "snippet"]
    if lead_v:
        print(f"  LEAD: [{lead_v.source}] {lead_v.title}")
    for i, s in enumerate(snippets_v, 1):
        print(f"  {i:2}. [{s.source}] {s.title}")
