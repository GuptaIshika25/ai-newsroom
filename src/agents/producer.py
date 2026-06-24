"""Producer: assemble verified drafts into a full script and synthesise one mp3."""

from __future__ import annotations

import subprocess
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


def assemble_script(run_date: str, config: dict) -> tuple[str, list[str], Story, list[Story]]:
    """Pull verified stories, assemble the ordered script + per-segment list.

    Returns (script_text, segments, lead, snippets). `segments` is the list fed to the
    chunked TTS (intro, lead, each snippet, outro); `script_text` is the same joined for
    saving/inspection.
    """
    db = DB()
    verified = db.by_date(run_date, status="verified")
    db.close()

    if not verified:
        raise RuntimeError(f"No verified stories for {run_date}. Run critique loop first.")

    lead = next((s for s in verified if s.role == "lead"), None)
    snippets = [s for s in verified if s.role == "snippet"]

    if lead is None:
        # The intended lead (and any promoted replacement) was dropped — e.g. its source
        # was unfetchable. Rather than abort the whole run, promote the highest-scored
        # surviving snippet so the listener still gets an episode.
        if snippets:
            snippets = sorted(snippets, key=lambda s: s.score, reverse=True)
            lead = snippets.pop(0)
            print(f"  No verified lead — promoting top snippet to lead: [{lead.source}] {lead.title[:55]}")
        else:
            raise RuntimeError(f"No verified stories with content for {run_date} — nothing to produce.")

    # Cap the spoken brief to the top N stories (1 lead + the rest as snippets).
    audio_stories = config.get("format", {}).get("audio_stories", 5)
    snippets = snippets[: max(0, audio_stories - 1)]

    name = config["newsletter"]["name"]
    segments = [_intro(run_date, name), lead.draft or ""]
    segments += [s.draft or "" for s in snippets]
    segments.append(_outro(name))
    segments = [seg for seg in segments if seg.strip()]

    script = "\n\n".join(segments)
    return script, segments, lead, snippets


def run(run_date: str | None = None) -> Path:
    """Assemble script and synthesise mp3. Returns path to the output file."""
    with open("config.yaml") as f:
        config = yaml.safe_load(f)

    today = run_date or date.today().isoformat()
    audio_cfg = config.get("audio", {})
    voice = audio_cfg.get("voice", "en-US-AvaMultilingualNeural")
    rate = audio_cfg.get("rate", "+0%")

    print("Assembling script ...")
    script, segments, lead, snippets = assemble_script(today, config)
    word_count = len(script.split())
    print(f"  Script: {word_count} words across 1 lead + {len(snippets)} snippets ({len(segments)} segments)")

    OUTPUT_DIR.mkdir(exist_ok=True)
    wav_path = OUTPUT_DIR / f"ai-newsroom-{today}.wav"
    mp3_path = OUTPUT_DIR / f"ai-newsroom-{today}.mp3"
    script_path = OUTPUT_DIR / f"ai-newsroom-{today}.txt"

    # Save the script text for inspection
    script_path.write_text(script, encoding="utf-8")
    print(f"  Script saved: {script_path}")

    print(f"Synthesising audio (voice: {voice}) — {len(segments)} segments ...")
    tts.synthesise_segments(segments, wav_path, voice=voice, rate=rate)

    print("  Converting WAV → MP3 ...")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-q:a", "4", str(mp3_path)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wav_path.unlink()

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
