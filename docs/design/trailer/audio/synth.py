"""Two short mood samples for the trailer, synthesised from nothing (pure Python, no libraries).

A: quiet machine (the manager's world): sub pulse, soft ticks, kalimba motif, a drone with open fifths.
B: driven pulse (the developer's world): muted plucks, ticks, a bass line, one low hit per file drop.

No strings, no piano. Nothing is sampled, so there is nothing to license.
"""
import array
import math
import random
import struct
import sys
import time
import wave

SR = 44100
TWO_PI = 2 * math.pi
random.seed(7)


class Mix:
    def __init__(self, seconds):
        self.n = int(seconds * SR)
        self.L = [0.0] * self.n
        self.R = [0.0] * self.n

    def add(self, start, samples, gain=1.0, pan=0.0):
        """pan -1 (left) .. +1 (right), constant power."""
        a = (pan + 1) * math.pi / 4
        gl, gr = math.cos(a) * gain, math.sin(a) * gain
        i0 = int(start * SR)
        L, R = self.L, self.R
        n = min(len(samples), self.n - i0)
        for k in range(n):
            s = samples[k]
            L[i0 + k] += s * gl
            R[i0 + k] += s * gr


def kalimba(freq, dur=1.6, vel=1.0):
    n = int(dur * SR)
    out = [0.0] * n
    partials = ((1.0, 1.00, 2.6), (2.0, 0.18, 4.5), (5.4, 0.10, 9.0))
    for ratio, amp, rate in partials:
        w = TWO_PI * freq * ratio / SR
        dec = math.exp(-rate / SR)
        env = amp * vel
        for k in range(n):
            out[k] += env * math.sin(w * k)
            env *= dec
    # a soft attack and a short click for the tine
    for k in range(int(0.003 * SR)):
        out[k] *= k / (0.003 * SR)
    for k in range(int(0.004 * SR)):
        out[k] += (random.random() * 2 - 1) * 0.12 * vel * (1 - k / (0.004 * SR))
    return out


def pluck(freq, dur=0.5, vel=1.0, damp=0.985):
    """Karplus-Strong, kept short: a muted string."""
    period = max(2, int(SR / freq))
    buf = [(random.random() * 2 - 1) * vel for _ in range(period)]
    # a little smoothing: the string is muted, not bright
    for _ in range(2):
        buf = [0.5 * (buf[i] + buf[i - 1]) for i in range(period)]
    n = int(dur * SR)
    out = [0.0] * n
    idx = 0
    for k in range(n):
        v = buf[idx]
        out[k] = v
        nxt = buf[(idx + 1) % period]
        buf[idx] = 0.5 * (v + nxt) * damp
        idx = (idx + 1) % period
    fade = int(0.02 * SR)
    for k in range(fade):
        out[n - 1 - k] *= k / fade
    return out


def thump(f0, f1, dur, glide=0.12, decay=5.0):
    n = int(dur * SR)
    out = [0.0] * n
    phase = 0.0
    for k in range(n):
        t = k / SR
        f = f1 + (f0 - f1) * math.exp(-t / glide)
        phase += TWO_PI * f / SR
        out[k] = math.sin(phase) * math.exp(-decay * t)
    for k in range(int(0.002 * SR)):
        out[k] *= k / (0.002 * SR)
    return out


def tick(dur=0.012, vel=1.0):
    n = int(dur * SR)
    prev = 0.0
    out = [0.0] * n
    for k in range(n):
        x = random.random() * 2 - 1
        out[k] = (x - prev) * vel * math.exp(-k / (0.0025 * SR))
        prev = x
    return out


def noise_burst(dur, lp=0.35, decay=12.0):
    n = int(dur * SR)
    y = 0.0
    out = [0.0] * n
    for k in range(n):
        y += lp * ((random.random() * 2 - 1) - y)
        out[k] = y * math.exp(-decay * k / SR)
    return out


def riser(dur, a0=0.01, a1=0.35):
    n = int(dur * SR)
    y = 0.0
    out = [0.0] * n
    for k in range(n):
        p = k / n
        a = a0 + (a1 - a0) * p * p
        y += a * ((random.random() * 2 - 1) - y)
        out[k] = y * (p ** 2.2)
    return out


def pad(freqs, dur, fade_in, fade_out, lfo=0.13):
    n = int(dur * SR)
    out = [0.0] * n
    waves = []
    for f in freqs:
        for det in (-0.9, 0.9):
            waves.append(TWO_PI * f * (1 + det / 1200) / SR)
    for k in range(n):
        t = k / SR
        env = 1.0
        if t < fade_in:
            env = t / fade_in
        elif t > dur - fade_out:
            env = max(0.0, (dur - t) / fade_out)
        env = env * env * (3 - 2 * env)
        s = 0.0
        for w in waves:
            s += math.sin(w * k)
        # a little 2nd harmonic of the lowest voice keeps it from being a bare sine
        s += 0.35 * math.sin(waves[0] * 2 * k)
        out[k] = s * env * (1 + 0.10 * math.sin(TWO_PI * lfo * t)) / len(waves)
    return out


def reverb(L, R, wet=0.24):
    n = len(L)
    combs_l = (1557, 1617, 1491)
    combs_r = (1580, 1640, 1514)
    ap = 225
    fb = 0.82
    damp = 0.25

    def run(x, delays):
        out = [0.0] * n
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
            # one all-pass for density (Schroeder form)
            z = apb[api]
            w = acc + 0.5 * z
            out[k] = z - 0.5 * w
            apb[api] = w
            api = api + 1 if api + 1 < ap else 0
        return out

    rl, rr = run(L, combs_l), run(R, combs_r)
    return ([a * (1 - wet) + b * wet for a, b in zip(L, rl)],
            [a * (1 - wet) + b * wet for a, b in zip(R, rr)])


def finish(L, R, path, peak=0.7):
    m = max(max(abs(x) for x in L), max(abs(x) for x in R)) or 1.0
    g = peak / m
    data = array.array("h")
    for l, r in zip(L, R):
        data.append(int(max(-1, min(1, l * g)) * 32767))
        data.append(int(max(-1, min(1, r * g)) * 32767))
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    rms = math.sqrt(sum(x * x for x in L[::7]) / max(1, len(L[::7]))) * g
    return {"seconds": len(L) / SR, "peak_before_norm": round(m, 3), "gain": round(g, 3), "rms": round(rms, 3)}


# --------------------------------------------------------------------------- A
def sample_a(path):
    bpm = 96
    beat = 60 / bpm
    bars = 13
    body = bars * 4 * beat
    mix = Mix(body + 4.0)

    def T(bar, b=0.0):
        return ((bar - 1) * 4 + b) * beat

    # sub pulse
    for bar in range(1, 13):
        mix.add(T(bar, 0), thump(66, 44, 0.55), 0.85, 0)
        mix.add(T(bar, 2), thump(60, 42, 0.45), 0.5, 0)
    mix.add(T(13, 0), thump(62, 40, 1.2, decay=3.5), 0.9, 0)

    # ticks from bar 3
    for bar in range(3, 13):
        for i, b in enumerate((0.5, 1.5, 2.25, 3.5)):
            mix.add(T(bar, b), tick(vel=1.0), 0.16, -0.5 if i % 2 == 0 else 0.5)

    # drone with open fifths, moving once
    mix.add(T(2), pad((110.0, 164.81, 246.94), 5 * 4 * beat + 3, 2.5, 3.0), 0.20, 0)
    mix.add(T(7), pad((98.0, 146.83, 220.0), 4 * 4 * beat + 3, 3.0, 3.0), 0.20, 0)
    mix.add(T(11), pad((110.0, 164.81, 246.94), 3 * 4 * beat + 2, 2.5, 4.0), 0.20, 0)

    # kalimba motif: a six-note loop against a four-beat bar
    seq = (440.0, 523.25, 659.25, 587.33, 659.25, 523.25)
    step = beat / 2
    t0 = T(5)
    steps = int((T(13) - t0) / step)
    for i in range(steps):
        f = seq[i % 6]
        vel = 1.0 if i % 6 == 0 else 0.62
        mix.add(t0 + i * step, kalimba(f, 1.4, vel), 0.30, -0.25)
    t1 = T(9) + step  # a second voice, one eighth late, an octave up, quieter
    steps2 = int((T(13) - t1) / step)
    for i in range(steps2):
        f = seq[i % 6] * 2
        vel = 0.8 if i % 6 == 3 else 0.5
        mix.add(t1 + i * step, kalimba(f, 1.0, vel), 0.17, 0.45)

    # bass
    mix.add(T(5), pad((55.0,), 8 * beat * 4 + 1.5, 1.5, 2.0), 0.55, 0)

    # riser into the hit, then the hit
    mix.add(T(8, 2), riser(2 * beat * 2 + 0.0), 0.28, 0)
    mix.add(T(9), thump(70, 34, 2.2, glide=0.18, decay=2.2), 1.0, 0)
    mix.add(T(9), noise_burst(0.35, lp=0.30, decay=9.0), 0.35, 0)

    # last note rings out
    mix.add(T(13, 0), kalimba(440.0, 3.4, 0.8), 0.30, 0)

    L, R = reverb(mix.L, mix.R, wet=0.26)
    return finish(L, R, path)


# --------------------------------------------------------------------------- B
def sample_b(path):
    bpm = 108
    beat = 60 / bpm
    bars = 15
    body = bars * 4 * beat
    mix = Mix(body + 3.5)

    def T(bar, b=0.0):
        return ((bar - 1) * 4 + b) * beat

    s16 = beat / 4
    # ticks all the way, 16ths, accented on the offbeat
    for bar in range(1, 15):
        for i in range(16):
            acc = 1.0 if i % 4 == 2 else (0.5 if i % 2 == 0 else 0.28)
            mix.add(T(bar) + i * s16, tick(vel=1.0), 0.12 * acc, -0.4 if i % 2 else 0.4)

    # muted pluck ostinato from bar 3
    notes = (82.41, None, 164.81, 82.41, None, 82.41, 98.0, None,
             82.41, None, 164.81, 82.41, None, 123.47, None, 146.83)
    for bar in range(3, 15):
        for i, f in enumerate(notes):
            if f is None:
                continue
            vel = 1.0 if i in (0, 8) else 0.6
            mix.add(T(bar) + i * s16, pluck(f, 0.32, vel, damp=0.97), 0.34, -0.1)

    # bass line from bar 4: E2, with a second harmonic
    for bar in range(4, 15):
        for i in (0, 6, 10):
            mix.add(T(bar) + i * s16, thump(82.41, 82.41, 0.35, glide=0.01, decay=7.0), 0.30, 0)

    # a very quiet drone
    mix.add(T(1), pad((82.41, 123.47, 164.81), bars * 4 * beat + 2, 3.0, 4.0), 0.10, 0)

    # sparkle from bar 9
    arp = (659.25, 783.99, 987.77, 1174.66)
    for bar in range(9, 15):
        for i in range(8):
            mix.add(T(bar) + i * (beat / 2), kalimba(arp[i % 4], 0.9, 0.55 if i % 4 == 0 else 0.35), 0.15, 0.4)

    # one low hit per file drop, each with a short riser
    for bar in (4, 9, 14):
        mix.add(T(bar - 1, 2), riser(beat * 2, a0=0.02, a1=0.3), 0.20, 0)
        mix.add(T(bar), thump(72, 36, 1.8, glide=0.16, decay=2.4), 0.95, 0)
        mix.add(T(bar), noise_burst(0.25, lp=0.3, decay=10.0), 0.30, 0)

    L, R = reverb(mix.L, mix.R, wet=0.20)
    return finish(L, R, path)


if __name__ == "__main__":
    which, path = sys.argv[1], sys.argv[2]
    t = time.time()
    info = sample_a(path) if which == "a" else sample_b(path)
    info["render_seconds"] = round(time.time() - t, 1)
    print(which, info)
