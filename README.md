# grip-hear — teach your AI to *listen* to music

Most AI can read your words and look at your images. **grip-hear lets it
*hear*.** Point it at an audio file and it tells you what's actually in the
recording — the genre, the mood, the instruments, whether someone's singing
and in what language, how the song is built, even whether it's a polished
master or a rough phone demo. Not from the filename. Not from metadata. From
*listening* to the sound.

It's one small Python file, the standard library, and a Google Gemini key.

**See what it built:** [The Catalogue — A Listening Study](https://codetonight-sa.github.io/grip-catalogue/)

---

## The story

It started as a simple ask: *"Find every song I've ever recorded."*

Laurie Scheepers has been writing and recording music for years — some of it
released, most of it not. The AI went looking. It found **44 released tracks**
on SoundCloud, and then it kept finding more: roughly **a hundred demos,
alt-mixes, pre-masters, and phone recordings** scattered across old hard
drives, a phone, and a couple of forgotten folders. Half-finished songs. A
band's rehearsal tapes. Four Afrikaans songs someone had sung into a phone.

Then came the real question: *what are they?* Nobody had ever catalogued them.
There were no genre tags, no notes on mood, no record of which demo became which
master. So the AI did the only honest thing — it **listened to every one of
them, overnight**, track by track, and wrote down what it heard.

The result is **The Catalogue**: 78 songs you can play, see laid out on a map of
feeling, and search not by title but by *how you want to feel right now*. The
same overactive mind, in every version of the recording, heard back by the
machine he built to hear it.

This repo is that machine, cleaned up so you can point it at your own music.

---

## How it works

```
  your audio file  ──▶  Gemini (multimodal)  ──▶  a structured "hearing"  ──▶  an interactive map you explore by feeling
   song.mp3              listens to the sound        JSON: mood, energy,          The Emotional Field
                                                     darkness, key lyric…
```

1. **Hear one track.** `grip_hear.py` sends the audio straight to Google's
   Gemini model and asks it to describe what it genuinely hears — grounded in
   the sound, not guessing. Ask for plain prose, or ask for `--json` and you get
   a tidy record with two key numbers:
   - **energy** — `0` is still and sparse, `1` is loud and frantic.
   - **darkness** — `0` is light and warm, `1` is grief, dread, or aggression.
2. **Build a catalogue.** `build_catalogue.py` listens to a whole folder, caches
   each hearing (so re-runs are basically free), and writes one
   `catalogue.json`.
3. **Build the site.** `build_site.py` turns that JSON into a single
   self-contained web page — no server, no build tools. It draws **The
   Emotional Field**: every song is a dot, placed left-to-right by energy and
   bottom-to-top by darkness. **Hover** a dot to read what the AI heard;
   **click** it to play the track. There's also a *"How are you feeling?"*
   finder — pick a mood and the songs that meet you there float to the top.

The whole thing is the loop eating its own tail: the listening tool produces the
data, and the product is built from what it heard.

---

## Quick start

You need Python 3.9+ and a free Gemini API key from
[Google AI Studio](https://aistudio.google.com/apikey).

```bash
# 1. Put your key in the environment (the tool reads GEMINI_API_KEY).
#    On macOS/Linux:
GEMINI_API_KEY="paste-your-key-here"; export GEMINI_API_KEY

# 2. Hear a single track — plain description.
python3 grip_hear.py path/to/song.mp3

# 3. Or get the structured hearing (mood, energy, darkness, a key lyric…).
python3 grip_hear.py path/to/song.mp3 --json

# 4. Listen to a whole folder and build the catalogue.
python3 build_catalogue.py path/to/your/music/ --out catalogue

# 5. Turn it into the interactive site, then open it.
python3 build_site.py --catalogue catalogue/catalogue.json --out site
open site/index.html        # macOS  (use 'xdg-open' on Linux)
```

Supported audio: `.mp3 .m4a .wav .aif .aiff .flac .ogg .opus .aac`
(tracks under ~20 MB go straight in; longer files are a roadmap item).

No extra packages required — it's standard library plus `urllib`. See
`requirements.txt`.

---

## What's in this repo

| File | What it does |
|------|--------------|
| `grip_hear.py` | The ear. One audio file → a grounded description (or `--json`). |
| `build_catalogue.py` | Listens to a folder, caches each hearing, writes `catalogue.json`. |
| `build_site.py` | Turns `catalogue.json` into the interactive Emotional Field page. |
| `index.html` | The live showcase — Laurie's 78-song catalogue, prebuilt. |
| `audio/` | The 78 recordings the showcase plays. |

---

## Roadmap

grip-hear's *impression* of tempo and key is exactly that — an impression. The
goal is to pair perception with measurement:

- **Deterministic tempo & key** via [librosa](https://librosa.org/) — real
  beat-tracking and pitch analysis alongside the AI's reading, so "feels like
  ~80 bpm" becomes a measured number.
- **Afrikaans lyric transcription** — the phone recordings are in Afrikaans and
  the lyrics are currently approximate; proper transcription would make them
  searchable and singable-along.
- **Hear a track mid-conversation** — expose grip-hear as a tool your assistant
  can call live, so you can hand it a song in the middle of a chat and ask
  "what is this?" and have it actually listen and answer.

---

## License

MIT © 2026 Laurie Scheepers. See [LICENSE](LICENSE).
