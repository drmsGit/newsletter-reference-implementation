"""Read script A with any provider in tts_providers.py, one file per scene (S08 and S19 per sentence), each fitted
into its window on the scene timeline. The voice is one switch, `--provider`.

  python narrate_tts.py --provider kokoro     --config voice-config.json --out DIR
  python narrate_tts.py --provider openai     --config voice-config.json --out DIR            # dry run: prints the plan and the cost
  python narrate_tts.py --provider openai     --config voice-config.json --out DIR --only S12,S19 --send
  python narrate_tts.py --provider elevenlabs --config voice-config.json --out DIR --send

Paid providers do nothing but print what they would send, unless `--send` is given and the API key is in the
environment. Every synthesised line is cached under DIR/cache by a hash of the provider settings, the text, the
direction and the neighbouring lines, so only a changed line is paid for again. `--only` re-reads chosen scenes.
`--budget-chars` refuses a run that would send more than that many characters (default 6000, about two passes)
unless `--yes` is given. Direction (tone) comes from `voice-direction.json` and is used by OpenAI only.
"""
import argparse
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tts_providers import TTSError, apply_pronunciations, make_provider  # noqa: E402

TRAILER = Path(__file__).resolve().parents[2]          # docs/design/trailer
LEAD = {"S01": 1.2, "S04": 1.5, "S18": 0.3, "S19": 0.4, "S20": 0.8}   # equal to score.py
SPLIT = {"S08": (0.8, 8.0, 16.3), "S19": (0.4, 2.2, 4.0)}               # sentence anchors, equal to score.py

# Approximate prices, for the dry run only. ElevenLabs: Diede's screenshot of its API price list, 2026-10-17.
# OpenAI: a community figure, about 1.5 cents per minute; check the official page.
ELEVEN_V2_V3_PER_1K_USD = 0.10
ELEVEN_FLASH_PER_1K_EUR = 0.05
OPENAI_PER_MIN_USD = 0.015


def secs(t):
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def load_script():
    sb = (TRAILER / "STORYBOARD.md").read_text(encoding="utf-8")
    vo = (TRAILER / "VOICEOVER.md").read_text(encoding="utf-8")
    scenes = [(m.group(1), secs(m.group(2)), secs(m.group(3)))
              for m in re.finditer(r"^### (S\d\d[a-z]?) · (\d+:\d\d) to (\d+:\d\d) ·", sb, flags=re.M)]
    pat = r"\*\*(S\d\d[a-z]?)\*\* \[[^\]]*\]\n([^\n]+)"
    lines = {m.group(1): m.group(2).strip() for m in re.finditer(pat, vo.split("## Script A")[1].split("## Script B")[0])}
    return scenes, lines


def build_pieces(scenes, lines):
    """[(name, scene id, text, window seconds)] in film order."""
    pieces = []
    for sid, a0, b0 in scenes:
        if sid in SPLIT:
            anchors = SPLIT[sid]
            sents = [x.strip() for x in re.split(r"(?<=[.])\s+", lines[sid]) if x.strip()]
            for i, (sent, anc) in enumerate(zip(sents, anchors)):
                nxt = anchors[i + 1] if i + 1 < len(anchors) else (b0 - a0)
                pieces.append((f"{sid}_{i + 1}", sid, sent, nxt - anc - 0.3))
        else:
            pieces.append((sid, sid, lines[sid], (b0 - a0) - LEAD.get(sid, 0.6) - 0.25))
    return pieces


def write_wav16(path, audio, sr):
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def read_wav16(path):
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
    return a, sr


def level(a):
    """One loudness for every line: RMS of the voiced samples to about -19 dBFS, peaks under 0.95."""
    voiced = a[np.abs(a) > 0.02]
    rms = float(np.sqrt(np.mean(voiced ** 2))) if len(voiced) else 0.1
    a = a * (0.11 / max(rms, 1e-4))
    return a * min(1.0, 0.95 / max(float(np.abs(a).max()), 1e-4))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", required=True, choices=["kokoro", "openai", "elevenlabs"])
    ap.add_argument("--config", required=True, help="voice-config.json (see voice-config.example.json)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--direction", default=str(Path(__file__).resolve().parent / "voice-direction.json"))
    ap.add_argument("--only", default="", help="comma-separated scene ids, for example S12,S19")
    ap.add_argument("--send", action="store_true", help="really call a paid provider")
    ap.add_argument("--budget-chars", type=int, default=6000)
    ap.add_argument("--yes", action="store_true", help="allow a run above the character budget")
    args = ap.parse_args()

    cfg_all = json.loads(Path(args.config).read_text(encoding="utf-8"))
    cfg = cfg_all[args.provider]
    pron = cfg_all.get("pronunciations", {})
    direction_all = json.loads(Path(args.direction).read_text(encoding="utf-8")) if Path(args.direction).exists() else {}
    provider = make_provider(args.provider, cfg)
    free = args.provider == "kokoro"
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    out = Path(args.out)
    for sub in ("wav-native", "wav44", "cache"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    scenes, lines = load_script()
    pieces = build_pieces(scenes, lines)
    base_speed = 0.95 if args.provider == "kokoro" else 1.0
    cap = 1.2

    def direction_for(sid):
        if not provider.uses_direction:
            return ""
        scene = (direction_all.get("scenes") or {}).get(sid, "")
        return " ".join(x for x in (direction_all.get("base", ""), scene) if x)

    # what would be sent, and what is already cached
    todo = []
    for i, (name, sid, text, window) in enumerate(pieces):
        if only and sid not in only:
            continue
        prev_text = pieces[i - 1][2] if i > 0 else ""
        next_text = pieces[i + 1][2] if i + 1 < len(pieces) else ""
        spoken = apply_pronunciations(text, pron)
        key = provider.cache_key(spoken, direction_for(sid), prev_text, next_text, base_speed if provider.supports_speed else None)
        todo.append({"name": name, "sid": sid, "text": text, "spoken": spoken, "window": window, "prev": prev_text,
                     "next": next_text, "key": key, "cached": (out / "cache" / f"{key}.wav").exists()})

    new_chars = sum(len(t["spoken"]) for t in todo if not t["cached"])
    all_chars = sum(len(t["spoken"]) for t in todo)
    words = sum(len(t["text"].split()) for t in todo)
    minutes = words / 150.0
    print(f"provider {args.provider}: {len(todo)} lines, {all_chars} characters, {sum(t['cached'] for t in todo)} already cached, "
          f"{new_chars} characters to send, about {minutes:.1f} minutes of speech")
    if not free:
        print(f"  approximate cost of a full pass: OpenAI about ${minutes * OPENAI_PER_MIN_USD:.2f} (community figure); "
              f"ElevenLabs multilingual v2/v3 about ${all_chars / 1000 * ELEVEN_V2_V3_PER_1K_USD:.2f}, "
              f"Turbo/Flash about EUR {all_chars / 1000 * ELEVEN_FLASH_PER_1K_EUR:.2f}. Check the current price lists.")
        if not args.send:
            print("DRY RUN: nothing is sent. Add --send to call the provider. The first requests that would go out:")
            for t in todo[:3]:
                print(json.dumps(provider.plan(t["spoken"], direction_for(t["sid"]), base_speed if provider.supports_speed else None,
                                               t["prev"], t["next"]), ensure_ascii=False, indent=1))
            return
        if new_chars > args.budget_chars and not args.yes:
            print(f"REFUSED: {new_chars} characters is above --budget-chars {args.budget_chars}. Use --only, or add --yes.")
            sys.exit(2)

    report = []
    for t in todo:
        cache = out / "cache" / f"{t['key']}.wav"
        sp = base_speed
        tries = 0
        max_tries = 6 if free else 2
        while True:
            if cache.exists():
                audio, sr = read_wav16(cache)
                hit = True
            else:
                try:
                    audio, sr = provider.synth(t["spoken"], direction_for(t["sid"]), sp if provider.supports_speed else None,
                                               t["prev"], t["next"])
                except TTSError as e:
                    print(f"{t['name']}: {e}")
                    sys.exit(1)
                write_wav16(cache, audio, sr)
                hit = False
            d = len(audio) / sr
            tries += 1
            if d <= t["window"] or not provider.supports_speed or sp >= cap or tries >= max_tries:
                break
            sp = round(min(cap, sp * d / t["window"] * 1.02), 2)   # one calculated step, not a crawl: paid retries cost money
            cache = out / "cache" / f"{provider.cache_key(t['spoken'], direction_for(t['sid']), t['prev'], t['next'], sp)}.wav"
        a = level(audio.astype(np.float32))
        native = out / "wav-native" / f"{t['name']}.wav"
        write_wav16(native, a, sr)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", str(native), str(out / "wav44" / f"{t['name']}.wav")], check=True)
        over = d > t["window"] + 0.01
        print(f"{t['name']:6} window {t['window']:5.1f}s  read {d:5.1f}s  speed {sp:.2f}  {'cached' if hit else 'sent' if not free else 'made'}{'  OVER' if over else ''}")
        report.append({"name": t["name"], "window": round(t["window"], 2), "read": round(d, 2), "speed": sp, "cached": hit, "over": over})
    (out / "report.json").write_text(json.dumps({"provider": args.provider, "cfg": {k: v for k, v in cfg.items() if "key" not in k.lower()},
                                                 "lines": report}, indent=1), encoding="utf-8")
    print("provider", args.provider, "total read", round(sum(r["read"] for r in report), 1), "s")


if __name__ == "__main__":
    main()
