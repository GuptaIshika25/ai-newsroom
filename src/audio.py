"""Generate a podcast-style MP3 from the audio script using edge-tts (no API key)."""
from __future__ import annotations

import asyncio

import edge_tts


async def _synthesize(script: str, out_path: str, voice: str, rate: str) -> None:
    communicate = edge_tts.Communicate(script, voice=voice, rate=rate)
    await communicate.save(out_path)


def generate_audio(script: str, out_path: str, config: dict) -> str | None:
    audio_cfg = config.get("audio", {})
    if not audio_cfg.get("enabled", False):
        return None
    voice = audio_cfg.get("voice", "en-US-AriaNeural")
    rate = audio_cfg.get("rate", "+0%")
    asyncio.run(_synthesize(script, out_path, voice, rate))
    return out_path
