#!/usr/bin/env python3
"""grip-hear — teach your AI to *listen* to music.

Send an audio file to Google's Gemini multimodal model and get back a grounded
reading of what's actually in the recording: genre, mood, tempo feel, the main
instruments, whether there are vocals and in what language, the song structure,
and the production qualities (lo-fi, polished, live, demo).

With ``--json`` it returns a machine-readable hearing — the contract the
catalogue builder consumes — including two numbers that place the track on an
"Emotional Field": ``energy`` (0 still -> 1 intense) and ``darkness``
(0 light/warm -> 1 dark/grief/aggression).

Standard library only (plus ``urllib``). No SDK, no build step.

Setup: put your Gemini API key in the GEMINI_API_KEY environment variable.
Get a key at https://aistudio.google.com/apikey

Usage:
    python3 grip_hear.py <audio-file>
    python3 grip_hear.py <audio-file> --json
    python3 grip_hear.py <audio-file> --model gemini-2.5-flash --prompt "..."
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODEL = "gemini-2.5-flash"  # native audio input; NOT the -tts model
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_KEY_ENV = "GEMINI_API_KEY"

# Music-listening directive — elicits a grounded, track-specific perception.
DEFAULT_PROMPT = (
    "Listen to this audio recording and describe what you ACTUALLY hear in THIS "
    "specific track. Cover: genre/style, mood/feeling, tempo feel, the main "
    "instruments, whether there are vocals and in what language, the song "
    "structure, and production/recording qualities (lo-fi, polished, live, demo). "
    "Ground every claim in the audio; if you are unsure, say so. Be specific and "
    "concise — no generic filler."
)

# Structured directive (--json): a machine-readable hearing for the catalogue
# contract. energy/darkness are the two axes of the Emotional Field map.
STRUCTURED_PROMPT = (
    "Listen to this audio recording and return ONLY a JSON object (no prose, no "
    "code fence) describing what you ACTUALLY hear in THIS specific track, with "
    "these exact keys: "
    '{"genre": short style string, '
    '"mood": 2-4 mood words, '
    '"language": "English"|"Afrikaans"|"instrumental"|other, '
    '"instrumental": true|false, '
    '"vocals": true|false, '
    '"key_lyric": one short memorable lyric line (or null if instrumental), '
    '"energy": number 0.0-1.0 (0=still/sparse/quiet, 1=intense/loud/frantic), '
    '"darkness": number 0.0-1.0 (0=light/hopeful/warm, 1=dark/dread/grief/aggression), '
    '"one_line": one vivid sentence capturing this track}. '
    "Ground every value in the audio. Output the JSON object and nothing else."
)
_STRUCT_KEYS = ("genre", "mood", "language", "instrumental", "vocals",
                "key_lyric", "energy", "darkness", "one_line")

# extension -> IANA mime type Gemini accepts for audio input.
_MIME = {
    ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac",
    ".aif": "audio/aiff", ".aiff": "audio/aiff", ".wav": "audio/wav",
    ".flac": "audio/flac", ".ogg": "audio/ogg", ".opus": "audio/opus",
}
_MAX_INLINE_BYTES = 19 * 1024 * 1024  # generateContent inline cap ~20MB; stay under.


def gemini_key() -> str:
    """Read the Gemini API key from the environment."""
    key = os.environ.get(_KEY_ENV, "").strip()
    if not key:
        raise RuntimeError(
            f"{_KEY_ENV} is not set. Get a key at https://aistudio.google.com/apikey "
            f"then set it in your shell environment as {_KEY_ENV}."
        )
    return key


def mime_for(path: Path) -> str:
    mime = _MIME.get(path.suffix.lower())
    if mime is None:
        raise RuntimeError(f"Unsupported audio type {path.suffix!r}. Known: {sorted(_MIME)}")
    return mime


def load_audio(path: Path) -> tuple[str, str]:
    """Return (base64_data, mime_type). Raises if over the inline cap."""
    data = path.read_bytes()
    if len(data) > _MAX_INLINE_BYTES:
        raise RuntimeError(
            f"{path.name} is {len(data) // 1024 // 1024}MB — over the ~20MB inline cap. "
            f"Use the Gemini Files API for long tracks (future upgrade)."
        )
    return base64.b64encode(data).decode("ascii"), mime_for(path)


def extract_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates (feedback={payload.get('promptFeedback')}).")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError(f"Gemini returned no text (finishReason={candidates[0].get('finishReason')}).")
    return text


def hear(path: Path, prompt: str = DEFAULT_PROMPT, model: str = MODEL) -> str:
    """Core: send audio to the multimodal model, return its grounded description."""
    b64, mime = load_audio(path)
    body = {"contents": [{"parts": [
        {"inlineData": {"mimeType": mime, "data": b64}},
        {"text": prompt},
    ]}]}
    req = urllib.request.Request(
        ENDPOINT.format(model=model) + f"?key={gemini_key()}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Gemini HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}") from e
    return extract_text(payload)


def _clamp01(v) -> float:
    """Coerce to float in [0,1]; fail-safe to 0.5 on garbage (never crash the contract)."""
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return 0.5


def parse_structured(text: str) -> dict:
    """Parse the model's JSON hearing; tolerate code fences; clamp the axes."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if "```" in t[3:] else t.strip("`")
        t = t[4:].strip() if t.lower().startswith("json") else t.strip()
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError(f"No JSON object in model output: {text[:200]}")
    obj = json.loads(t[start:end + 1])
    obj["energy"] = _clamp01(obj.get("energy"))
    obj["darkness"] = _clamp01(obj.get("darkness"))
    obj["instrumental"] = bool(obj.get("instrumental", False))
    obj["vocals"] = bool(obj.get("vocals", not obj["instrumental"]))
    for k in _STRUCT_KEYS:
        obj.setdefault(k, None)
    return obj


def hear_structured(path: Path, model: str = MODEL) -> dict:
    """Structured hearing: audio -> validated dict (the catalogue contract)."""
    return parse_structured(hear(path, STRUCTURED_PROMPT, model))


def main() -> int:
    ap = argparse.ArgumentParser(prog="grip-hear", description="Teach your AI to listen to music.")
    ap.add_argument("audio", type=Path, help="path to an audio file")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--json", action="store_true",
                    help="emit a structured JSON hearing (the catalogue contract)")
    args = ap.parse_args()
    if not args.audio.is_file():
        print(f"No such file: {args.audio}", file=sys.stderr)
        return 2
    try:
        if args.json:
            print(json.dumps(hear_structured(args.audio, args.model), ensure_ascii=False))
        else:
            print(hear(args.audio, args.prompt, args.model))
    except RuntimeError as e:
        print(f"grip-hear error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
