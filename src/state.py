"""SQLite persistence layer and Story model."""

import sqlite3
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "newsroom.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS stories (
  id TEXT,
  run_date TEXT,
  source TEXT,
  title TEXT,
  url TEXT,
  published TEXT,
  raw_summary TEXT,
  score INTEGER,
  role TEXT,
  draft TEXT,
  verified INTEGER DEFAULT 0,
  verify_notes TEXT,
  revisions INTEGER DEFAULT 0,
  status TEXT DEFAULT 'candidate',
  PRIMARY KEY (id, run_date)
);
"""


@dataclass
class Story:
    id: str
    run_date: str
    source: str
    title: str
    url: str
    published: str = ""
    raw_summary: str = ""
    score: int = 0
    role: Optional[str] = None          # lead | snippet | dropped
    draft: Optional[str] = None
    verified: bool = False
    verify_notes: Optional[str] = None
    revisions: int = 0
    status: str = "candidate"           # candidate → ranked → drafted → verified → produced

    @staticmethod
    def make_id(url: str) -> str:
        return hashlib.sha1(url.encode()).hexdigest()[:12]


class DB:
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.con = sqlite3.connect(str(path))
        self.con.row_factory = sqlite3.Row
        self.con.executescript(_SCHEMA)
        self.con.commit()

    def upsert(self, story: Story) -> None:
        self.con.execute(
            """
            INSERT INTO stories
              (id, run_date, source, title, url, published, raw_summary,
               score, role, draft, verified, verify_notes, revisions, status)
            VALUES
              (:id, :run_date, :source, :title, :url, :published, :raw_summary,
               :score, :role, :draft, :verified, :verify_notes, :revisions, :status)
            ON CONFLICT(id, run_date) DO UPDATE SET
              source=excluded.source, title=excluded.title, url=excluded.url,
              published=excluded.published, raw_summary=excluded.raw_summary,
              score=excluded.score, role=excluded.role, draft=excluded.draft,
              verified=excluded.verified, verify_notes=excluded.verify_notes,
              revisions=excluded.revisions, status=excluded.status
            """,
            {
                "id": story.id,
                "run_date": story.run_date,
                "source": story.source,
                "title": story.title,
                "url": story.url,
                "published": story.published,
                "raw_summary": story.raw_summary,
                "score": story.score,
                "role": story.role,
                "draft": story.draft,
                "verified": int(story.verified),
                "verify_notes": story.verify_notes,
                "revisions": story.revisions,
                "status": story.status,
            },
        )
        self.con.commit()

    def get(self, story_id: str, run_date: str) -> Optional[Story]:
        row = self.con.execute(
            "SELECT * FROM stories WHERE id=? AND run_date=?", (story_id, run_date)
        ).fetchone()
        return _row_to_story(row) if row else None

    def by_date(self, run_date: str, status: Optional[str] = None, role: Optional[str] = None) -> list[Story]:
        q = "SELECT * FROM stories WHERE run_date=?"
        params: list = [run_date]
        if status:
            q += " AND status=?"
            params.append(status)
        if role:
            q += " AND role=?"
            params.append(role)
        return [_row_to_story(r) for r in self.con.execute(q, params).fetchall()]

    def close(self) -> None:
        self.con.close()


def _row_to_story(row: sqlite3.Row) -> Story:
    d = dict(row)
    d["verified"] = bool(d["verified"])
    return Story(**d)
