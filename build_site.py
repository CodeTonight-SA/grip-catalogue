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


def html(records: list) -> str:
    data = json.dumps(records, ensure_ascii=False)
    feelings = json.dumps(FEELINGS, ensure_ascii=False)
    colours = json.dumps(MOVEMENT_COLOUR, ensure_ascii=False)
    order = json.dumps(MOVEMENT_ORDER, ensure_ascii=False)
    blurbs = json.dumps(MOVEMENT_BLURB, ensure_ascii=False)
    n = len(records)
    n_instr = sum(1 for r in records if r.get("instrumental"))
    n_afr = sum(1 for r in records if (r.get("language") or "").lower().startswith("afrik"))
    n_movements = len({r["movement"] for r in records})
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
  .card audio {{ width:100%; height:34px; }}
  footer {{ color:var(--muted); font-size:12.5px; padding:40px 0 60px; text-align:center; }}
  footer .caveat {{ font-style:italic; max-width:680px; margin:8px auto 0; }}
</style></head>
<body>
<header class="overture"><div class="wrap">
  <p class="kicker">grip-hear · A Listening Instrument</p>
  <h1>The Catalogue</h1>
  <p class="thesis">Songs by Laurie Scheepers — published tracks, demos, alt-mixes, pre-masters, and phone recordings — heard by the machine he built, and turned into something you can play, map, and search by how you feel.</p>
  <p style="margin:14px 0 0;font-family:Georgia,serif;"><a href="musical-thread.html" style="color:#b0667d;font-size:15px;letter-spacing:.5px;border-bottom:1px solid #8a2846;padding-bottom:2px;text-decoration:none;">Read: The Musical Thread — how this music is written, across the genres &rarr;</a></p>
  <div class="numbers">
    <div class="n"><span class="big">{n}</span><span class="lab">Songs</span></div>
    <div class="n"><span class="big">{n_movements}</span><span class="lab">Movements</span></div>
    <div class="n"><span class="big">{n_instr}</span><span class="lab">Instrumental</span></div>
    <div class="n"><span class="big">{n_afr}</span><span class="lab">In Afrikaans</span></div>
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
  <p class="sublede">All {n} songs, in movements. Each as the AI heard it.</p>
  <div id="catalogue"></div>
</div></section>

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
    ${{audio}}
  </div>`;
}}
function renderCatalogue() {{
  const root = document.getElementById("catalogue");
  let html = "";
  let mi = 0;
  ORDER.forEach(m => {{
    const songs = CATALOGUE.filter(r => r.movement === m);
    if (!songs.length) return;
    html += `<div class="movement-head"><div class="mnum" style="color:${{COLOUR[m]}}">Movement ${{ROMAN[mi]||(mi+1)}}</div>`+
      `<h3>${{esc(m)}}</h3><p class="mb">${{esc(BLURB[m]||"")}}</p></div>`;
    html += `<div class="cards">${{songs.map(cardHTML).join("")}}</div>`;
    mi++;
  }});
  root.innerHTML = html;
}}

/* ---------- play helper: scroll to a song's card and start it ---------- */
function playSong(id) {{
  const card = document.getElementById("song-"+id);
  if (!card) return;
  card.scrollIntoView({{behavior:"smooth", block:"center"}});
  const a = card.querySelector("audio");
  if (a) {{ document.querySelectorAll("audio").forEach(x => {{ if(x!==a) x.pause(); }}); a.play().catch(()=>{{}}); }}
  card.style.transition="box-shadow .3s"; card.style.boxShadow="0 0 0 3px var(--garnet-soft)";
  setTimeout(()=>card.style.boxShadow="none", 1400);
}}

function esc(s) {{ return String(s==null?"":s).replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c])); }}

renderField(); renderFeelings(); renderCatalogue();
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

    args.out.mkdir(parents=True, exist_ok=True)
    copy_audio(records, args.out)
    (args.out / "index.html").write_text(html(records), encoding="utf-8")
    playable = sum(1 for r in records if r.get("audio"))
    print(f"site -> {args.out / 'index.html'}  ({len(records)} songs, {playable} playable)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
