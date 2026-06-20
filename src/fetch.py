"""Fetch and rank recent AI news from RSS/Atom feeds."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import feedparser
from dateutil import parser as dateparser


@dataclass
class Story:
    title: str
    url: str
    source: str
    published: datetime
    summary: str = ""
    score: int = 0
    tldr: str = field(default="")  # filled in later by the summarizer

    @property
    def uid(self) -> str:
        return hashlib.sha1(self.url.encode("utf-8")).hexdigest()[:12]


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


def fetch_stories(config: dict) -> list[Story]:
    nl = config["newsletter"]
    keywords = config["relevance_keywords"]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=nl["lookback_hours"])

    stories: dict[str, Story] = {}
    for feed in config["feeds"]:
        try:
            parsed = feedparser.parse(feed["url"])
        except Exception as e:  # noqa: BLE001
            print(f"  ! failed to parse {feed['name']}: {e}")
            continue

        for entry in parsed.entries:
            published = _parse_date(entry)
            if published is None or published < cutoff:
                continue
            title = _clean(entry.get("title", ""))
            summary = _clean(entry.get("summary", ""))[:600]
            url = entry.get("link", "")
            if not title or not url:
                continue
            score = _score(title, summary, keywords)
            if score == 0:
                continue  # not AI-relevant enough
            story = Story(
                title=title,
                url=url,
                source=feed["name"],
                published=published,
                summary=summary,
                score=score,
            )
            # dedupe by url; keep the higher-scored copy
            if story.uid not in stories or stories[story.uid].score < score:
                stories[story.uid] = story

    ranked = sorted(
        stories.values(),
        key=lambda s: (s.score, s.published),
        reverse=True,
    )
    return ranked[: nl["max_stories"]]


if __name__ == "__main__":
    import yaml

    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
    items = fetch_stories(cfg)
    print(f"Fetched {len(items)} stories:")
    for s in items:
        print(f"  [{s.score}] {s.source}: {s.title}")
