#!/usr/bin/env python3
"""Build a catalogue.json by *listening* to a folder of audio files.

Runs the grip_hear ``--json`` contract over every audio file in a directory,
groups them into editorial "movements", and writes one catalogue.json that the
site generator (build_site.py) turns into the interactive Emotional Field.

Per-track hearings are cached under <out>/cache/ so re-runs are near-free and
resumable — one track's failure never aborts the build. This is the dogfood
loop: grip-hear produces the structured hearing; the product is built from it.

Standard library only. Imports grip_hear from this same folder.

Usage:
    python3 build_catalogue.py <audio-dir> [--out catalogue]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import grip_hear

# Title (filename stem) -> movement. The editorial map. Any track not listed
# here falls into the default movement, so the build never depends on it.
MOVEMENT = {
    # I. The Confessionals
    "Aisle Seat": "The Confessionals", "Another Thought": "The Confessionals",
    "Dirt Poor Genius": "The Confessionals", "Faith In the Human Race": "The Confessionals",
    "For a While": "The Confessionals", "Happiness That's Broke": "The Confessionals",
    "I woke up this morning": "The Confessionals", "I'm Feeling Good": "The Confessionals",
    "Just Fine": "The Confessionals", "Kry Kontrole": "The Confessionals",
    "Legacy": "The Confessionals", "One Day": "The Confessionals",
    "Realize": "The Confessionals", "Reconnected": "The Confessionals",
    "Scare off the devils": "The Confessionals", "Singing Along": "The Confessionals",
    "The Place": "The Confessionals", "Too Much In My Mind": "The Confessionals",
    "Wait until I feel good": "The Confessionals",
    # II. The Band
    "Ek Is Die Een Wat Omgee": "The Band", "You see": "The Band",
    "Loneliness": "The Band", "Nemesis": "The Band",
    "Ongemaklike Situasies": "The Band", "Opportunities and what happens to them": "The Band",
    "Freetown - Marlon Brando": "The Band", "Freetown - Must be a way": "The Band",
    "Freetown - Psychological Warfare": "The Band",
    # III. Without Words
    "Broken Ring Finger": "Without Words", "That's How I Wanna Go": "Without Words",
    "The Black Sheep": "Without Words", "Sometimes": "Without Words",
    "Tigrrr's Song": "Without Words", "Moving on up": "Without Words",
    "Wave to Frank": "Without Words",
    # IV. The Dark Room
    "It's time": "The Dark Room", "Fuck Everything": "The Dark Room",
    "Trip to the Circus": "The Dark Room", "The Mood Stabilizing Depressant Circus": "The Dark Room",
    # V. Borrowed Voices
    "If (Pink Floyd Cover)": "Borrowed Voices", "You've got to hide your love away": "Borrowed Voices",
    "If You Go Away": "Borrowed Voices", "Golden Hair": "Borrowed Voices",
}
DEFAULT_MOVEMENT = "The Confessionals"
MOVEMENT_ORDER = ["The Confessionals", "The Band", "Without Words", "The Dark Room", "Borrowed Voices"]
AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".aif", ".aiff", ".flac", ".ogg", ".opus", ".aac"}


def slug(title: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", title.lower())).strip("-")


def hear_cached(path: Path, cache_dir: Path) -> dict | None:
    """Return the structured hearing for one file, using/refreshing the cache."""
    cache = cache_dir / f"{slug(path.stem)}.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text())
        except json.JSONDecodeError:
            pass  # fall through and re-hear
    try:
        h = grip_hear.hear_structured(path)
    except (RuntimeError, OSError) as e:
        print(f"  ! hear failed: {path.name}: {str(e)[:160]}", file=sys.stderr)
        return None
    cache.write_text(json.dumps(h, ensure_ascii=False, indent=2))
    return h


def record_for(path: Path, cache_dir: Path) -> dict | None:
    h = hear_cached(path, cache_dir)
    if h is None:
        return None
    title = path.stem
    return {
        "id": slug(title),
        "title": title,
        "file": str(path),
        "movement": MOVEMENT.get(title, DEFAULT_MOVEMENT),
        "genre": h.get("genre"),
        "mood": h.get("mood"),
        "language": h.get("language"),
        "instrumental": bool(h.get("instrumental", False)),
        "key_lyric": h.get("key_lyric"),
        "energy": float(h.get("energy", 0.5)),
        "darkness": float(h.get("darkness", 0.5)),
        "one_line": h.get("one_line"),
    }


def movement_rank(rec: dict) -> tuple[int, str]:
    m = rec["movement"]
    rank = MOVEMENT_ORDER.index(m) if m in MOVEMENT_ORDER else len(MOVEMENT_ORDER)
    return (rank, rec["title"].lower())


def main() -> int:
    ap = argparse.ArgumentParser(description="Build catalogue.json by listening to a folder of audio.")
    ap.add_argument("audio_dir", type=Path, help="folder containing audio files")
    ap.add_argument("--out", type=Path, default=Path("catalogue"), help="output dir (default: ./catalogue)")
    args = ap.parse_args()

    if not args.audio_dir.is_dir():
        sys.exit(f"FAIL: not a directory: {args.audio_dir}")
    cache_dir = args.out / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in args.audio_dir.iterdir()
                   if p.is_file() and p.suffix.lower() in AUDIO_EXTS)
    if not files:
        sys.exit(f"FAIL: no audio files in {args.audio_dir}")

    records = []
    for i, p in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {p.stem}")
        rec = record_for(p, cache_dir)
        if rec:
            records.append(rec)

    records.sort(key=movement_rank)
    out_file = args.out / "catalogue.json"
    out_file.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print(f"\ncatalogue.json: {len(records)} songs -> {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
