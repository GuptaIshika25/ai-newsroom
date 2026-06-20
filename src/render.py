"""Render the digest into HTML email, plain text, and an audio script."""
from __future__ import annotations

from datetime import datetime

from fetch import Story


def _date_label() -> str:
    return datetime.now().strftime("%A, %B %-d, %Y")


def render_html(intro: str, stories: list[Story], config: dict) -> str:
    nl = config["newsletter"]
    rows = []
    for i, s in enumerate(stories, 1):
        rows.append(
            f"""
        <tr><td style="padding:18px 0;border-bottom:1px solid #ECECEC;">
          <div style="font-size:13px;color:#8A8A8A;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px;">{i:02d} &middot; {s.source}</div>
          <a href="{s.url}" style="font-size:18px;font-weight:600;color:#111;text-decoration:none;line-height:1.3;">{s.title}</a>
          <p style="font-size:15px;color:#444;line-height:1.55;margin:8px 0 0;">{s.tldr or s.summary}</p>
        </td></tr>"""
        )
    stories_html = "".join(rows)
    return f"""<!DOCTYPE html>
<html><body style="margin:0;background:#F5F5F3;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F5F5F3;padding:32px 0;">
   <tr><td align="center">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#fff;border-radius:14px;padding:36px;">
      <tr><td>
        <div style="font-size:26px;font-weight:800;color:#111;letter-spacing:-.02em;">{nl['name']}</div>
        <div style="font-size:14px;color:#8A8A8A;margin-top:2px;">{nl['tagline']} &middot; {_date_label()}</div>
        <p style="font-size:16px;color:#222;line-height:1.6;margin:22px 0 6px;font-style:italic;">{intro}</p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{stories_html}</table>
        <p style="font-size:12px;color:#A0A0A0;margin-top:28px;line-height:1.5;">
          You're reading AI TLDR &mdash; an automated daily brief built with Claude.
          {len(stories)} stories, summarized in seconds.
        </p>
      </td></tr>
    </table>
   </td></tr>
  </table>
</body></html>"""


def render_text(intro: str, stories: list[Story], config: dict) -> str:
    nl = config["newsletter"]
    lines = [f"{nl['name'].upper()} — {_date_label()}", nl["tagline"], "", intro, ""]
    for i, s in enumerate(stories, 1):
        lines += [f"{i:02d}. {s.title}  ({s.source})", f"    {s.tldr or s.summary}", f"    {s.url}", ""]
    return "\n".join(lines)


def render_audio_script(intro: str, stories: list[Story], config: dict) -> str:
    """A natural-sounding script for TTS — no URLs, no markup."""
    nl = config["newsletter"]
    parts = [
        f"Good morning. This is {nl['name']}, your AI brief for {_date_label()}.",
        intro,
        f"Here are today's {len(stories)} stories.",
    ]
    for i, s in enumerate(stories, 1):
        parts.append(f"Story {i}, from {s.source}. {s.title}. {s.tldr or s.summary}")
    parts.append("That's your brief. Have a great day.")
    return " ".join(parts)
