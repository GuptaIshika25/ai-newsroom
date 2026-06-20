"""edge-tts wrapper: synthesise text to mp3 using the Ava voice."""

from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts


async def _synthesise(text: str, output_path: Path, voice: str, rate: str) -> None:
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(str(output_path))


def synthesise(text: str, output_path: Path, voice: str, rate: str = "+0%") -> None:
    """Convert text to mp3 at output_path using edge-tts."""
    asyncio.run(_synthesise(text, output_path, voice, rate))
