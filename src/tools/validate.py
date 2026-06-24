"""Validate that a drafted segment is a real narration — not a model refusal or meta-text.

The Writer runs with no web tools and only a short RSS summary. When the source is too
thin (paywalled, truncated mid-sentence), the model sometimes returns a refusal or a
clarifying question — e.g. "I wasn't able to access the full article... could you paste
the full article text here?" — instead of narration. The Fact-checker only flags
unsupported *claims*, and a refusal makes no claims, so it passes and ships as content.

This guard catches those drafts so the pipeline can skip the story entirely.
"""
from __future__ import annotations

# Phrases that essentially never appear in a real spoken AI-news segment but are common
# in model refusals, clarifying questions, and meta-commentary. Matched case-insensitively
# as substrings.
_REFUSAL_MARKERS: tuple[str, ...] = (
    "i wasn't able to",
    "i was not able to",
    "i was unable to",
    "i'm unable to",
    "i am unable to",
    "i couldn't access",
    "i could not access",
    "i can't access",
    "i cannot access",
    "i don't have access",
    "i do not have access",
    "without access to",
    "unable to access",
    "couldn't retrieve",
    "could not retrieve",
    "could you paste",
    "please paste",
    "paste the full",
    "paste the article",
    "paste the complete",
    "share the full",
    "send me the article",
    "provide the full article",
    "once i have the",
    "if you can share",
    "if you paste",
    "i don't want to fabricate",
    "i do not want to fabricate",
    "risk putting misinformation",
    "i can't fabricate",
    "i cannot fabricate",
    "to avoid fabricating",
    "as an ai language model",
    "as an ai assistant",
    "i'm just an ai",
    "the summary cuts off",
    "summary is cut off",
    "cuts off mid-sentence",
    "web tools need",
    "permission grant",
    "in this environment",
    "i'm sorry, but i",
    "i apologize, but i",
    "unfortunately, i don't",
    "i'm not able to write",
    "i am not able to write",
)

# Below these word counts a draft is treated as broken/empty rather than a real segment.
_MIN_WORDS: dict[str, int] = {"lead": 60, "snippet": 25}


def is_valid_narration(draft: str | None, role: str) -> tuple[bool, str]:
    """Return (is_valid, reason). `reason` is '' when valid, else a short explanation."""
    if not draft or not draft.strip():
        return False, "empty draft"

    text = draft.strip()
    low = text.lower()

    for marker in _REFUSAL_MARKERS:
        if marker in low:
            return False, f'draft reads as a model refusal / meta-text (matched: "{marker}")'

    words = len(text.split())
    floor = _MIN_WORDS.get(role or "snippet", _MIN_WORDS["snippet"])
    if words < floor:
        return False, f"draft too short for a {role} ({words} words < {floor})"

    return True, ""
