"""Full-length score for the animatic (286 s), arranged on the storyboard's scene timeline.

Mood A (quiet machine) carries the manager's acts, mood B (driven pulse) the developer's. Built from the
same synthesis functions as the two samples (docs/design/trailer/audio/synth.py). No strings, no piano.
Then the narration is mixed in, with the music ducked while the voice speaks.
"""
import array
import math
import random
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, "/Users/diedeslembrouck/Projects/newsletter-reference-implementation/docs/design/trailer/audio")
import synth  # noqa: E402

SR = synth.SR
random.seed(11)
NARR = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

DUR = [("S01", 14), ("S02", 16), ("S03", 20), ("S03b", 14), ("S04", 10), ("S05", 8), ("S06", 10), ("S07", 20),
       ("S08", 22), ("S09", 10), ("S10", 12), ("S11", 8), ("S12", 12), ("S13", 12), ("S14", 12), ("S15", 12),
       ("S16", 16), ("S16b", 12), ("S17", 12), ("S18", 10), ("S19", 6), ("S20", 18)]
T0, c = {}, 0
for sid, d in DUR:
    T0[sid] = c
    c += d
TOTAL = c  # 286
S08_ANCHORS = (0.8, 8.0, 16.3)  # seconds after the scene start: the record, the variant, Approvals
LEAD = {"S01": 1.2, "S04": 1.5, "S18": 0.3, "S19": 0.4, "S20": 0.8}  # voice starts this long after the scene starts


class Mix:
    def __init__(self, seconds):
        self.n = int(seconds * SR)
        self.L = array.array("d", bytes(8 * self.n))
        self.R = array.array("d", bytes(8 * self.n))

    def add(self, start, samples, gain=1.0, pan=0.0):
        a = (pan + 1) * math.pi / 4
        gl, gr = math.cos(a) * gain, math.sin(a) * gain
        i0 = int(start * SR)
        if i0 >= self.n:
            return
        L, R = self.L, self.R
        n = min(len(samples), self.n - i0)
        for k in range(n):
            s = samples[k]
            L[i0 + k] += s * gl
            R[i0 + k] += s * gr


def reverb(L, R, wet):
    n = len(L)
    fb, damp, ap = 0.82, 0.25, 225

    def run(x, delays):
        out = array.array("d", bytes(8 * n))
        bufs = [[0.0] * d for d in delays]
        idx = [0] * len(delays)
        lp = [0.0] * len(delays)
        apb = [0.0] * ap
        api = 0
        for k in range(n):
            s = x[k]
            acc = 0.0
            for j in range(len(delays)):
                b = bufs[j]
                i = idx[j]
                y = b[i]
                lp[j] = y * (1 - damp) + lp[j] * damp
                b[i] = s + lp[j] * fb
                idx[j] = i + 1 if i + 1 < delays[j] else 0
                acc += y
            acc *= 0.33
            z = apb[api]
            w = acc + 0.5 * z
            out[k] = z - 0.5 * w
            apb[api] = w
            api = api + 1 if api + 1 < ap else 0
        return out

    rl, rr = run(L, (1557, 1617, 1491)), run(R, (1580, 1640, 1514))
    for k in range(n):
        L[k] = L[k] * (1 - wet) + rl[k] * wet
        R[k] = R[k] * (1 - wet) + rr[k] * wet


def build_music():
    mix = Mix(TOTAL + 5)
    kal, thump, tick = synth.kalimba, synth.thump, synth.tick
    A_BEAT = 60 / 96
    B_BEAT = 60 / 108

    # ---------------- Act 0, the hook (0 to 14): drone, a pulse, three hits on the three numbers
    mix.add(0, synth.pad((110.0, 164.81), 14, 3.0, 1.5), 0.14)
    for k in range(1, 12):
        mix.add(float(k), thump(62, 42, 0.5), 0.45)
    for t in (3.0, 5.8, 8.6):
        mix.add(t, thump(70, 36, 1.4, glide=0.16, decay=2.6), 0.95)
        mix.add(t, synth.noise_burst(0.2, lp=0.3, decay=11.0), 0.22)

    # ---------------- Act 1 (14 to 74): a pad rising under the problem, the core, the doorways, the title
    mix.add(14, synth.pad((110.0, 164.81, 246.94), 40, 14.0, 4.0), 0.20)
    for k in range(0, 14):
        mix.add(14 + k * 1.25, thump(60, 42, 0.45), 0.30)
    mix.add(23.5, thump(66, 34, 1.6, glide=0.16, decay=2.8), 0.85)       # "Powerful"
    for t in (36.0, 40.5, 44.5):                                          # three plugs
        mix.add(t, tick(), 0.22, -0.3)
    mix.add(47.5, kal(440.0, 3.2, 0.8), 0.30, -0.1)                       # the first soft mallet note
    for i, t in enumerate((52.0, 54.5, 57.0, 59.5)):                      # the four doorways
        mix.add(t, tick(), 0.22, -0.5 + 0.33 * i)
    mix.add(53.0, kal(659.25, 1.6, 0.6), 0.18, 0.2)
    mix.add(58.0, kal(587.33, 1.6, 0.6), 0.18, 0.2)
    mix.add(64.0, thump(70, 34, 2.2, glide=0.18, decay=2.2), 1.0)         # the title: the first full hit
    mix.add(64.0, synth.noise_burst(0.35, lp=0.3, decay=9.0), 0.32)

    # ---------------- Act 2 (74 to 164): mood A, the manager
    bar = 4 * A_BEAT
    t = 66.0
    while t < 144.0:
        mix.add(t, thump(66, 44, 0.55), 0.62 if t < 74 else 0.80)
        mix.add(t + 2 * A_BEAT, thump(60, 42, 0.45), 0.45)
        t += bar
    for t0 in (78.0 + i * bar for i in range(int((150 - 78) / bar))):
        for j, b in enumerate((0.5, 1.5, 2.25, 3.5)):
            mix.add(t0 + b * A_BEAT, tick(), 0.14, -0.5 if j % 2 == 0 else 0.5)
    mix.add(70, synth.pad((110.0, 164.81, 246.94), 44, 3.0, 3.0), 0.20)
    mix.add(106, synth.pad((98.0, 146.83, 220.0), 34, 3.0, 3.0), 0.20)
    mix.add(132, synth.pad((110.0, 164.81, 246.94), 32, 3.0, 4.0), 0.18)
    mix.add(82, synth.pad((55.0,), 66, 1.5, 3.0), 0.50)
    seq = (440.0, 523.25, 659.25, 587.33, 659.25, 523.25)
    step = A_BEAT / 2
    i = 0
    t = 82.0
    while t < 144.0:
        f = seq[i % 6]
        mix.add(t, kal(f, 1.2, 1.0 if i % 6 == 0 else 0.62), 0.28, -0.25)
        i += 1
        t += step
    i = 0
    t = 112.0 + step
    while t < 143.0:
        mix.add(t, kal(seq[i % 6] * 2, 0.9, 0.8 if i % 6 == 3 else 0.5), 0.15, 0.45)
        i += 1
        t += step
    mix.add(108.0, thump(60, 36, 1.6, glide=0.15, decay=2.6), 0.9)        # the triptych locks (S07)
    for t in (113.5, 120.5):
        mix.add(t, tick(), 0.30, 0.0)
    mix.add(130.0, thump(90, 70, 0.25, glide=0.02, decay=14), 0.6)       # "Approve and run"
    mix.add(130.0, tick(), 0.4)
    mix.add(148.0, kal(440.0, 3.0, 0.8), 0.28, 0)                         # the pulse thins to one note
    mix.add(153.0, tick(), 0.35)                                          # "Release"
    for t, g in ((157.0, 0.2), (159.0, 0.3), (161.0, 0.42)):               # the signal comes back
        mix.add(t, tick(), g)

    # ---------------- Act 3 (164 to 240): mood B, the developer
    mix.add(162.8, synth.riser(1.2, a0=0.02, a1=0.3), 0.16)               # the hard cut into the dark
    bb = 4 * B_BEAT
    t = 165.0
    while t < 228.0:
        mix.add(t, thump(82.41, 82.41, 0.4, glide=0.01, decay=7.0), 0.26)
        t += bb
    s16 = B_BEAT / 4
    t0 = 168.0
    while t0 < 228.0:
        for i in range(16):
            acc = 1.0 if i % 4 == 2 else (0.5 if i % 2 == 0 else 0.28)
            mix.add(t0 + i * s16, tick(), 0.09 * acc, -0.4 if i % 2 else 0.4)
        t0 += bb
    notes = (82.41, None, 164.81, 82.41, None, 82.41, 98.0, None,
             82.41, None, 164.81, 82.41, None, 123.47, None, 146.83)
    t0 = 176.0
    while t0 < 228.0:
        for i, f in enumerate(notes):
            if f is not None:
                mix.add(t0 + i * s16, synth.pluck(f, 0.30, 1.0 if i in (0, 8) else 0.6, damp=0.97), 0.30, -0.1)
        t0 += bb
    mix.add(164, synth.pad((82.41, 123.47, 164.81), 76, 3.0, 4.0), 0.10)
    for t in (179.0, 191.0, 203.0, 215.0, 221.0):                         # one low hit per file drop
        mix.add(t - 1.0, synth.riser(1.0, a0=0.02, a1=0.3), 0.14)
        mix.add(t, thump(72, 36, 1.8, glide=0.16, decay=2.4), 0.92)
        mix.add(t, synth.noise_burst(0.25, lp=0.3, decay=10.0), 0.26)
    mix.add(224.0, synth.riser(4.0, a0=0.02, a1=0.35), 0.20)              # the swell into the next act
    mix.add(231.0, synth.pad((82.41, 123.47), 7, 1.5, 3.0), 0.20)         # a soft low note under the ADR

    # ---------------- Act 4 (240 to 268): the two meet, the full swell, then silence
    t = 240.0
    while t < 266.0:
        mix.add(t, thump(66, 44, 0.5), 0.55)
        t += B_BEAT * 2
    mix.add(240.0, synth.riser(12.0, a0=0.01, a1=0.35), 0.24)
    arp = (659.25, 783.99, 987.77, 1174.66)
    t = 244.0
    i = 0
    while t < 266.0:
        mix.add(t, kal(arp[i % 4], 0.9, 0.7 if i % 4 == 0 else 0.4), 0.18, 0.35)
        mix.add(t, kal(seq[i % 6], 1.0, 0.7), 0.20, -0.3)
        i += 1
        t += B_BEAT / 2
    mix.add(240, synth.pad((110.0, 164.81, 246.94), 28, 4.0, 1.0), 0.20)
    mix.add(252, synth.pad((82.41, 123.47, 164.81), 16, 3.0, 1.0), 0.18)
    for k in range(10):                                                   # a tick on every cut of the montage
        mix.add(252.3 + k, tick(), 0.30, -0.4 if k % 2 else 0.4)
    mix.add(266.0, thump(72, 34, 2.0, glide=0.18, decay=2.2), 1.0)        # the third line
    mix.add(266.0, synth.noise_burst(0.3, lp=0.3, decay=9.0), 0.30)

    # ---------------- Act 5 (268 to 286): a gap, one soft mallet note, silence
    mix.add(270.0, kal(440.0, 4.0, 0.8), 0.30, 0)

    reverb(mix.L, mix.R, 0.24)
    # the swell cuts to silence at 268.0 (the pillar card), keeping the end card's one note
    cut = int(268.0 * SR)
    fade = int(0.04 * SR)
    note_start = int(269.9 * SR)
    for k in range(cut - fade, note_start):
        g = max(0.0, 1 - (k - (cut - fade)) / fade)
        mix.L[k] *= g
        mix.R[k] *= g
    return mix


def _place(nar, wavpath, start):
    with wave.open(str(wavpath)) as w:
        raw = array.array("h")
        raw.frombytes(w.readframes(w.getnframes()))
    i0 = int(start * SR)
    for k, v in enumerate(raw):
        if i0 + k < len(nar):
            nar[i0 + k] += v / 32768.0
    return len(raw) / SR


def load_narration(total_n):
    nar = array.array("d", bytes(8 * total_n))
    placed = {}
    parts = {}
    for sid, _ in DUR:
        if sid == "S08":
            ps = []
            for i, a in enumerate(S08_ANCHORS, 1):
                st = T0[sid] + a
                d = _place(nar, NARR / f"S08_{i}.wav", st)
                ps.append((st, d))
            parts[sid] = ps
            placed[sid] = (ps[0][0], ps[-1][0] + ps[-1][1] - ps[0][0])
            continue
        start = T0[sid] + LEAD.get(sid, 0.6)
        d = _place(nar, NARR / f"{sid}.wav", start)
        placed[sid] = (start, d)
    return nar, placed, parts


def duck_gains(nar, n):
    block = 441
    nb = n // block + 1
    g = 1.0
    hold = 0
    gains = []
    for b in range(nb):
        seg = nar[b * block:(b + 1) * block]
        peak = max((abs(x) for x in seg), default=0.0)
        if peak > 0.03:
            hold = 18
        else:
            hold = max(0, hold - 1)
        target = 0.42 if hold > 0 else 1.0
        g += (target - g) * (0.45 if target < g else 0.035)
        gains.append(g)
    return gains, block


def write_wav(path, L, R, gain):
    data = array.array("h")
    for l, r in zip(L, R):
        data.append(int(max(-1.0, min(1.0, l * gain)) * 32767))
        data.append(int(max(-1.0, min(1.0, r * gain)) * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


t_start = time.time()
music = build_music()
n = int((TOTAL + 1) * SR)
mL = music.L[:n]
mR = music.R[:n]
peak_m = max(max(abs(x) for x in mL[::3]), max(abs(x) for x in mR[::3])) or 1.0
mscale = 0.72 / peak_m
nar, placed, parts = load_narration(n)
gains, block = duck_gains(nar, n)

mixL = array.array("d", bytes(8 * n))
mixR = array.array("d", bytes(8 * n))
for k in range(n):
    b = k // block
    g0 = gains[b]
    g1 = gains[b + 1] if b + 1 < len(gains) else g0
    g = g0 + (g1 - g0) * ((k % block) / block)
    v = nar[k] * 0.95
    mixL[k] = mL[k] * mscale * g + v
    mixR[k] = mR[k] * mscale * g + v
pk = max(max(abs(x) for x in mixL[::3]), max(abs(x) for x in mixR[::3])) or 1.0
scale = 0.89 / pk
write_wav(OUT / "mix.wav", mixL, mixR, scale)
write_wav(OUT / "music.wav", array.array("d", (x * mscale for x in mL)), array.array("d", (x * mscale for x in mR)), 1.0)
write_wav(OUT / "narration.wav", array.array("d", (x * 0.95 for x in nar)), array.array("d", (x * 0.95 for x in nar)), 1.0)

report = {sid: (round(s, 2), round(d, 2)) for sid, (s, d) in placed.items()}
(OUT / "placed.json").write_text(__import__("json").dumps({"placed": report, "parts": parts}), encoding="utf-8")
print("rendered", round(time.time() - t_start, 1), "s;", "mix peak scale", round(scale, 3))
