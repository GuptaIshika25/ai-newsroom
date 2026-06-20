"""Resend wrapper: send the daily digest email with mp3 attachment."""

from __future__ import annotations

import base64
import os
from pathlib import Path

import resend

from src.state import Story


def _load_env() -> None:
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def _build_html(run_date: str, lead: Story, snippets: list[Story], name: str) -> str:
    snippet_items = "".join(
        f"<li><b><a href='{s.url}'>{s.title}</a></b> — {s.source}<br>"
        f"<small>{s.raw_summary[:200]}...</small></li>\n"
        for s in snippets
    )
    return f"""
<html><body style="font-family:sans-serif;max-width:680px;margin:auto;color:#111">
<h2 style="border-bottom:2px solid #000;padding-bottom:8px">{name} · {run_date}</h2>

<h3>Lead Story</h3>
<p><b><a href="{lead.url}">{lead.title}</a></b> — {lead.source}</p>
<blockquote style="border-left:4px solid #ccc;margin-left:0;padding-left:16px;color:#444">
{lead.draft[:600]}...
</blockquote>
<p><i>(Full narration in the attached mp3)</i></p>

<h3>Today's Snippets</h3>
<ol>{snippet_items}</ol>

<hr>
<p style="color:#888;font-size:12px">
  {name} is an AI-generated audio brief.
  To unsubscribe, reply "unsubscribe".
</p>
</body></html>
""".strip()


def _build_text(run_date: str, lead: Story, snippets: list[Story], name: str) -> str:
    lines = [
        f"{name} · {run_date}",
        "=" * 50,
        "",
        "LEAD STORY",
        f"{lead.title}",
        f"Source: {lead.source}",
        f"URL: {lead.url}",
        "",
        lead.draft[:800] + "...",
        "",
        "TODAY'S SNIPPETS",
        "-" * 30,
    ]
    for i, s in enumerate(snippets, 1):
        lines.append(f"{i}. {s.title}")
        lines.append(f"   {s.source} — {s.url}")
        lines.append("")
    lines.append("(Full narration in the attached mp3)")
    return "\n".join(lines)


def send(
    run_date: str,
    lead: Story,
    snippets: list[Story],
    mp3_path: Path,
    config: dict,
) -> str:
    """Send the digest + mp3 via Resend. Returns the message ID."""
    _load_env()

    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY not set — add it to .env")

    resend.api_key = api_key

    email_cfg = config.get("email", {})
    from_addr = email_cfg.get("from_address", f"{config['newsletter']['name']} <onboarding@resend.dev>")
    to_addrs = email_cfg.get("to_addresses", [])
    name = config["newsletter"]["name"]

    subject = f"{name} · {run_date} · {lead.title[:60]}"

    mp3_bytes = mp3_path.read_bytes()
    mp3_b64 = base64.b64encode(mp3_bytes).decode()
    filename = mp3_path.name

    params: resend.Emails.SendParams = {
        "from": from_addr,
        "to": to_addrs,
        "subject": subject,
        "html": _build_html(run_date, lead, snippets, name),
        "text": _build_text(run_date, lead, snippets, name),
        "attachments": [
            {
                "filename": filename,
                "content": mp3_b64,
            }
        ],
    }

    response = resend.Emails.send(params)
    return response["id"]
