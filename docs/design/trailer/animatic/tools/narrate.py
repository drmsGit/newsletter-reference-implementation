"""Read script A with a macOS voice, one file per scene, and report how long each line takes."""
import re
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path("/Users/diedeslembrouck/Projects/newsletter-reference-implementation/docs/design/trailer")
OUT = Path(sys.argv[1])
VOICE = sys.argv[2] if len(sys.argv) > 2 else "Daniel"
RATE = sys.argv[3] if len(sys.argv) > 3 else "150"
OUT.mkdir(parents=True, exist_ok=True)

sb = (ROOT / "STORYBOARD.md").read_text(encoding="utf-8")
vo = (ROOT / "VOICEOVER.md").read_text(encoding="utf-8")


def secs(t):
    m, s = t.split(":")
    return int(m) * 60 + int(s)


scenes = []
for m in re.finditer(r"^### (S\d\d[a-z]?) · (\d+:\d\d) to (\d+:\d\d) · ([^·\n]+)", sb, flags=re.M):
    scenes.append((m.group(1), secs(m.group(2)), secs(m.group(3)), m.group(4).strip()))

pat = r"\*\*(S\d\d[a-z]?)\*\* \[[^\]]*\]\n([^\n]+)"
lines = {m.group(1): m.group(2).strip() for m in re.finditer(pat, vo.split("## Script A")[1].split("## Script B")[0])}

rows = []
for sid, a, b, title in scenes:
    text = lines[sid]
    sent = 160 if sid == "S18" else 450
    spoken = text.replace(". ", f". [[slnc {sent}]] ").replace(": ", ": [[slnc 220]] ").replace(", ", ", [[slnc 130]] ")
    aiff = OUT / f"{sid}.aiff"
    wav = OUT / f"{sid}.wav"
    subprocess.run(["say", "-v", VOICE, "-r", RATE, "-o", str(aiff), spoken], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", str(aiff), str(wav)], check=True)
    with wave.open(str(wav)) as w:
        dur = w.getnframes() / w.getframerate()
    rows.append((sid, a, b, dur, len(text.split())))
    print(f"{sid:5} scene {a:>3}-{b:<3} ({b-a:>2}s)  read {dur:5.1f}s  words {len(text.split()):>2}  {'TOO LONG' if dur + 0.6 > b - a else ''}")
# S08 is read sentence by sentence, so each sentence can sit on its own shot
s08 = [x.strip() for x in re.split(r"(?<=[.])\s+", lines["S08"]) if x.strip()]
for i, sent in enumerate(s08, 1):
    aiff = OUT / f"S08_{i}.aiff"
    wav = OUT / f"S08_{i}.wav"
    subprocess.run(["say", "-v", VOICE, "-r", RATE, "-o", str(aiff), sent], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", str(aiff), str(wav)], check=True)
print("voice", VOICE, "rate", RATE, "total read", round(sum(r[3] for r in rows), 1), "s of", scenes[-1][2], "s")
