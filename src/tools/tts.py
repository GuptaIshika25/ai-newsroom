"""Gemini TTS wrapper: synthesise text to WAV using the Zephyr voice.

Gemini's preview TTS returns only a short partial clip when a single call's input
gets too large, which silently truncates long multi-story scripts (the tail and outro
just vanish). To stay length-proof we synthesise each segment in its own call and
concatenate the raw PCM, so total episode length never depends on one call's limit.
"""

from __future__ import annotations

import os
import time
import wave
from pathlib import Path

# Gemini TTS PCM format: 24 kHz, 16-bit, mono.
_SAMPLE_RATE = 24000
_SAMPLE_WIDTH = 2
_CHANNELS = 1

_MAX_RETRIES = 3
_RETRY_SLEEP = 4.0      # seconds; also spaces calls out to stay under rate limits
_BETWEEN_SEGMENTS = 1.0


def _load_env() -> None:
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def _client():
    _load_env()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    from google import genai
    return genai.Client(api_key=api_key)


def _synthesise_one(client, text: str, voice: str) -> bytes:
    """Synthesise one segment to raw PCM bytes, with retries."""
    from google.genai import types

    last_err: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-preview-tts",
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                        )
                    ),
                ),
            )
            pcm = response.candidates[0].content.parts[0].inline_data.data
            if pcm:
                return pcm
            last_err = RuntimeError("empty PCM returned")
        except Exception as e:  # noqa: BLE001
            last_err = e
        print(f"    ! TTS segment attempt {attempt}/{_MAX_RETRIES} failed: {last_err}")
        if attempt < _MAX_RETRIES:
            time.sleep(_RETRY_SLEEP)
    raise RuntimeError(f"TTS failed for segment after {_MAX_RETRIES} attempts: {last_err}")


def _write_wav(pcm: bytes, output_path: Path) -> None:
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_SAMPLE_WIDTH)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm)


def synthesise_segments(segments: list[str], output_path: Path, voice: str, rate: str = "+0%") -> None:
    """Synthesise each non-empty segment separately and concatenate into one WAV.

    `rate` is accepted for API compatibility; Gemini prebuilt voices don't take a rate
    parameter, so it's currently a no-op.
    """
    clean = [s.strip() for s in segments if s and s.strip()]
    if not clean:
        raise RuntimeError("No text segments to synthesise.")

    client = _client()
    pcm_parts: list[bytes] = []
    for i, seg in enumerate(clean, 1):
        print(f"  TTS segment {i}/{len(clean)} ({len(seg.split())} words) …")
        pcm_parts.append(_synthesise_one(client, seg, voice))
        if i < len(clean):
            time.sleep(_BETWEEN_SEGMENTS)

    _write_wav(b"".join(pcm_parts), output_path)


def synthesise(text: str, output_path: Path, voice: str, rate: str = "+0%") -> None:
    """Back-compatible single-string entry point: split on blank lines, then chunk."""
    segments = [b for b in text.split("\n\n") if b.strip()]
    synthesise_segments(segments, output_path, voice=voice, rate=rate)
