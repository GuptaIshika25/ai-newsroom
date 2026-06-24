"""Feedparser wrapper: fetch recent items from RSS/Atom feeds."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import TypedDict

import feedparser
from dateutil import parser as dateparser


class RawItem(TypedDict):
    title: str
    url: str
    source: str
    published: str       # ISO-8601 string
    raw_summary: str
    score: int


def _parse_date(entry) -> datetime | None:
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if val:
            try:
                dt = dateparser.parse(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (ValueError, TypeError):
                continue
    return None


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _score(title: str, summary: str, keywords: list[str]) -> int:
    blob = f"{title} {summary}".lower()
    return sum(1 for kw in keywords if kw.lower() in blob)


def fetch(config: dict) -> list[RawItem]:
    """Fetch all candidate items from configured RSS feeds.

    Returns items published within lookback_hours that match at least one
    keyword. No cap on count — the Scout agent does the curation.
    """
    nl = config["newsletter"]
    keywords = config["relevance_keywords"]
    exclude = [e.lower() for e in config.get("exclude_keywords", [])]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=nl["lookback_hours"])

    seen: dict[str, RawItem] = {}

    for feed in config["feeds"]:
        try:
            parsed = feedparser.parse(feed["url"])
        except Exception as exc:
            print(f"  ! feed error [{feed['name']}]: {exc}")
            continue

        for entry in parsed.entries:
            published = _parse_date(entry)
            if published is None or published < cutoff:
                continue

            title = _clean(entry.get("title", ""))
            summary = _clean(entry.get("summary", ""))[:800]
            url = entry.get("link", "")
            if not title or not url:
                continue

            blob_l = f"{title} {summary}".lower()
            if any(bad in blob_l for bad in exclude):
                continue  # war / conflict / geopolitics — out of scope, even if AI-related

            score = _score(title, summary, keywords)
            if score == 0:
                continue

            item: RawItem = {
                "title": title,
                "url": url,
                "source": feed["name"],
                "published": published.isoformat(),
                "raw_summary": summary,
                "score": score,
            }

            uid = url.strip()
            if uid not in seen or seen[uid]["score"] < score:
                seen[uid] = item

    items = sorted(seen.values(), key=lambda x: x["score"], reverse=True)

    # Cap per-source dominance so no single outlet floods the candidate pool.
    # Items are score-desc, so each source keeps its highest-scoring items.
    cap = config.get("max_per_source")
    if cap:
        per_source: dict[str, int] = {}
        capped: list[RawItem] = []
        for it in items:
            src = it["source"]
            if per_source.get(src, 0) >= cap:
                continue
            per_source[src] = per_source.get(src, 0) + 1
            capped.append(it)
        items = capped

    return items
