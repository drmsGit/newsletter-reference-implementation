"""Build the animatic player, the captions file and the pacing report from the storyboard and the placed narration."""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path("/Users/diedeslembrouck/Projects/newsletter-reference-implementation/docs/design/trailer")
OUT = ROOT / "animatic"
SCR = Path(sys.argv[1])  # scratch output folder with mix.m4a etc. and placed.json
OUT.mkdir(exist_ok=True)

sb = (ROOT / "STORYBOARD.md").read_text(encoding="utf-8")
_pj = json.loads((SCR / "placed.json").read_text(encoding="utf-8"))
placed = _pj["placed"]
parts = _pj.get("parts", {})


def secs(t):
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def tc(s):
    return f"{int(s) // 60}:{int(s) % 60:02d}"


scenes = []
cur = None
for line in sb.splitlines():
    m = re.match(r"### (S\d\d[a-z]?) · (\d+:\d\d) to (\d+:\d\d) · ([^·\n]+)(.*)", line)
    if m:
        cur = {"id": m.group(1), "start": secs(m.group(2)), "end": secs(m.group(3)), "title": m.group(4).strip(),
               "hero": "HERO" in m.group(5), "teaser": " T" in m.group(5) or m.group(5).strip().startswith("T"), "f": {}}
        scenes.append(cur)
        continue
    m = re.match(r"- \*\*([A-Za-z]+)\.\*\* (.*)", line)
    if m and cur is not None:
        cur["f"].setdefault(m.group(1), m.group(2))


def plain(s):
    s = re.sub(r"\[\[([^\]|]+)[^\]]*\]\]", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    return s


LIVE = "../../ux-audit-2026-10-17/screenshots/"
REND = "../../renders/"
shots = []
for sc in scenes:
    names = re.findall(r"`(\d\d-[\w-]+\.(?:jpg|png))`", sc["f"].get("Source", ""))
    dur = sc["end"] - sc["start"]
    world = "black" if sc["id"] == "S01" else ("dark" if sc["id"] in ("S12", "S13", "S14", "S15", "S16", "S16b") else "light")
    text_lines = re.findall(r'"([^"]+)"', sc["f"].get("Text", ""))
    see = plain(sc["f"].get("See", ""))
    if sc["id"] in ("S04", "S20"):
        name = json.loads(Path("/Users/diedeslembrouck/Projects/newsletter-reference-implementation/product.json").read_text(encoding="utf-8"))["name"]
        text_lines = [name] + text_lines[:3]
    elif not text_lines:
        text_lines = [q for q in re.findall(r'"([^"]+)"', see) if len(q) < 60][:3]
    first = re.split(r"(?<=[.])\s", see, maxsplit=1)[0]
    if names:
        weights = {"S08": [4, 3.5, 3, 3, 1.2, 1.3, 6]}.get(sc["id"]) or [1] * len(names)
        weights = (weights + [1] * len(names))[:len(names)]
        tot = sum(weights)
        acc = 0.0
        for i, nm in enumerate(names):
            a0 = acc / tot
            acc += weights[i]
            a1 = acc / tot
            kind = "audit" if nm.endswith(".jpg") else "render"
            shots.append({"scene": sc["id"], "start": sc["start"] + dur * a0, "end": sc["start"] + dur * a1,
                          "img": (LIVE if kind == "audit" else REND) + nm, "kind": kind, "name": nm, "world": world,
                          "text": text_lines, "see": first})
    else:
        shots.append({"scene": sc["id"], "start": sc["start"], "end": sc["end"], "img": None, "kind": "built", "name": "",
                      "world": world, "text": text_lines, "see": first})

# ------- captions: cut each scene's narration into short cues, timed over the real audio
cues = []
for sc in scenes:
    sid = sc["id"]
    text = plain(sc["f"]["A"])
    st, du = placed[sid]
    if sid in parts:
        sents = [x.strip() for x in re.split(r"(?<=[.])\s+", text) if x.strip()]
        for (ps, pd), sent in zip(parts[sid], sents):
            cues.append({"s": round(ps, 2), "e": round(ps + pd - 0.05, 2), "t": sent, "scene": sid})
        continue
    sentparts = [p.strip() for p in re.split(r"(?<=[.?!:])\s+", text) if p.strip()]
    out = []
    for p in sentparts:
        if len(p) > 74 and "," in p:
            mid = len(p) // 2
            cut = min((m.start() for m in re.finditer(r",\s", p)), key=lambda k: abs(k - mid))
            out += [p[:cut + 1].strip(), p[cut + 1:].strip()]
        else:
            out.append(p)
    total = sum(len(x) for x in out)
    acc = 0
    for x in out:
        a = st + du * acc / total
        acc += len(x)
        b = st + du * acc / total
        cues.append({"s": round(a, 2), "e": round(b - 0.05, 2), "t": x, "scene": sid})


def srt_time(x):
    h, r = divmod(x, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def wrap(t):
    if len(t) <= 42:
        return t
    mid = len(t) // 2
    sp = min((m.start() for m in re.finditer(" ", t)), key=lambda k: abs(k - mid))
    return t[:sp] + "\n" + t[sp + 1:]


(OUT / "captions.srt").write_text("\n".join(
    f"{i + 1}\n{srt_time(c['s'])} --> {srt_time(c['e'])}\n{wrap(c['t'])}\n" for i, c in enumerate(cues)), encoding="utf-8")

# ------- pacing report
rows = []
over = []
for sc in scenes:
    st, du = placed[sc["id"]]
    end = st + du
    head = sc["end"] - end
    spoken = sum(d for _, d in parts[sc["id"]]) if sc["id"] in parts else du
    rows.append((sc["id"], sc["title"], sc["end"] - sc["start"], st - sc["start"], spoken, head))
    if head < 1.0:
        over.append((sc["id"], head))
speech = sum(r[4] for r in rows)
total = scenes[-1]["end"]
md = ["---", "type: reference", "status: draft", "created: 2026-10-17", "---", "",
      "# Animatic: pacing report", "",
      "The first animatic of the trailer: the reference stills in storyboard order, a **synthetic read of script A** (ElevenLabs, voice Alice, British female), a full-length score made of ElevenLabs music (one segment per act, no strings, no piano) with the sound effects (single tick, whoosh, low hit), and captions. It tests the pacing; it is not the trailer and it does not use the frames the film will have. See [[TRAILER-BRIEF]] and [[STORYBOARD]]. Open `animatic.html` in Chrome and press Play.", "",
      f"**Speech:** {speech:.0f} s of {total} s, {100 * speech / total:.0f} percent of the film is narrated. Every line fits its window at the voice's natural pace (none had to be sped up). S08 and S19 are read sentence by sentence so each sentence sits on its own shot or card.", "",
      "| Scene | Title | Scene length | Voice starts | Voice reads | Headroom |", "|---|---|---|---|---|---|"]
for sid, title, ln, lead, du, head in rows:
    flag = "  **tight**" if head < 1.0 else ""
    md.append(f"| {sid} | {title} | {ln} s | +{lead:.1f} s | {du:.1f} s | {head:.1f} s{flag} |")
md += ["", "**Tight scenes** (under one second of headroom): " + (", ".join(f"{a} ({b:.1f} s)" for a, b in over) + ". A slower human read would overflow these, so either the scene gets a second or two, or the line is trimmed." if over else "none."),
       "Scenes with a lot of room (over eight seconds of headroom): " + (", ".join(f"{r[0]} ({r[5]:.1f} s)" for r in rows if r[5] > 8) or "none") + ". The end card holds its silence by design.", "",
       "**What the tracks are.** `mix.m4a` is narration over the score with the music ducked while the voice speaks; `narration.m4a` and `music.m4a` are the two layers alone. `captions.srt` is cut from the narration and timed over the measured audio. The music is one ElevenLabs generation per act, placed on the scene timeline and evened out; the sound effects (a single tick, a whoosh, a low hit) sit on the hook's numbers, the title, each file drop, the montage cuts and the third line; the swell cuts to silence at the three lines, and one soft note closes the end card.", "",
       "**Not in the animatic:** the redrawn frames, the camera moves, the sound of clicks tied to the cursor, the first-person script B.", ""]
(OUT / "PACING.md").write_text("\n".join(md), encoding="utf-8")

for f in ("mix.m4a", "narration.m4a", "music.m4a"):
    shutil.copy(SCR / f, OUT / f)

# ------- the player
data = {"scenes": [{"id": s["id"], "start": s["start"], "end": s["end"], "title": s["title"], "hero": s["hero"],
                    "teaser": s["teaser"], "A": plain(s["f"]["A"])} for s in scenes],
        "shots": shots, "cues": cues, "total": total}

page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trailer animatic</title>
<style>
:root{--bg:#1b1815;--text:#f4eee6;--muted:#b5aa9b;--accent:#6fc3dd;--line:#36302a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.4 -apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif}
.wrap{max-width:1280px;margin:0 auto;padding:12px 16px 24px}
#frame{position:relative;width:100%;aspect-ratio:16/9;overflow:hidden;border-radius:6px;background:#000}
#stage{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",system-ui,sans-serif}
.world-light{background:#fcf8f2;color:#1f1b16}.world-dark{background:#14110f;color:#f4eee6}.world-black{background:#000;color:#f4eee6}
#badge{position:absolute;left:48px;top:36px;font-size:28px;opacity:.75}
#badge b{font-family:ui-monospace,Menlo,monospace;margin-right:14px}
#shot{position:absolute;left:0;top:90px;width:1920px;height:800px;display:flex;align-items:center;justify-content:center}
#shot img{max-width:1500px;max-height:760px;box-shadow:0 0 0 2px rgba(0,0,0,.18),0 10px 40px rgba(0,0,0,.25);border-radius:8px}
#ref{position:absolute;right:48px;top:44px;font-size:22px;opacity:.7;text-align:right;max-width:700px}
.card{max-width:1500px;text-align:left}.card p{margin:10px 0;font-size:64px;line-height:1.15;font-weight:650}
.card small{display:block;margin-top:34px;font-size:28px;font-weight:400;opacity:.65;max-width:1300px}
#cap{position:absolute;left:0;right:0;bottom:44px;text-align:center;padding:0 160px}
#cap span{display:inline-block;background:rgba(0,0,0,.82);color:#fff;font-size:46px;line-height:1.25;padding:10px 26px;border-radius:6px;white-space:pre-line}
#ctl{margin-top:10px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
button,select{background:#2a2622;color:var(--text);border:1px solid var(--line);border-radius:6px;padding:6px 12px;font:inherit}
button:hover{border-color:var(--accent)}
#time{font-variant-numeric:tabular-nums;color:var(--muted)}
#bar{position:relative;display:flex;gap:2px;margin-top:10px;height:34px;cursor:pointer}
#bar div.seg{position:relative;border-radius:3px;background:#2a2622;border:1px solid var(--line);font-size:11px;color:var(--muted);text-align:center;padding-top:8px;overflow:hidden}
#bar div.seg.hero{background:#243a42}#bar div.seg.on{outline:2px solid var(--accent)}
#head{position:absolute;top:-4px;bottom:-4px;width:2px;background:var(--accent);pointer-events:none}
#info{margin-top:10px;color:var(--muted)}
a{color:var(--accent)}
</style></head><body><div class="wrap">
<div id="frame"><div id="stage" class="world-black"><div id="badge"></div><div id="ref"></div><div id="shot"></div><div id="cap"></div></div></div>
<div id="ctl"><button id="play">Play</button><button id="prev">Previous scene</button><button id="next">Next scene</button>
<select id="track"><option value="mix.m4a">Narration and music</option><option value="narration.m4a">Narration only</option><option value="music.m4a">Music only</option></select>
<label><input type="checkbox" id="caps" checked> Captions</label><span id="time"></span></div>
<div id="bar"></div><div id="info"></div>
<p style="color:var(--muted);margin-top:18px">A first animatic: reference stills in storyboard order, a synthetic read of script A, a full-length mood score and captions. Stills marked "audit capture" were taken at 16:54 on 2026-10-17 and are older than the app; they stand in for frames that are drawn later. Space plays and pauses, left and right arrows jump a scene. See <code>PACING.md</code> for the numbers.</p>
</div>
<script>
const D = __DATA__;
const audio = new Audio("mix.m4a"); audio.preload = "auto";
const q = new URLSearchParams(location.search); let vt = q.get("t") !== null ? parseFloat(q.get("t")) : null;
const now = () => vt !== null ? vt : audio.currentTime;
const stage = document.getElementById("stage"), frame = document.getElementById("frame");
function fit(){ stage.style.transform = "scale(" + (frame.clientWidth/1920) + ")"; }
addEventListener("resize", fit); fit();
const bar = document.getElementById("bar");
D.scenes.forEach(s => { const d = document.createElement("div"); d.className = "seg" + (s.hero ? " hero" : ""); d.style.flex = (s.end - s.start) + " 1 0"; d.textContent = s.id.slice(1); d.title = s.id + " " + s.title; d.onclick = e => { e.stopPropagation(); seek(s.start); }; bar.appendChild(d); });
const head = document.createElement("div"); head.id = "head"; bar.appendChild(head);
bar.onclick = e => { const r = bar.getBoundingClientRect(); seek((e.clientX - r.left) / r.width * D.total); };
const $ = id => document.getElementById(id);
function seek(t){ vt = null; audio.currentTime = Math.max(0, Math.min(D.total, t)); render(); }
function sceneAt(t){ return D.scenes.find(s => t >= s.start && t < s.end) || D.scenes[D.scenes.length-1]; }
let lastShot = null;
function render(){
  const t = now(), sc = sceneAt(t);
  const sh = D.shots.find(x => t >= x.start && t < x.end) || D.shots[D.shots.length-1];
  if (sh !== lastShot){
    lastShot = sh; stage.className = "world-" + sh.world;
    const box = $("shot"); box.innerHTML = "";
    if (sh.img){ const im = document.createElement("img"); im.src = sh.img; box.appendChild(im);
      $("ref").textContent = sh.kind === "audit" ? "Audit capture, 16:54: older than the app" : "Design render: invented data, layout only"; }
    else { const c = document.createElement("div"); c.className = "card";
      (sh.text.length ? sh.text : [sc.title]).slice(0,4).forEach(x => { const p = document.createElement("p"); p.textContent = x; c.appendChild(p); });
      const sm = document.createElement("small"); sm.textContent = "Built for the film: " + sh.see; c.appendChild(sm); box.appendChild(c); $("ref").textContent = ""; }
  }
  $("badge").innerHTML = "<b>" + sc.id + "</b>" + Math.floor(sc.start/60) + ":" + String(Math.floor(sc.start%60)).padStart(2,"0") + " · " + sc.title;
  const cue = D.cues.find(c => t >= c.s && t <= c.e);
  $("cap").innerHTML = ($("caps").checked && cue) ? "<span></span>" : ""; if (cue && $("caps").checked) $("cap").firstChild.textContent = cue.t;
  head.style.left = (t / D.total * 100) + "%";
  [...bar.querySelectorAll(".seg")].forEach((el,i) => el.classList.toggle("on", D.scenes[i] === sc));
  const m = x => Math.floor(x/60) + ":" + String(Math.floor(x%60)).padStart(2,"0");
  $("time").textContent = m(t) + " / " + m(D.total);
  $("info").textContent = sc.id + ": " + sc.A;
}
function loop(){ render(); requestAnimationFrame(loop); } loop();
$("play").onclick = () => { if (audio.paused) { audio.play(); } else { audio.pause(); } };
audio.onplay = () => $("play").textContent = "Pause"; audio.onpause = () => $("play").textContent = "Play";
audio.onended = () => $("play").textContent = "Play";
$("next").onclick = () => { const i = D.scenes.indexOf(sceneAt(audio.currentTime)); seek(D.scenes[Math.min(i+1, D.scenes.length-1)].start); };
$("prev").onclick = () => { const sc = sceneAt(audio.currentTime); const i = D.scenes.indexOf(sc); seek(audio.currentTime - sc.start > 1.5 ? sc.start : D.scenes[Math.max(i-1,0)].start); };
$("track").onchange = e => { const t = audio.currentTime, was = !audio.paused; audio.src = e.target.value; audio.currentTime = t; if (was) audio.play(); };
addEventListener("keydown", e => { if (e.code === "Space") { e.preventDefault(); $("play").click(); } if (e.code === "ArrowRight") $("next").click(); if (e.code === "ArrowLeft") $("prev").click(); });
</script></body></html>
""".replace("__DATA__", json.dumps(data, ensure_ascii=False))
(OUT / "animatic.html").write_text(page, encoding="utf-8")
print("wrote", OUT, "shots", len(shots), "cues", len(cues), "speech", round(speech), "of", total, "tight:", over)
