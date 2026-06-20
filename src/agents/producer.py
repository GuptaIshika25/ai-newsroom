"""Producer: assemble verified drafts into a full script and synthesise one mp3."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from src.state import DB, Story
from src.tools import tts

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def _intro(run_date: str, name: str) -> str:
    # Parse YYYY-MM-DD into a spoken date like "Thursday, June 19th, 2026"
    from datetime import datetime
    dt = datetime.strptime(run_date, "%Y-%m-%d")
    day = dt.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    spoken_date = dt.strftime(f"%A, %B {day}{suffix}, %Y")
    return (
        f"Good morning. This is {name} for {spoken_date}. "
        f"Coming up: one deep-dive lead story, followed by your briefing on today's AI news. "
        f"Let's get into it."
    )


def _outro(name: str) -> str:
    return (
        f"That's your briefing from {name}. "
        f"We'll be back tomorrow with the latest from the world of AI. "
        f"Have a great day."
    )


def assemble_script(run_date: str, config: dict) -> tuple[str, Story, list[Story]]:
    """Pull verified stories from DB, assemble ordered script, return (script, lead, snippets)."""
    db = DB()
    verified = db.by_date(run_date, status="verified")
    db.close()

    if not verified:
        raise RuntimeError(f"No verified stories for {run_date}. Run critique loop first.")

    lead = next((s for s in verified if s.role == "lead"), None)
    snippets = [s for s in verified if s.role == "snippet"]

    if lead is None:
        raise RuntimeError("No verified lead story found.")

    name = config["newsletter"]["name"]
    parts = [
        _intro(run_date, name),
        "",
        lead.draft or "",
    ]

    for s in snippets:
        parts.append("")
        parts.append(s.draft or "")

    parts.append("")
    parts.append(_outro(name))

    script = "\n".join(parts)
    return script, lead, snippets


def run(run_date: str | None = None) -> Path:
    """Assemble script and synthesise mp3. Returns path to the output file."""
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    today = run_date or date.today().isoformat()
    audio_cfg = config.get("audio", {})
    voice = audio_cfg.get("voice", "en-US-AvaMultilingualNeural")
    rate = audio_cfg.get("rate", "+0%")

    print("Assembling script ...")
    script, lead, snippets = assemble_script(today, config)
    word_count = len(script.split())
    print(f"  Script: {word_count} words across 1 lead + {len(snippets)} snippets")

    OUTPUT_DIR.mkdir(exist_ok=True)
    mp3_path = OUTPUT_DIR / f"ai-newsroom-{today}.mp3"
    script_path = OUTPUT_DIR / f"ai-newsroom-{today}.txt"

    # Save the script text for inspection
    script_path.write_text(script, encoding="utf-8")
    print(f"  Script saved: {script_path}")

    print(f"Synthesising audio (voice: {voice}) ...")
    tts.synthesise(script, mp3_path, voice=voice, rate=rate)

    # Mark all stories as produced
    db = DB()
    for s in [lead] + snippets:
        s.status = "produced"
        db.upsert(s)
    db.close()

    size_kb = mp3_path.stat().st_size // 1024
    print(f"  Audio saved: {mp3_path}  ({size_kb} KB)")
    return mp3_path


if __name__ == "__main__":
    path = run()
    print(f"\nDone. Play it:\n  open \"{path}\"")
