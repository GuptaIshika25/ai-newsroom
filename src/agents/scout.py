"""Scout agent: fetches RSS feeds and uses the Claude Agent SDK (Claude Pro plan) to filter
for AI-relevant stories. No API key required — uses the local claude CLI credentials."""

from __future__ import annotations

import asyncio
import json
from datetime import date

import yaml
from claude_agent_sdk import ClaudeAgentOptions

from src.state import DB, Story
from src.tools import feeds
from src.tools.retry import query_with_retry

_PROMPT_TEMPLATE = """\
You are the Scout for a daily AI-news brief. Today's date: {today}.

From the items below, keep only those genuinely about AI — model launches, research,
policy/regulation, funding, layoffs, notable product moves.
Drop off-topic items, ads, and duplicates.

HARD EXCLUDE — never keep these, even when AI is involved: war, armed conflict, military
operations, weapons, terrorism, and diplomatic or geopolitical disputes. This is a tech
and business brief, not world news. (AI regulation, AI law, antitrust, and chip/export
policy ARE in scope; anything battlefield, military, or conflict-related is NOT.)

Return ONLY a JSON array with no commentary, markdown, or code fences.
Each element must have exactly these keys:
  "title"  — the item title (string)
  "url"    — the item url (string)
  "source" — the feed source name (string)
  "why"    — one-line reason it's relevant (string)

Items to evaluate:
{items_json}
"""


async def _run_scout(prompt: str) -> str:
    """Call the Claude Agent SDK and return the final result text."""
    return await query_with_retry(prompt, ClaudeAgentOptions(allowed_tools=[]))


def _extract_json_array(text: str) -> str:
    """Pull just the JSON array out of the model's reply.

    Strips markdown fences and any prose before/after by slicing from the
    first '[' to the last ']'. Returns the original text if no array is found.
    """
    if text.startswith("```"):
        text = "\n".join(l for l in text.splitlines() if not l.startswith("```")).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _parse_kept(raw_text: str) -> list[dict]:
    """Parse Scout's reply into a list of kept items, tolerating malformed JSON.

    First tries to extract and parse the array directly. If that fails (e.g. a
    missing comma or an unescaped quote in a title), re-asks the model once to
    repair its own output into valid JSON before giving up.
    """
    try:
        return json.loads(_extract_json_array(raw_text))
    except json.JSONDecodeError as exc:
        print(f"  Scout returned invalid JSON ({exc}) — asking it to repair and retrying once …")
        repair_prompt = (
            "The following was supposed to be a JSON array but is malformed. "
            "Return ONLY the corrected, valid JSON array — no commentary, markdown, "
            "or code fences. Keep the same items and keys; just fix the JSON.\n\n"
            f"{raw_text}"
        )
        repaired = asyncio.run(_run_scout(repair_prompt)).strip()
        return json.loads(_extract_json_array(repaired))


def run(run_date: str | None = None) -> list[Story]:
    """Fetch feeds, filter with Claude (via Agent SDK / Claude Pro plan), persist candidates."""
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    today = run_date or date.today().isoformat()

    print("Fetching feeds …")
    raw_items = feeds.fetch(config)
    print(f"  {len(raw_items)} keyword-matched items from {len(config['feeds'])} feeds")

    if not raw_items:
        print("  No items found — try extending lookback_hours in config.yaml")
        return []

    item_list = [
        {
            "idx": i,
            "title": r["title"],
            "url": r["url"],
            "source": r["source"],
            "summary": r["raw_summary"][:300],
        }
        for i, r in enumerate(raw_items)
    ]

    prompt = _PROMPT_TEMPLATE.format(
        today=today,
        items_json=json.dumps(item_list, indent=2),
    )

    print("Calling Scout (Claude Agent SDK / Claude Pro plan) …")
    raw_text = asyncio.run(_run_scout(prompt)).strip()

    kept: list[dict] = _parse_kept(raw_text)

    url_index = {r["url"]: r for r in raw_items}

    db = DB()
    stories: list[Story] = []
    for item in kept:
        url = item["url"]
        raw = url_index.get(url, {})
        story = Story(
            id=Story.make_id(url),
            run_date=today,
            source=item.get("source", raw.get("source", "")),
            title=item["title"],
            url=url,
            published=raw.get("published", ""),
            raw_summary=raw.get("raw_summary", ""),
            score=raw.get("score", 0),
            status="candidate",
        )
        db.upsert(story)
        stories.append(story)
    db.close()

    return stories


if __name__ == "__main__":
    stories = run()
    print(f"\n=== {len(stories)} candidate stories ===\n")
    for s in stories:
        print(f"[{s.source}] {s.title}")
        print(f"  {s.url}")
        print()
