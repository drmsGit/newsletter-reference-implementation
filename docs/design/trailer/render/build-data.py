"""Build data/timeline.json for the scenes from the storyboard, the placed narration, the captions and the checks' code.

  python3 build-data.py

Reads (all in docs/design/trailer): STORYBOARD.md (scene times), animatic/tools/placed.json (where each narration line
starts and how long it is), animatic/captions.srt (the burned-in captions), PREPRODUCTION-CHECKS*.md (the exact files of
the four file drops, for the developer scenes) and product.json (the name). Nothing here is hand-typed timing.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAILER = HERE.parent
ROOT = TRAILER.parent.parent.parent
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)


def secs(t):
    m, s = t.split(":")
    return int(m) * 60 + int(s)


sb = (TRAILER / "STORYBOARD.md").read_text(encoding="utf-8")
scenes = []
for m in re.finditer(r"^### (S\d\d[a-z]?) · (\d+:\d\d) to (\d+:\d\d) · ([^·\n]+)", sb, flags=re.M):
    scenes.append({"id": m.group(1), "start": secs(m.group(2)), "end": secs(m.group(3)), "title": m.group(4).strip()})

# data/placed.json is the one the last mix wrote (mix_eleven.py, copied here); the older file in animatic/tools is the draft's
placed = OUT / "placed.json"
pj = json.loads((placed if placed.exists() else TRAILER / "animatic/tools/placed.json").read_text(encoding="utf-8"))
voice = {k: {"start": v[0], "dur": v[1]} for k, v in pj["placed"].items()}
parts = {k: [{"start": a, "dur": b} for a, b in v] for k, v in pj.get("parts", {}).items()}


def srt_time(s):
    h, m, rest = s.split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


cues = []
for block in (TRAILER / "animatic/captions.srt").read_text(encoding="utf-8").strip().split("\n\n"):
    lines = block.split("\n")
    a, b = lines[1].split(" --> ")
    cues.append({"s": srt_time(a), "e": srt_time(b), "t": " ".join(lines[2:])})

# the exact files of the drops, from the checks' appendices: "### A. `path`" followed by a fenced block
code = {}
for fn in ("PREPRODUCTION-CHECKS.md", "PREPRODUCTION-CHECKS-2.md"):
    txt = (TRAILER / fn).read_text(encoding="utf-8")
    for m in re.finditer(r"^### [A-G]\. `([^`]+)`[^\n]*\n(?:.*?\n)*?```(\w*)\n(.*?)```", txt, flags=re.M | re.S):
        path, lang, body = m.group(1), m.group(2), m.group(3)
        code[path] = {"lang": lang, "text": body.rstrip("\n")}   # the later file (round 2) wins: both providers in factory.py

# files of the repository that the developer scenes show as they are
def head(path, n):
    return "\n".join((ROOT / path).read_text(encoding="utf-8").splitlines()[:n])


ADR = ROOT / "docs/architecture/ADR"
adr101 = next(ADR.glob("ADR-101 — *.md")).read_text(encoding="utf-8").splitlines()
adr143 = next(ADR.glob("ADR-143 — *.md")).read_text(encoding="utf-8").splitlines()
i101 = next(i for i, l in enumerate(adr101) if l.startswith("## Decision"))
i143 = next(i for i, l in enumerate(adr143) if l.startswith("**1. Mode C"))
files = {
    "factory_head": head("backend/app/delivery/providers/factory.py", 12),
    "top_score_head": head("backend/app/decision/strategies/top_score.py", 48),
    "adr101_name": next(ADR.glob("ADR-101 — *.md")).name,
    "adr101_text": "\n".join(adr101[:12] + [""] + adr101[i101 - 2:i101 + 5]),
    "adr143_name": next(ADR.glob("ADR-143 — *.md")).name,
    "adr143_text": " ".join(l.strip() for l in adr143[i143:i143 + 2]),
}
product = json.loads((ROOT / "product.json").read_text(encoding="utf-8"))
data = {"fps": 24, "size": [1920, 1080], "total": scenes[-1]["end"], "name": product["name"],
        "scenes": scenes, "voice": voice, "parts": parts, "cues": cues, "code": code, "files": files}
(OUT / "timeline.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("scenes", len(scenes), "| voice lines", len(voice), "| parts", {k: len(v) for k, v in parts.items()}, "| cues", len(cues), "| code files", list(code))
