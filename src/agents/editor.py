"""Editor agent: picks the lead story and ranks candidates as snippets."""

from __future__ import annotations

import asyncio
import json
from datetime import date

import yaml
from claude_agent_sdk import ClaudeAgentOptions

from src.state import DB, Story
from src.tools.retry import query_with_retry

_INSTRUCTIONS = (
    "You are the Editor for a daily AI-news brief. "
    "Pick the ONE most significant story of the day as the lead — biggest impact on people "
    "building with or affected by AI. Then select up to 10–15 more as snippets, ordered by "
    "importance. Dedupe near-identical stories. Flex the snippet count with news quality. "
    "Drop the rest.\n\n"
    "Return ONLY a JSON object with no commentary or code fences:\n"
    '{"lead": "<story_id>", "snippets": ["<id>", ...], "dropped": ["<id>", ...]}\n'
    "Use the exact id values from the input. Do not explain your choices."
)


async def _call_editor(prompt: str) -> str:
    return await query_with_retry(prompt, ClaudeAgentOptions(allowed_tools=[]))


def run(run_date: str | None = None) -> tuple[Story, list[Story]]:
    """Rank candidates: returns (lead_story, [snippet_stories]) and persists to DB."""
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    today = run_date or date.today().isoformat()
    db = DB()
    candidates = db.by_date(today, status="candidate")

    if not candidates:
        db.close()
        raise RuntimeError(f"No candidate stories for {today}. Run Scout first.")

    print(f"Editor ranking {len(candidates)} candidates …")

    item_list = [
        {"id": s.id, "title": s.title, "source": s.source, "summary": s.raw_summary[:300]}
        for s in candidates
    ]
    prompt = (
        f"Today's date: {today}\n\n"
        f"Candidate stories:\n{json.dumps(item_list, indent=2)}"
    )

    raw = asyncio.run(_call_editor(_INSTRUCTIONS + "\n\n" + prompt)).strip()
    # Strip markdown code fences (``` or ```json)
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(l for l in lines if not l.startswith("```")).strip()

    if not raw:
        raise RuntimeError("Editor returned empty response — try re-running.")

    decision: dict = json.loads(raw)
    lead_id = decision["lead"]
    snippet_ids: list[str] = decision.get("snippets", [])
    dropped_ids: list[str] = decision.get("dropped", [])

    by_id = {s.id: s for s in candidates}

    lead_story: Story | None = None
    snippet_stories: list[Story] = []

    for s in candidates:
        if s.id == lead_id:
            s.role = "lead"
            s.status = "ranked"
            lead_story = s
        elif s.id in snippet_ids:
            s.role = "snippet"
            s.status = "ranked"
            snippet_stories.append(s)
        else:
            s.role = "dropped"
            s.status = "ranked"
        db.upsert(s)

    # Preserve the Editor's snippet ordering
    order = {sid: i for i, sid in enumerate(snippet_ids)}
    snippet_stories.sort(key=lambda s: order.get(s.id, 999))

    db.close()

    if lead_story is None:
        raise RuntimeError(f"Editor returned lead id '{lead_id}' not found in candidates.")

    return lead_story, snippet_stories


if __name__ == "__main__":
    lead, snippets = run()
    print(f"\n=== LEAD ===")
    print(f"[{lead.source}] {lead.title}")
    print(f"  {lead.url}")
    print(f"\n=== SNIPPETS ({len(snippets)}) ===")
    for i, s in enumerate(snippets, 1):
        print(f"{i:2}. [{s.source}] {s.title}")
        print(f"    {s.url}")
