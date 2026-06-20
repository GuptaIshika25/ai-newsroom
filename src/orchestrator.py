"""Orchestrator: runs the full pipeline Scout → Editor → Writer → Fact-checker → Producer → Mailer."""

from __future__ import annotations

import sys
import traceback
from datetime import date
from pathlib import Path

import yaml


def _banner(msg: str) -> None:
    bar = "─" * 56
    print(f"\n{bar}")
    print(f"  {msg}")
    print(bar)


def run(run_date: str | None = None, dry_run: bool = False) -> None:
    today = run_date or date.today().isoformat()

    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    print(f"\n{'='*60}")
    mode = "DRY-RUN" if dry_run else "LIVE"
    print(f"  AI Newsroom · {today} · {mode}")
    print(f"{'='*60}")

    # ── 1. Scout ─────────────────────────────────────────────
    _banner("1 / 6  Scout — fetching & filtering RSS feeds")
    if dry_run:
        print("  [dry-run] skipping Scout LLM call")
        candidates = _any_stories_for_date(today)
    else:
        from src.agents import scout
        try:
            candidates = scout.run(run_date=today)
        except Exception as e:
            _abort("Scout", e)
            return
    print(f"  {len(candidates)} stories in DB for {today}")

    if not candidates:
        print("  Nothing to do today — no stories in DB. Exiting.")
        return

    # ── 2. Editor ────────────────────────────────────────────
    _banner("2 / 6  Editor — ranking candidates, picking lead")
    if dry_run:
        print("  [dry-run] skipping Editor LLM call")
        lead, snippets = _check_ranked(today)
    else:
        from src.agents import editor
        try:
            lead, snippets = editor.run(run_date=today)
        except Exception as e:
            _abort("Editor", e)
            return
    print(f"  Lead: [{lead.source}] {lead.title[:60]}")
    print(f"  Snippets: {len(snippets)}")

    # ── 3. Writer ────────────────────────────────────────────
    _banner("3 / 6  Writer — drafting lead + snippets")
    if dry_run:
        print("  [dry-run] skipping Writer LLM calls")
        from src.state import DB
        db = DB(); drafted = db.by_date(today, status="drafted"); db.close()
        if not drafted:
            print("  [dry-run] no existing drafts found — run live first")
    else:
        from src.agents import writer
        try:
            writer.run(run_date=today)
        except Exception as e:
            _abort("Writer", e)
            return
    print("  Drafts complete")

    # ── 4. Fact-checker / critique loop ──────────────────────
    _banner("4 / 6  Fact-checker — critique loop (max 2 revisions)")
    if dry_run:
        print("  [dry-run] skipping Fact-checker LLM calls")
        from src.state import DB
        db = DB(); verified = db.by_date(today, status="verified"); db.close()
        print(f"  [dry-run] {len(verified)} verified stories found in DB")
    else:
        from src.agents import critique_loop
        try:
            results = critique_loop.run(run_date=today)
        except Exception as e:
            _abort("Fact-checker", e)
            return
        approved = [r for r in results if r.outcome == "approved"]
        dropped  = [r for r in results if r.outcome == "dropped"]
        revised  = [r for r in results if r.revisions_made > 0 and r.outcome == "approved"]
        print(f"  Approved: {len(approved)}  |  Dropped: {len(dropped)}  |  Revised: {len(revised)}")
        if not approved:
            print("  All stories failed fact-check — aborting run.")
            return

    # ── 5. Producer ──────────────────────────────────────────
    _banner("5 / 6  Producer — assembling script + synthesising mp3")
    mp3_path = Path("output") / f"ai-newsroom-{today}.mp3"
    if dry_run and mp3_path.exists():
        print(f"  [dry-run] reusing existing mp3: {mp3_path}")
    else:
        from src.agents import producer
        try:
            mp3_path = producer.run(run_date=today)
        except Exception as e:
            _abort("Producer", e)
            return
    print(f"  Output: {mp3_path}  ({mp3_path.stat().st_size // 1024} KB)")

    # ── 6. Mailer ────────────────────────────────────────────
    _banner("6 / 6  Mailer — sending digest + mp3")
    if dry_run:
        to = config.get("email", {}).get("to_addresses", [])
        print(f"  [dry-run] would send to: {', '.join(to)}")
        print(f"  [dry-run] attachment: {mp3_path.name}")
    else:
        from src.agents import mailer
        try:
            msg_id = mailer.run(run_date=today)
        except Exception as e:
            _abort("Mailer", e)
            return
        print(f"  Message ID: {msg_id}")

    # ── Done ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Done! AI Newsroom · {today} · {mode} complete.")
    print(f"{'='*60}\n")


# ── helpers ──────────────────────────────────────────────────

def _abort(stage: str, exc: Exception) -> None:
    print(f"\n  ERROR in {stage}: {exc}")
    traceback.print_exc()
    print(f"  Run aborted.")
    sys.exit(1)


def _any_stories_for_date(run_date: str):
    from src.state import DB
    db = DB()
    stories = db.by_date(run_date)
    db.close()
    if not stories:
        print(f"  [dry-run] no stories in DB for {run_date} — run live first")
    return stories


def _check_ranked(run_date: str):
    from src.state import DB
    db = DB()
    # Accept any status — stories advance past 'ranked' through the pipeline
    all_stories = db.by_date(run_date)
    db.close()
    lead = next((s for s in all_stories if s.role == "lead"), None)
    snippets = [s for s in all_stories if s.role == "snippet"]
    if lead is None:
        raise RuntimeError("No lead story in DB — run Editor first")
    return lead, snippets
