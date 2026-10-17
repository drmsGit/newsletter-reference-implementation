"""Generate the film's music with ElevenLabs, one segment per act (see music-segments.json).

  python generate_music.py --env-file /path/to/.env --out DIR                 # dry run: plan and estimated credits
  python generate_music.py --env-file /path/to/.env --out DIR --send          # spend credits
  python generate_music.py ... --send --only a2-manager                       # one segment again

A segment is cached by a hash of its prompt and length, so only a changed segment is paid for again. The estimate
uses the price list ($0.15 per minute, about 1,500 credits). `--max-credits` refuses a plan above it. The key is read
by name from the environment or ONE line of the env file and is never printed. Output: DIR/<id>.mp3 and a 44.1 kHz
mono-or-stereo WAV next to it, plus DIR/segments.json.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import elevenlabs_extras as ex  # noqa: E402
from tts_providers import TTSError, key_status  # noqa: E402

OVERLAP = 2.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--spec", default=str(HERE / "music-segments.json"))
    ap.add_argument("--only", default="")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--max-credits", type=int, default=12000)
    ap.add_argument("--base-url", default=ex.BASE)
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    only = {x.strip() for x in a.only.split(",") if x.strip()}
    plan = []
    for s in spec["segments"]:
        if only and s["id"] not in only:
            continue
        length = (s["end"] - s["start"]) + OVERLAP
        prompt = (s["prompt"] + " " + spec.get("common", "")).strip()
        key = hashlib.sha1(json.dumps([prompt, length], sort_keys=True).encode()).hexdigest()[:12]
        plan.append({"id": s["id"], "start": s["start"], "end": s["end"], "length": length, "prompt": prompt, "key": key,
                     "cached": (out / f"{s['id']}-{key}.mp3").exists()})
    new = [p for p in plan if not p["cached"]]
    est = sum(ex.est_music_credits(p["length"]) for p in new)
    print(key_status(ex.NAME, a.env_file))
    print(f"{len(plan)} segments, {len(new)} to generate, {sum(p['length'] for p in new):.0f} s of music, about {est} credits "
          f"(about ${sum(p['length'] for p in new) / 60 * 0.15:.2f} at $0.15 per minute)")
    if est > a.max_credits:
        print(f"REFUSED: above --max-credits {a.max_credits}")
        sys.exit(2)
    if not a.send:
        for p in new:
            print(f"  {p['id']}: {p['length']:.0f} s  {p['prompt'][:100]}...")
        print("DRY RUN: nothing sent. Add --send.")
        return
    done = []
    try:
        for p in plan:
            mp3 = out / f"{p['id']}-{p['key']}.mp3"
            if not mp3.exists():
                data = ex.music(p["prompt"], p["length"], a.env_file, a.base_url)
                mp3.write_bytes(data)
                print(f"{p['id']}: generated {len(data)} bytes")
            else:
                print(f"{p['id']}: cached")
            wav = mp3.with_suffix(".wav")
            subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", str(mp3), str(wav)], check=True)
            done.append({**{k: p[k] for k in ("id", "start", "end", "length")}, "file": wav.name})
    except TTSError as e:
        print("STOPPED:", e)
        sys.exit(1)
    finally:
        (out / "segments.json").write_text(json.dumps(done, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
