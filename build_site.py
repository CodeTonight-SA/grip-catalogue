#!/usr/bin/env python3
"""Generate the interactive "Catalogue" site from a catalogue.json.

Emits a single self-contained index.html (embedded data + vanilla JS, no build
step, no backend) and copies each track's audio into <out>/audio/ so every song
plays. Open the result in any browser (file://) or serve it over http.

Sections: Overture - The Emotional Field (energy x darkness map) -
How are you feeling? (mood finder) - The Catalogue (movements, playable).

Standard library only.

Usage:
    python3 build_site.py [--catalogue catalogue/catalogue.json] [--out site]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

MOVEMENT_COLOUR = {
    "The Confessionals": "#8a2846",
    "The Band": "#c2410c",
    "Without Words": "#0f766e",
    "The Dark Room": "#5b21b6",
    "Borrowed Voices": "#a16207",
    "The Workshop": "#1d4ed8",
    "Borrowed Voices (Afrikaans)": "#92400e",
}
MOVEMENT_ORDER = [
    "The Confessionals", "The Band", "Without Words", "The Dark Room",
    "Borrowed Voices", "The Workshop", "Borrowed Voices (Afrikaans)",
]
MOVEMENT_BLURB = {
    "The Confessionals": "Voice and acoustic guitar — the crowded mind, and the connection it reaches for.",
    "The Band": "Drums, bass, distorted guitar — the louder declarations, and the doubts behind them.",
    "Without Words": "The instrumentals — where the guitar stops accompanying the voice and becomes it.",
    "The Dark Room": "Drone, industrial noise, dread — the far pole from the folk.",
    "Borrowed Voices": "The covers — and a map of where this songwriting comes from.",
    "The Workshop": "Demos, alt-mixes, and pre-masters — the songs before they were songs.",
    "Borrowed Voices (Afrikaans)": "Phone recordings — Afrikaans songs, caught raw.",
}

# Mood finder: each feeling -> a target point in the (energy, darkness) field.
FEELINGS = [
    {"key": "overwhelmed", "label": "Overwhelmed / too much in my mind", "e": 0.32, "d": 0.58},
    {"key": "tender", "label": "Tender / in love", "e": 0.26, "d": 0.24},
    {"key": "catharsis", "label": "I need to let it out", "e": 0.86, "d": 0.82},
    {"key": "calm", "label": "I want to drift / be calm", "e": 0.20, "d": 0.40, "instrumental_bonus": True},
    {"key": "heartbroken", "label": "Heartbroken", "e": 0.34, "d": 0.76},
    {"key": "defiant", "label": "Defiant / fired up", "e": 0.80, "d": 0.50},
]


def copy_audio(records: list, out_dir: Path) -> None:
    """Stage each song's audio under <out>/audio/<id><ext> and set rec['audio'].

    Three cases, in order:
      1. rec['file'] points at a readable source -> copy it in (the build-from-
         source path);
      2. no 'file' (or unreadable) but rec already carries a relative 'audio'
         path that exists in this repo -> keep it (rebuild-from-catalogue path,
         audio already committed);
      3. neither -> rec['audio']=None; the card still renders without playback.
    A machine-local 'file' path is never inlined into the page (popped below).
    """
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    for r in records:
        src = Path(r["file"]) if r.get("file") else None
        if src and src.is_file():
            dst = audio_dir / f"{r['id']}{src.suffix.lower()}"
            try:
                shutil.copyfile(src, dst)
                r["audio"] = f"audio/{r['id']}{src.suffix.lower()}"
            except OSError:
                r["audio"] = None
        elif r.get("audio"):
            pass  # already-committed repo audio (audio/<id>.<ext>) — keep as-is
        else:
            r["audio"] = None  # no playable source; card still renders
        r.pop("file", None)  # never leak a build-machine path into the page


def _upcoming_html(upcoming: list) -> str:
    """Render the static Upcoming Songs section."""
    import html as _html
    cards = []
    for item in upcoming:
        title = _html.escape(item.get("title", ""))
        lang = _html.escape(item.get("lang", ""))
        teaser = _html.escape(item.get("teaser", ""))
        lyric_raw = item.get("lyric", "") or ""
        lyric_html = _html.escape(lyric_raw).replace("\n", "<br>")
        cards.append(
            f'<div class="upcoming-card">'
            f'<h4>{title}</h4>'
            f'<span class="lang-chip">{lang}</span>'
            f'<div class="teaser">{teaser}</div>'
            f'<details><summary>Lyrics</summary>'
            f'<div class="lyric-body">{lyric_html}</div></details>'
            f'</div>'
        )
    cards_html = "\n".join(cards)
    return (
        '\n<section class="upcoming"><div class="wrap">\n'
        '  <h2>Upcoming Songs</h2>\n'
        '  <p class="intro">Written, not yet recorded — lyrics on the page, songs on the way.</p>\n'
        f'  <div class="upcoming-grid">\n{cards_html}\n  </div>\n'
        '</div></section>\n'
    )


def html(records: list, upcoming: list | None = None) -> str:
    upcoming_section = _upcoming_html(upcoming or [])
    data = json.dumps(records, ensure_ascii=False)
    feelings = json.dumps(FEELINGS, ensure_ascii=False)
    colours = json.dumps(MOVEMENT_COLOUR, ensure_ascii=False)
    order = json.dumps(MOVEMENT_ORDER, ensure_ascii=False)
    blurbs = json.dumps(MOVEMENT_BLURB, ensure_ascii=False)
    n = len(records)
    n_instr = sum(1 for r in records if r.get("instrumental"))
    n_afr = sum(1 for r in records if (r.get("language") or "").lower().startswith("afrik"))
    n_movements = len({r["movement"] for r in records})
    n_e = sum(1 for r in records if (r.get("key") or "").strip().split(" ")[0].upper() == "E")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Catalogue — A Listening Study</title>
<style>
  :root {{
    --ink:#23232a; --cream:#faf8f4; --charcoal:#1a1a1e; --garnet:#8a2846;
    --garnet-soft:#b0667d; --rule:#e4ded4; --muted:#6b6760;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--cream); color:var(--ink);
    font-family:-apple-system,'Helvetica Neue',Arial,sans-serif; line-height:1.55; }}
  h1,h2,h3 {{ font-family:Georgia,'Times New Roman',serif; font-weight:700; }}
  a {{ color:var(--garnet); }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:0 22px; }}

  /* Overture */
  .overture {{ background:var(--charcoal); color:var(--cream); padding:64px 0 56px; position:relative; overflow:hidden; }}
  .overture::after {{ content:""; position:absolute; top:-160px; right:-160px; width:420px; height:420px;
    border-radius:50%; background:repeating-radial-gradient(circle at center, transparent 0 10px, rgba(176,102,125,.14) 10px 11px); }}
  .overture .kicker {{ font-family:Georgia,serif; letter-spacing:5px; text-transform:uppercase;
    color:var(--garnet-soft); font-size:13px; margin:0; }}
  .overture h1 {{ font-size:60px; line-height:1.02; margin:10px 0 0; letter-spacing:-.5px; }}
  .overture .thesis {{ font-family:Georgia,serif; font-style:italic; font-size:20px; color:#d8d2c8;
    max-width:760px; margin:22px 0 0; }}
  .numbers {{ display:flex; gap:34px; margin:30px 0 0; flex-wrap:wrap; }}
  .numbers .n .big {{ font-family:Georgia,serif; font-size:34px; color:var(--garnet-soft); display:block; line-height:1; }}
  .numbers .n .lab {{ font-size:11px; letter-spacing:1.5px; text-transform:uppercase; color:#9a948a; }}
  /* "In the key of E" — one-tap filter control (the stat IS the toggle) */
  .numbers .n.n-tap {{ cursor:pointer; border-radius:8px; padding:6px 10px; margin:-6px -10px;
    transition:background .15s, box-shadow .15s; outline:none; -webkit-tap-highlight-color:transparent; }}
  .numbers .n.n-tap .lab {{ color:var(--garnet-soft); }}
  .numbers .n.n-tap:hover {{ background:rgba(176,102,125,.18); }}
  .numbers .n.n-tap:focus-visible {{ box-shadow:0 0 0 2px var(--garnet-soft); }}
  .numbers .n.n-tap[aria-pressed="true"] {{ background:var(--garnet); }}
  .numbers .n.n-tap[aria-pressed="true"] .big,
  .numbers .n.n-tap[aria-pressed="true"] .lab {{ color:#fff; }}

  section.block {{ padding:48px 0 8px; }}
  section.block > .wrap > h2 {{ font-size:30px; color:var(--charcoal); margin:0 0 4px;
    border-bottom:2px solid var(--garnet); display:inline-block; padding-bottom:6px; }}
  .sublede {{ color:var(--muted); font-family:Georgia,serif; font-style:italic; margin:8px 0 22px; }}

  /* Field map */
  #fieldWrap {{ position:relative; background:#fff; border:1px solid var(--rule); border-radius:10px; padding:10px; }}
  svg {{ width:100%; height:auto; display:block; }}
  .axis-label {{ font-size:11px; letter-spacing:1.5px; text-transform:uppercase; fill:var(--muted); font-family:-apple-system,sans-serif; }}
  .dot {{ cursor:pointer; transition:r .12s; }}
  .dot:hover {{ stroke:#1a1a1e; stroke-width:1.5; }}
  .legend {{ display:flex; gap:18px; flex-wrap:wrap; margin:14px 2px 0; font-size:12.5px; color:var(--muted); }}
  .legend .sw {{ display:inline-block; width:11px; height:11px; border-radius:50%; margin-right:6px; vertical-align:middle; }}
  #tip {{ position:absolute; pointer-events:none; background:var(--charcoal); color:var(--cream);
    padding:9px 12px; border-radius:8px; font-size:12.5px; max-width:280px; opacity:0; transition:opacity .12s; z-index:5; }}
  #tip .t {{ font-weight:700; font-family:Georgia,serif; }}
  #tip .l {{ color:var(--garnet-soft); font-style:italic; margin-top:3px; }}

  /* Finder */
  .feelings {{ display:flex; flex-wrap:wrap; gap:10px; margin:0 0 18px; }}
  .feelings button {{ font:inherit; font-size:14px; padding:9px 15px; border:1px solid var(--garnet);
    background:#fff; color:var(--garnet); border-radius:22px; cursor:pointer; }}
  .feelings button:hover, .feelings button[aria-pressed="true"] {{ background:var(--garnet); color:#fff; }}
  #finderOut {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; }}

  /* Cards */
  .movement-head {{ margin:34px 0 4px; }}
  .movement-head .mnum {{ font-family:Georgia,serif; letter-spacing:3px; text-transform:uppercase; font-size:12px; }}
  .movement-head h3 {{ font-size:23px; margin:2px 0 2px; color:var(--charcoal); }}
  .movement-head .mb {{ color:var(--muted); font-family:Georgia,serif; font-style:italic; margin:0 0 14px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; }}
  .card {{ border:1px solid var(--rule); border-left:4px solid var(--garnet); border-radius:9px;
    background:#fff; padding:15px 16px; }}
  .card h4 {{ margin:0 0 3px; font-family:Georgia,serif; font-size:17px; color:var(--charcoal); }}
  .card .tags {{ font-size:10.5px; letter-spacing:1px; text-transform:uppercase; color:var(--garnet); font-weight:700; margin:0 0 8px; }}
  .card .one {{ font-size:13.5px; margin:0 0 8px; }}
  .card .lyric {{ font-family:Georgia,serif; font-style:italic; color:var(--garnet); font-size:13px;
    border-left:2px solid var(--garnet-soft); padding-left:9px; margin:0 0 10px; }}
  /* Mechanical floor (librosa): tempo + musical key, measured not guessed. */
  .card .floor {{ display:flex; flex-wrap:wrap; gap:6px; margin:0 0 9px; }}
  .card .floor .chip {{ font-size:10.5px; letter-spacing:.4px; color:var(--charcoal);
    background:#f3eee6; border:1px solid var(--rule); border-radius:20px; padding:2px 9px; }}
  .card .floor .chip b {{ color:var(--garnet); font-weight:700; }}
  .card details.lyrics {{ margin:0 0 10px; }}
  .card details.lyrics summary {{ cursor:pointer; font-size:11px; letter-spacing:.5px; text-transform:uppercase; color:var(--garnet); font-weight:700; }}
  .card details.lyrics .body {{ white-space:pre-wrap; font-size:12.5px; color:var(--ink); line-height:1.5; margin:7px 0 0; max-height:240px; overflow:auto; }}
  .card details.lyrics .prov {{ font-size:10px; color:var(--muted); font-style:italic; margin-top:5px; }}
  .card audio {{ width:100%; height:34px; }}
  /* Upcoming Songs */
  .upcoming {{ padding:48px 0 24px; }}
  .upcoming h2 {{ font-size:30px; color:var(--charcoal); margin:0 0 4px; border-bottom:2px solid var(--garnet); display:inline-block; padding-bottom:6px; font-family:Georgia,'Times New Roman',serif; font-weight:700; }}
  .upcoming .intro {{ color:var(--muted); font-family:Georgia,serif; font-style:italic; margin:8px 0 22px; }}
  .upcoming-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; }}
  .upcoming-card {{ border:1px solid var(--rule); border-left:4px solid var(--garnet-soft); border-radius:9px; background:#fff; padding:15px 16px; }}
  .upcoming-card h4 {{ margin:0 0 3px; font-family:Georgia,serif; font-size:17px; color:var(--charcoal); }}
  .upcoming-card .lang-chip {{ display:inline-block; font-size:10px; letter-spacing:.8px; text-transform:uppercase; background:#f3eee6; border:1px solid var(--rule); border-radius:20px; padding:2px 9px; color:var(--garnet); font-weight:700; margin:0 0 8px; }}
  .upcoming-card .teaser {{ font-size:13px; color:var(--muted); margin:0 0 10px; }}
  .upcoming-card details {{ margin:0; }}
  .upcoming-card details summary {{ cursor:pointer; font-size:11px; letter-spacing:.5px; text-transform:uppercase; color:var(--garnet-soft); font-weight:700; }}
  .upcoming-card details .lyric-body {{ white-space:pre-wrap; font-size:12.5px; color:var(--ink); line-height:1.6; margin:7px 0 0; max-height:280px; overflow:auto; }}
  footer {{ color:var(--muted); font-size:12.5px; padding:40px 0 60px; text-align:center; }}
  footer .caveat {{ font-style:italic; max-width:680px; margin:8px auto 0; }}
  /* ---------- Listening Instrument: hero actions, live field sync, sticky player ---------- */
  .hero-actions {{ display:flex; gap:10px; margin:18px 0 0; flex-wrap:wrap; }}
  .hero-actions button {{ font:inherit; font-size:13px; letter-spacing:.3px; padding:9px 16px;
    border:1px solid var(--garnet-soft); background:transparent; color:var(--cream);
    border-radius:22px; cursor:pointer; transition:background .15s, color .15s; }}
  .hero-actions button:hover {{ background:var(--garnet-soft); color:#1a1a1e; }}
  .card {{ transition:box-shadow .3s, border-color .3s; scroll-margin:90px 0; }}
  .card.playing {{ box-shadow:0 0 0 3px var(--garnet-soft); border-left-color:var(--garnet); }}
  .dot.playing {{ stroke:#1a1a1e; stroke-width:2; animation:dotpulse 1.1s ease-in-out infinite; }}
  @keyframes dotpulse {{ 0%,100% {{ r:6.5px; opacity:.82; }} 50% {{ r:11px; opacity:1; }} }}
  #player {{ position:fixed; left:0; right:0; bottom:0; z-index:40; background:var(--charcoal);
    color:var(--cream); border-top:2px solid var(--garnet); box-shadow:0 -4px 24px rgba(0,0,0,.28); }}
  #player[hidden] {{ display:none; }}
  #player .pl-wrap {{ max-width:1080px; margin:0 auto; display:flex; align-items:center; gap:14px; padding:10px 18px; }}
  #player .pl-dot {{ width:12px; height:12px; border-radius:50%; background:var(--garnet); flex:0 0 auto; }}
  #player .pl-meta {{ min-width:0; flex:0 1 220px; }}
  #player .pl-title {{ font-family:Georgia,serif; font-size:15px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  #player .pl-sub {{ font-size:11px; letter-spacing:.5px; color:#cdbac1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
  #player .pl-ctrls {{ display:flex; gap:4px; flex:0 0 auto; }}
  #player .pl-ctrls button {{ font-size:15px; width:38px; height:38px; border-radius:50%; border:1px solid #4a3138;
    background:transparent; color:var(--cream); cursor:pointer; line-height:1; }}
  #player .pl-ctrls button:hover {{ background:var(--garnet); border-color:var(--garnet); }}
  #player .pl-seek {{ display:flex; align-items:center; gap:8px; flex:1 1 auto; font-size:11px; color:#cdbac1; min-width:120px; }}
  #player .pl-seek input[type=range] {{ flex:1 1 auto; accent-color:var(--garnet-soft); cursor:pointer; }}
  #player #plClose {{ background:transparent; border:none; color:#cdbac1; font-size:20px; cursor:pointer; flex:0 0 auto; }}
  #player #plClose:hover {{ color:var(--cream); }}
  @media (max-width:640px) {{ #player .pl-seek {{ display:none; }} #player .pl-wrap {{ gap:10px; padding:8px 12px; }} }}
  @media (prefers-reduced-motion: reduce) {{ .dot.playing {{ animation:none; }} html {{ scroll-behavior:auto; }} }}
</style></head>
<body>
<header class="overture"><div class="wrap">
  <p class="kicker">grip-hear · A Listening Instrument</p>
  <h1>The Catalogue</h1>
  <p class="thesis">Songs by Laurie Scheepers — published tracks, demos, alt-mixes, pre-masters, and phone recordings — heard by the machine he built, and turned into something you can play, map, and search by how you feel.</p>
  <p style="margin:14px 0 0;font-family:Georgia,serif;"><a href="musical-thread.html" style="color:#b0667d;font-size:15px;letter-spacing:.5px;border-bottom:1px solid #8a2846;padding-bottom:2px;text-decoration:none;">Read: The Musical Thread — how this music is written, across the genres &rarr;</a></p>
  <div class="hero-actions">
    <button id="playAll" type="button" title="Play the catalogue from the top, one song into the next">&#9654;&nbsp; Play all</button>
    <button id="surprise" type="button" title="Play a song at random">&#127922;&nbsp; Surprise me</button>
  </div>
  <div class="numbers">
    <div class="n"><span class="big">{n}</span><span class="lab">Songs</span></div>
    <div class="n"><span class="big">{n_movements}</span><span class="lab">Movements</span></div>
    <div class="n"><span class="big">{n_instr}</span><span class="lab">Instrumental</span></div>
    <div class="n"><span class="big">{n_afr}</span><span class="lab">In Afrikaans</span></div>
    <div class="n n-tap" id="eFilter" role="button" tabindex="0" aria-pressed="false" title="Tap to show only the songs in the key of E"><span class="big">{n_e}</span><span class="lab">In the key of E &#9656;</span></div>
  </div>
</div></header>

<section class="block"><div class="wrap">
  <h2>The Emotional Field</h2>
  <p class="sublede">Every song placed by what the AI heard in it — left&rarr;right is stillness&rarr;intensity, bottom&rarr;top is light&rarr;dark. Hover to read; click to play.</p>
  <div id="fieldWrap"><div id="tip"></div></div>
  <div class="legend" id="legend"></div>
</div></section>

<section class="block"><div class="wrap">
  <h2>How are you feeling?</h2>
  <p class="sublede">Pick a feeling — the songs from this catalogue that meet you there rise to the top.</p>
  <div class="feelings" id="feelings"></div>
  <div id="finderOut"></div>
</div></section>

<section class="block"><div class="wrap">
  <h2>The Catalogue</h2>
  <p class="sublede" id="catNote">All {n} songs, in movements. Each as the AI heard it.</p>
  <div id="catalogue"></div>
</div></section>
{upcoming_section}
<footer><div class="wrap">
  Heard in full via <strong>grip-hear</strong> · audio &rarr; Gemini multimodal &rarr; structured hearing
  <div class="caveat">Each placement and impression is grounded in what the model actually heard. Tempo and musical key are measured deterministically with librosa, not guessed. Where shown, lyrics are transcribed via Vulavula speech-to-text; the model's guessed line is the pull-quote. Playback uses the audio files in this repository.</div>
</div></footer>

<script>
const CATALOGUE = {data};
const FEELINGS = {feelings};
const COLOUR = {colours};
const ORDER = {order};
const BLURB = {blurbs};
const ROMAN = ["I","II","III","IV","V","VI","VII","VIII","IX","X"];

/* ---------- Emotional Field (SVG scatter) ---------- */
function renderField() {{
  const W=920, H=560, pad=54;
  const x = e => pad + e*(W-2*pad);
  const y = d => (H-pad) - d*(H-2*pad);   // darkness up
  let s = `<svg viewBox="0 0 ${{W}} ${{H}}" role="img" aria-label="Emotional field map">`;
  s += `<rect x="${{pad}}" y="${{pad}}" width="${{W-2*pad}}" height="${{H-2*pad}}" fill="#fcfbf9" stroke="#eee7db"/>`;
  for(let g=0.25; g<1; g+=0.25){{
    s += `<line x1="${{x(g)}}" y1="${{pad}}" x2="${{x(g)}}" y2="${{H-pad}}" stroke="#f0eadf"/>`;
    s += `<line x1="${{pad}}" y1="${{y(g)}}" x2="${{W-pad}}" y2="${{y(g)}}" stroke="#f0eadf"/>`;
  }}
  s += `<text class="axis-label" x="${{W/2}}" y="${{H-18}}" text-anchor="middle">still &rarr; intense  (energy)</text>`;
  s += `<text class="axis-label" transform="translate(20,${{H/2}}) rotate(-90)" text-anchor="middle">light &rarr; dark  (darkness)</text>`;
  CATALOGUE.forEach((r,i) => {{
    const c = COLOUR[r.movement] || "#8a2846";
    s += `<circle class="dot" data-i="${{i}}" cx="${{x(r.energy)}}" cy="${{y(r.darkness)}}" r="6.5" fill="${{c}}" fill-opacity="0.82"/>`;
  }});
  s += `</svg>`;
  const wrap = document.getElementById("fieldWrap");
  wrap.insertAdjacentHTML("beforeend", s);
  const tip = document.getElementById("tip");
  wrap.querySelectorAll(".dot").forEach(dot => {{
    const r = CATALOGUE[+dot.dataset.i];
    dot.addEventListener("mousemove", ev => {{
      const floor = [r.tempo_bpm? Math.round(r.tempo_bpm)+" BPM":"", fmtKey(r)].filter(Boolean).join(" · ");
      tip.innerHTML = `<div class="t">${{esc(r.title)}}</div>` +
        (floor ? `<div style="color:#cdbac1;font-size:11px;margin:2px 0">${{floor}}</div>` : "") +
        `<div>${{esc(r.one_line||"")}}</div>` +
        (r.key_lyric ? `<div class="l">&ldquo;${{esc(r.key_lyric)}}&rdquo;</div>` : "");
      const b = wrap.getBoundingClientRect();
      tip.style.left = Math.min(ev.clientX-b.left+14, b.width-290)+"px";
      tip.style.top = (ev.clientY-b.top+14)+"px"; tip.style.opacity=1;
    }});
    dot.addEventListener("mouseleave", () => tip.style.opacity=0);
    dot.addEventListener("click", () => playSong(r.id));
  }});
  document.getElementById("legend").innerHTML = ORDER.filter(m => CATALOGUE.some(r => r.movement===m)).map(m =>
    `<span><span class="sw" style="background:${{COLOUR[m]}}"></span>${{esc(m)}}</span>`).join("");
}}

/* ---------- Mood finder ---------- */
function renderFeelings() {{
  const box = document.getElementById("feelings");
  box.innerHTML = FEELINGS.map(f => `<button data-k="${{f.key}}">${{esc(f.label)}}</button>`).join("");
  box.querySelectorAll("button").forEach(btn => btn.addEventListener("click", () => {{
    box.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", b===btn ? "true":"false"));
    const f = FEELINGS.find(x => x.key === btn.dataset.k);
    const ranked = CATALOGUE.map(r => {{
      let dist = Math.hypot(r.energy - f.e, r.darkness - f.d);
      if (f.instrumental_bonus && r.instrumental) dist -= 0.12;
      return {{r, dist}};
    }}).sort((a,b) => a.dist - b.dist).slice(0,5).map(x => x.r);
    document.getElementById("finderOut").innerHTML = ranked.map(cardHTML).join("");
  }}));
}}

/* ---------- Catalogue cards ---------- */
function fmtKey(r) {{ return r.key ? esc(r.key) + (r.mode ? " " + esc(r.mode) : "") : ""; }}
function floorHTML(r) {{
  // librosa-measured tempo/key — only rendered when the mechanical floor ran.
  const chips = [];
  if (r.tempo_bpm) chips.push(`<span class="chip"><b>${{Math.round(r.tempo_bpm)}}</b> BPM</span>`);
  if (r.key) chips.push(`<span class="chip">key <b>${{fmtKey(r)}}</b></span>`);
  return chips.length ? `<div class="floor" title="Measured by librosa, not guessed">${{chips.join("")}}</div>` : "";
}}
function lyricsHTML(r) {{
  if (!r.lyrics) return "";
  const prov = r.lyrics_source === "notes" ? "Lyrics by Laurie Scheepers"
             : "Transcribed via Whisper — may contain errors";
  return `<details class="lyrics"><summary>Lyrics</summary>`+
    `<div class="body">${{esc(r.lyrics)}}</div>`+
    `<div class="prov">${{prov}}</div></details>`;
}}
function cardHTML(r) {{
  const tags = [r.genre, Array.isArray(r.mood)? r.mood.join(", "): r.mood, r.instrumental? "instrumental": (r.language||"")]
    .filter(Boolean).join(" · ");
  const audio = r.audio ? `<audio controls preload="none" src="${{encodeURI(r.audio)}}"></audio>`
                        : `<div style="font-size:12px;color:var(--muted)">(audio not linked)</div>`;
  return `<div class="card" id="song-${{r.id}}">
    <h4>${{esc(r.title)}}</h4>
    <div class="tags">${{esc(tags)}}</div>
    ${{floorHTML(r)}}
    <div class="one">${{esc(r.one_line||"")}}</div>
    ${{r.key_lyric ? `<div class="lyric">&ldquo;${{esc(r.key_lyric)}}&rdquo;</div>`:""}}
    ${{lyricsHTML(r)}}
    ${{audio}}
  </div>`;
}}
function renderCatalogue() {{
  const root = document.getElementById("catalogue");
  const pool = E_ONLY ? CATALOGUE.filter(isE) : CATALOGUE;
  let html = "";
  let mi = 0;
  ORDER.forEach(m => {{
    const songs = pool.filter(r => r.movement === m);
    if (!songs.length) return;
    html += `<div class="movement-head"><div class="mnum" style="color:${{COLOUR[m]}}">Movement ${{ROMAN[mi]||(mi+1)}}</div>`+
      `<h3>${{esc(m)}}</h3><p class="mb">${{esc(BLURB[m]||"")}}</p></div>`;
    html += `<div class="cards">${{songs.map(cardHTML).join("")}}</div>`;
    mi++;
  }});
  root.innerHTML = html;
}}

/* ---------- The Listening Instrument: one continuous player over 78 songs ----------
   Every play entry point (native card controls, scatter dots, mood finder, shuffle,
   deep-link) is unified by capturing media events at document level — so the sticky
   player, the card glow, and the Emotional-Field dot all light up in sync, and one
   song flows into the next. No change to how cards are built. */
var ACTIVE = null;   // the <audio> currently in charge
var ORDER_IDS = [];  // catalogue display order, for prev/next/auto-advance
var REDUCE = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

function buildOrderIds() {{
  var ids = [];
  ORDER.forEach(function(m) {{
    CATALOGUE.filter(function(r) {{ return r.movement === m; }})
             .forEach(function(r) {{ ids.push(r.id); }});
  }});
  CATALOGUE.forEach(function(r) {{ if (ids.indexOf(r.id) < 0) ids.push(r.id); }});
  return ids;
}}
function recOf(id) {{ for (var i=0;i<CATALOGUE.length;i++) if (CATALOGUE[i].id===id) return CATALOGUE[i]; return null; }}
function cardOf(id) {{ return document.getElementById("song-"+id); }}
function audioOf(id) {{ var c = cardOf(id); return c ? c.querySelector("audio") : null; }}
function idOfAudio(a) {{ var c = a && a.closest ? a.closest(".card") : null; return c ? c.id.replace(/^song-/, "") : null; }}
function dotOf(id) {{
  var i=-1; for (var k=0;k<CATALOGUE.length;k++) if (CATALOGUE[k].id===id) {{ i=k; break; }}
  return i<0 ? null : document.querySelector('.dot[data-i="'+i+'"]');
}}
function fmtTime(s) {{ s=Math.floor(s||0); var m=Math.floor(s/60), ss=s%60; return m+":"+(ss<10?"0":"")+ss; }}

function highlight(id) {{
  var c2 = document.querySelectorAll(".card.playing"); for (var i=0;i<c2.length;i++) c2[i].classList.remove("playing");
  var c = cardOf(id); if (c) c.classList.add("playing");
  var d2 = document.querySelectorAll(".dot.playing"); for (var j=0;j<d2.length;j++) d2[j].classList.remove("playing");
  var d = dotOf(id); if (d) d.classList.add("playing");
}}
function updateBar(id) {{
  var r = recOf(id); if (!r) return;
  var bar = document.getElementById("player"); bar.removeAttribute("hidden");
  document.body.style.paddingBottom = "76px";
  document.getElementById("plTitle").textContent = r.title || "";
  document.getElementById("plSub").textContent =
    [r.movement, (r.tempo_bpm ? Math.round(r.tempo_bpm)+" BPM" : ""), fmtKey(r)].filter(Boolean).join(" · ");
  document.getElementById("plDot").style.background = COLOUR[r.movement] || "var(--garnet)";
}}
function playById(id) {{
  var card = cardOf(id);
  if (card) card.scrollIntoView({{behavior: REDUCE ? "auto" : "smooth", block: "center"}});
  var a = audioOf(id);
  if (a) a.play().catch(function(){{}});   // the captured 'play' handler does the rest
}}
function playSong(id) {{ playById(id); }}   // scatter dots + legacy callers route here
function step(dir) {{
  var id = ACTIVE ? idOfAudio(ACTIVE) : null;
  var i = id ? ORDER_IDS.indexOf(id) : -1;
  var ni = i<0 ? 0 : (i + dir + ORDER_IDS.length) % ORDER_IDS.length;
  playById(ORDER_IDS[ni]);
}}
function onPlay(a) {{
  if (!a || a.tagName !== "AUDIO") return;
  var all = document.querySelectorAll("audio");
  for (var i=0;i<all.length;i++) if (all[i] !== a) all[i].pause();   // single stream
  ACTIVE = a;
  var id = idOfAudio(a); if (!id) return;
  updateBar(id); highlight(id);
  document.getElementById("plToggle").innerHTML = "&#10074;&#10074;";
  try {{ history.replaceState(null, "", "#"+id); }} catch(e) {{}}
}}
function buildPlayer() {{
  var bar = document.createElement("div");
  bar.id = "player"; bar.setAttribute("hidden", ""); bar.setAttribute("role", "region"); bar.setAttribute("aria-label", "Now playing");
  bar.innerHTML =
    '<div class="pl-wrap">'+
      '<span class="pl-dot" id="plDot"></span>'+
      '<div class="pl-meta"><div class="pl-title" id="plTitle"></div><div class="pl-sub" id="plSub"></div></div>'+
      '<div class="pl-ctrls">'+
        '<button id="plPrev" type="button" aria-label="Previous song" title="Previous">&#9198;</button>'+
        '<button id="plToggle" type="button" aria-label="Play or pause" title="Play / pause">&#9654;</button>'+
        '<button id="plNext" type="button" aria-label="Next song" title="Next">&#9197;</button>'+
      '</div>'+
      '<div class="pl-seek"><span id="plCur">0:00</span>'+
        '<input id="plBar" type="range" min="0" max="1000" value="0" aria-label="Seek within song">'+
        '<span id="plDur">0:00</span></div>'+
      '<button id="plClose" type="button" aria-label="Close player" title="Close">&times;</button>'+
    '</div>';
  document.body.appendChild(bar);
  document.getElementById("plToggle").addEventListener("click", function() {{
    if (!ACTIVE) {{ if (ORDER_IDS[0]) playById(ORDER_IDS[0]); return; }}
    if (ACTIVE.paused) ACTIVE.play().catch(function(){{}}); else ACTIVE.pause();
  }});
  document.getElementById("plPrev").addEventListener("click", function() {{ step(-1); }});
  document.getElementById("plNext").addEventListener("click", function() {{ step(1); }});
  document.getElementById("plClose").addEventListener("click", function() {{
    if (ACTIVE) ACTIVE.pause(); bar.setAttribute("hidden", ""); document.body.style.paddingBottom = "";
  }});
  var seek = document.getElementById("plBar");
  seek.addEventListener("input", function() {{ if (ACTIVE && ACTIVE.duration) ACTIVE.currentTime = (seek.value/1000)*ACTIVE.duration; }});
}}
function initPlayer() {{
  ORDER_IDS = buildOrderIds();
  buildPlayer();
  document.addEventListener("play", function(e) {{ onPlay(e.target); }}, true);
  document.addEventListener("pause", function(e) {{ if (e.target === ACTIVE) document.getElementById("plToggle").innerHTML = "&#9654;"; }}, true);
  document.addEventListener("ended", function(e) {{ if (e.target === ACTIVE) step(1); }}, true);
  document.addEventListener("timeupdate", function(e) {{
    if (e.target !== ACTIVE) return;
    var d = ACTIVE.duration || 0, t = ACTIVE.currentTime || 0;
    if (d) document.getElementById("plBar").value = Math.round(t/d*1000);
    document.getElementById("plCur").textContent = fmtTime(t);
    document.getElementById("plDur").textContent = fmtTime(d);
  }}, true);
  var pa = document.getElementById("playAll");
  if (pa) pa.addEventListener("click", function() {{ if (ORDER_IDS[0]) playById(ORDER_IDS[0]); }});
  var su = document.getElementById("surprise");
  if (su) su.addEventListener("click", function() {{
    var pool = E_ONLY ? CATALOGUE.filter(isE) : CATALOGUE;
    if (!pool.length) return;
    playById(pool[Math.floor(Math.random()*pool.length)].id);
  }});
  document.addEventListener("keydown", function(e) {{
    var tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return;
    if (e.key === " " || e.code === "Space") {{ if (ACTIVE) {{ e.preventDefault(); if (ACTIVE.paused) ACTIVE.play().catch(function(){{}}); else ACTIVE.pause(); }} }}
    else if (e.key === "ArrowRight") {{ if (ACTIVE) {{ e.preventDefault(); step(1); }} }}
    else if (e.key === "ArrowLeft") {{ if (ACTIVE) {{ e.preventDefault(); step(-1); }} }}
  }});
  var h = (location.hash || "").replace(/^#/, "");   // deep-link: cue (no autoplay without a gesture)
  if (h && recOf(h)) {{ var c = cardOf(h); if (c) {{ c.scrollIntoView({{behavior:"auto", block:"center"}}); highlight(h); }} }}
}}

function esc(s) {{ return String(s==null?"":s).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c])); }}

/* ---------- "In the key of E" one-tap filter ---------- */
let E_ONLY = false;
function isE(r) {{ return (r.key || "").trim().split(/\s+/)[0].toUpperCase() === "E"; }}
function wireEFilter() {{
  const btn = document.getElementById("eFilter");
  const note = document.getElementById("catNote");
  if (!btn) return;
  const nE = CATALOGUE.filter(isE).length;
  if (!nE) {{ btn.style.display = "none"; return; }}  // nothing to filter — hide the control
  function apply() {{
    btn.setAttribute("aria-pressed", E_ONLY ? "true" : "false");
    if (note) note.textContent = E_ONLY
      ? `Showing the ${{nE}} songs in the key of E — tap the stat again for all ${{CATALOGUE.length}}.`
      : `All ${{CATALOGUE.length}} songs, in movements. Each as the AI heard it.`;
    renderCatalogue();
    if (E_ONLY) document.getElementById("catalogue").scrollIntoView({{behavior:"smooth", block:"start"}});
  }}
  function toggle() {{ E_ONLY = !E_ONLY; apply(); }}
  btn.addEventListener("click", toggle);
  btn.addEventListener("keydown", e => {{ if (e.key === "Enter" || e.key === " ") {{ e.preventDefault(); toggle(); }} }});
}}

renderField(); renderFeelings(); renderCatalogue(); wireEFilter();
</script>
</body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the interactive Catalogue site from catalogue.json.")
    ap.add_argument("--catalogue", type=Path, default=Path("catalogue/catalogue.json"),
                    help="path to catalogue.json (default: catalogue/catalogue.json)")
    ap.add_argument("--out", type=Path, default=Path("site"), help="output dir (default: ./site)")
    args = ap.parse_args()

    if not args.catalogue.exists():
        sys.exit(f"FAIL: missing {args.catalogue} — run build_catalogue.py first")
    records = json.loads(args.catalogue.read_text())
    if not records:
        sys.exit("FAIL: catalogue.json is empty")

    # Load upcoming songs if present
    upcoming_path = Path("upcoming.json")
    upcoming: list = []
    if upcoming_path.exists():
        upcoming = json.loads(upcoming_path.read_text())

    args.out.mkdir(parents=True, exist_ok=True)
    copy_audio(records, args.out)
    (args.out / "index.html").write_text(html(records, upcoming), encoding="utf-8")
    playable = sum(1 for r in records if r.get("audio"))
    print(f"site -> {args.out / 'index.html'}  ({len(records)} songs, {playable} playable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
