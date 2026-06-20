"""Mailer agent: send today's digest + mp3 via Resend."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from src.state import DB
from src.tools import mailer as mailer_tool

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def run(run_date: str | None = None) -> str:
    """Send the episode email. Returns Resend message ID."""
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    today = run_date or date.today().isoformat()

    db = DB()
    # Accept produced OR verified stories (verified = passed critique loop)
    stories = db.by_date(today, status="produced")
    if not stories:
        stories = db.by_date(today, status="verified")
    db.close()

    if not stories:
        raise RuntimeError(f"No produced/verified stories for {today}. Run Producer first.")

    lead = next((s for s in stories if s.role == "lead"), None)
    snippets = [s for s in stories if s.role == "snippet"]

    if lead is None:
        raise RuntimeError("No lead story found.")

    mp3_path = OUTPUT_DIR / f"ai-newsroom-{today}.mp3"
    if not mp3_path.exists():
        raise RuntimeError(f"mp3 not found at {mp3_path}. Run Producer first.")

    to_addrs = config.get("email", {}).get("to_addresses", [])
    print(f"Sending to: {', '.join(to_addrs)}")
    print(f"  Lead: {lead.title}")
    print(f"  Snippets: {len(snippets)}")
    print(f"  Attachment: {mp3_path.name}  ({mp3_path.stat().st_size // 1024} KB)")

    msg_id = mailer_tool.send(
        run_date=today,
        lead=lead,
        snippets=snippets,
        mp3_path=mp3_path,
        config=config,
    )
    print(f"\nSent! Resend message ID: {msg_id}")
    return msg_id


if __name__ == "__main__":
    run()
