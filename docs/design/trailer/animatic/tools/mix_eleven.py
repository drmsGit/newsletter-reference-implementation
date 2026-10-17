"""Mix the animatic with ElevenLabs material: narration (narrate_tts.py), music segments (generate_music.py) and
three sound effects (tick, whoosh, low hit), placed on the storyboard's scene timeline. Replaces score.py's synthesised
score; the narration is ducked music, the effects are not.

  python mix_eleven.py <narration wav44 dir> <music segments dir> <sfx dir> <out dir>

Writes mix.wav, music.wav (music and effects), narration.wav and placed.json (for build_player.py).
"""
import json
import os
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
NARR, MUSIC, SFX, OUT = (Path(p) for p in sys.argv[1:5])
OUT.mkdir(parents=True, exist_ok=True)

DUR = [("S01", 14), ("S02", 16), ("S03", 20), ("S03b", 14), ("S04", 10), ("S05", 8), ("S06", 10), ("S07", 20),
       ("S08", 22), ("S09", 10), ("S10", 12), ("S11", 8), ("S12", 12), ("S13", 12), ("S14", 12), ("S15", 12),
       ("S16", 16), ("S16b", 12), ("S17", 12), ("S18", 10), ("S19", 6), ("S20", 18)]
T0, c = {}, 0
for sid, d in DUR:
    T0[sid] = c
    c += d
TOTAL = c
LEAD = {"S01": 1.2, "S04": 1.5, "S18": 0.3, "S19": 0.4, "S20": 0.8}
SPLIT = {"S08": (0.8, 8.0, 16.3), "S19": (0.4, 2.2, 4.0)}
N = int((TOTAL + 2) * SR)


def read_wav(path):
    with wave.open(str(path)) as w:
        ch, sr = w.getnchannels(), w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    assert sr == SR, f"{path} is {sr} Hz, expected {SR}"
    return a.reshape(-1, ch) if ch > 1 else a.reshape(-1, 1)


def stereo(a):
    return np.repeat(a, 2, axis=1) if a.shape[1] == 1 else a[:, :2]


def put(buf, start, x, gain=1.0):
    i = int(round(start * SR))
    if i >= len(buf):
        return
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += x[:n] * gain


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    if fin > 0:
        n = min(len(x), int(fin * SR))
        x[:n] *= np.linspace(0, 1, n)[:, None]
    if fout > 0:
        n = min(len(x), int(fout * SR))
        x[-n:] *= np.linspace(1, 0, n)[:, None]
    return x


# ------------------------------------------------------------------ music: one segment per act, evened out and overlapped
music = np.zeros((N, 2), dtype=np.float32)
segs = json.loads((MUSIC / "segments.json").read_text(encoding="utf-8"))
RMS_TARGET = 0.075
for s in segs:
    x = stereo(read_wav(MUSIC / s["file"]))
    body = x[np.abs(x).max(axis=1) > 0.01] if len(x) else x
    rms = float(np.sqrt(np.mean(body ** 2))) if len(body) else 0.05
    x = x * (RMS_TARGET / max(rms, 1e-4))
    if s["id"] == "a5-end":
        x = fade(x, 0.0, 1.5)
        put(music, 269.8, x, 0.9)                                   # the one soft note, after a held silence
        continue
    x = fade(x, 0.0 if s["start"] == 0 else 1.0, 2.0)
    put(music, s["start"], x)
# the pillar card: the swell cuts to silence at 268.0
cut, f = int(268.0 * SR), int(0.04 * SR)
end_note = int(269.7 * SR)
g = np.ones(N, dtype=np.float32)
g[cut - f:cut] = np.linspace(1, 0, f)
g[cut:end_note] = 0.0
music *= g[:, None]

# ------------------------------------------------------------------ sound effects (not ducked)
tick = stereo(read_wav(SFX / "tick-single.wav"))
whoosh = stereo(read_wav(SFX / "whoosh.wav"))
hit = stereo(read_wav(SFX / "low-hit.wav"))
sfx = np.zeros((N, 2), dtype=np.float32)


def pan(x, p):
    a = (p + 1) * np.pi / 4
    return np.stack([x[:, 0] * np.cos(a), x[:, 1] * np.sin(a)], axis=1) * np.sqrt(2)


for t, gain in ((3.0, 0.7), (5.8, 0.7), (8.6, 0.8), (23.5, 0.6), (64.0, 0.9), (179.0, 0.8), (191.0, 0.8), (203.0, 0.8),
                (215.0, 0.8), (221.0, 0.8), (266.0, 1.0)):
    put(sfx, t, hit, gain)                                           # hook, "Powerful", the title, the file drops, the third line
DEFAULT_TICKS = [36.0, 40.5, 44.5, 52.0, 54.5, 57.0, 59.5, 108.0, 113.5, 120.5, 130.0, 153.0] + [252.3 + k for k in range(10)]
# TICKS_JSON: {"ticks": [seconds, ...]} written by the frame project (render/ticks.mjs), one tick per press and cut on screen
TICKS = json.loads(Path(os.environ["TICKS_JSON"]).read_text(encoding="utf-8"))["ticks"] if os.environ.get("TICKS_JSON") else DEFAULT_TICKS
for i, t in enumerate(TICKS):
    put(sfx, t, pan(tick, -0.4 if i % 2 else 0.4), 0.7)               # plugs, doorways, previews, Approve, Release, the montage cuts
for t, gain in ((157.0, 0.45), (159.0, 0.6), (161.0, 0.8)):
    put(sfx, t, tick, gain)                                          # the signal comes back
put(sfx, 162.8, whoosh, 0.8)                                         # the hard cut into the dark
put(sfx, 226.5, whoosh, 0.5)                                         # the swell into the next act

# ------------------------------------------------------------------ narration
nar = np.zeros(N, dtype=np.float32)
placed, parts = {}, {}
for sid, _ in DUR:
    if sid in SPLIT:
        ps = []
        for i, a in enumerate(SPLIT[sid], 1):
            x = read_wav(NARR / f"{sid}_{i}.wav")[:, 0]
            st = T0[sid] + a
            put(nar[:, None], st, x[:, None], 1.0)
            ps.append((st, len(x) / SR))
        parts[sid] = ps
        placed[sid] = (ps[0][0], ps[-1][0] + ps[-1][1] - ps[0][0])
    else:
        x = read_wav(NARR / f"{sid}.wav")[:, 0]
        st = T0[sid] + LEAD.get(sid, 0.6)
        put(nar[:, None], st, x[:, None], 1.0)
        placed[sid] = (st, len(x) / SR)

# duck the music while the voice speaks
block = 441
nb = N // block + 1
env = np.array([np.abs(nar[b * block:(b + 1) * block]).max() if b * block < N else 0 for b in range(nb)])
gain, hold, gains = 1.0, 0, []
for v in env:
    hold = 18 if v > 0.03 else max(0, hold - 1)
    target = 0.45 if hold > 0 else 1.0
    gain += (target - gain) * (0.45 if target < gain else 0.035)
    gains.append(gain)
gcurve = np.interp(np.arange(N) / block, np.arange(nb), np.array(gains))[:, None].astype(np.float32)

bed = music * gcurve + sfx
mix = bed + (nar * 0.95)[:, None]
scale = 0.89 / max(float(np.abs(mix).max()), 1e-6)


def write(path, x, g):
    pcm = (np.clip(x * g, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


write(OUT / "mix.wav", mix, scale)
write(OUT / "music.wav", music * gcurve + sfx, scale)
write(OUT / "narration.wav", np.repeat((nar * 0.95)[:, None], 2, axis=1), scale)
(OUT / "placed.json").write_text(json.dumps({"placed": {k: (round(a, 2), round(b, 2)) for k, (a, b) in placed.items()},
                                             "parts": parts}), encoding="utf-8")
print("mixed", round(N / SR, 1), "s; mix peak scale", round(scale, 3))
