"""Turn raw stories into punchy TLDRs and a daily intro using Claude."""
from __future__ import annotations

import json
import os

from fetch import Story

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

_SYSTEM = (
    "You are the editor of 'AI TLDR', a sharp daily AI news brief for busy "
    "product people. You write tight, neutral, jargon-light summaries. No hype, "
    "no filler, no emoji. Every TLDR is one or two sentences and explains why it "
    "matters."
)


def _client():
    import anthropic

    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def summarize_stories(stories: list[Story]) -> list[Story]:
    """Fill each story's .tldr field. One batched call for efficiency."""
    if not stories:
        return stories

    client = _client()
    items = [
        {"id": i, "title": s.title, "source": s.source, "blurb": s.summary}
        for i, s in enumerate(stories)
    ]
    prompt = (
        "Write a one-to-two sentence TLDR for each story below. Focus on what "
        "happened and why it matters to someone building AI products. Return "
        "ONLY valid JSON: a list of objects with keys 'id' and 'tldr'.\n\n"
        f"{json.dumps(items, indent=2)}"
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    text = text[text.find("[") : text.rfind("]") + 1]  # strip any prose
    for obj in json.loads(text):
        stories[obj["id"]].tldr = obj["tldr"].strip()
    return stories


def write_intro(stories: list[Story]) -> str:
    """A 2-3 sentence editor's note tying the day's stories together."""
    if not stories:
        return "Quiet day in AI — nothing major broke through the noise."
    client = _client()
    headlines = "\n".join(f"- {s.title}" for s in stories)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    "Write a 2-3 sentence editor's intro for today's brief based "
                    "on these headlines. Set the scene, name the through-line if "
                    "there is one. No greeting, no signoff.\n\n" + headlines
                ),
            }
        ],
    )
    return resp.content[0].text.strip()
