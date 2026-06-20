"""Send the digest via Resend, with the audio MP3 attached."""
from __future__ import annotations

import base64
import os


def send_email(html: str, text: str, config: dict, audio_path: str | None = None) -> dict:
    import resend

    resend.api_key = os.environ["RESEND_API_KEY"]
    email_cfg = config["email"]

    from datetime import datetime
    subject = f"{email_cfg['subject_prefix']} — {datetime.now().strftime('%b %-d')}"

    params: dict = {
        "from": email_cfg["from_address"],
        "to": email_cfg["to_addresses"],
        "subject": subject,
        "html": html,
        "text": text,
    }

    if audio_path and os.path.exists(audio_path):
        with open(audio_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        params["attachments"] = [
            {"filename": "ai-tldr-brief.mp3", "content": encoded}
        ]

    return resend.Emails.send(params)
