"""A small, capped ElevenLabs test for the trailer: narration (S12 and S19), three sound effects, two music beds.

  python elevenlabs_test_run.py --env-file /path/to/.env --out DIR                 # dry run: plan and estimated credits
  python elevenlabs_test_run.py --env-file /path/to/.env --out DIR --send          # really spend credits

The key is read from the environment or from one line of the env file; it is never printed. Nothing is sent
without --send, and a plan above --max-credits is refused. Account credits are read before and after when the key
has the permission, so the real cost is visible; a key without that permission continues on estimates. Output is
for listening only: until the account is on a plan with commercial rights, none of it goes into the published film.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import elevenlabs_extras as ex  # noqa: E402
from tts_providers import TTSError, key_status  # noqa: E402

SFX = [
    ("tick", "a single soft interface click, dry and clean, very short, no reverb", 0.5),
    ("low-hit", "a deep low cinematic impact hit with a short natural tail, no music, no voice", 2.0),
    ("whoosh", "a quiet hushed whoosh, a short transition swell, no music", 1.2),
]
MUSIC = [
    ("mood-a-manager", "Calm, warm, minimal ambient bed for a product film. Soft kalimba and mallet motif, gentle pad, light ticks, "
                       "relaxed tempo, optimistic and quiet. Instrumental. No strings, no piano, no vocals, nothing dramatic.", 12),
    ("mood-b-developer", "Quiet but driven minimal pulse for a developer scene. Muted plucked bass, soft ticks, warm and dark, restrained, "
                         "a steady groove, one low hit at the start. Instrumental. No strings, no piano, no vocals.", 12),
]
NARRATION_SCENES = "S12,S19"
# Used when the key cannot list voices (no voices_read permission). Premade ElevenLabs voices; the ids are from memory,
# and a wrong id is refused by the service before any credit is spent, so the next candidate is tried.
FALLBACK_VOICES = [("Alice (British, female)", "Xb7hH8MSUJpSbSDYk0k2"), ("Lily (British, female)", "pFZP5JQG7iQjIQuC4Bku"),
                   ("George (British, male)", "JBFqnCBsd6RMkjVDRZzb"), ("Daniel (British, male)", "onwK4e9ZLuTAKqWW03F9"),
                   ("Rachel (American, female)", "21m00Tcm4TlvDq8ikWAM")]


def pick_candidates(a):
    """[(label, voice id)] to try for the narration."""
    if a.voice_id:
        return [("given voice id", a.voice_id)]
    try:
        vs = ex.voices(a.env_file, a.base_url)
        print("voices the key can use:", ", ".join(f"{v['name']} ({v['accent'] or '?'}, {v['gender'] or '?'})" for v in vs[:20]))
        pick = next((v for v in vs if (v["accent"] or "").lower().startswith("british") and (v["category"] or "") == "premade"), None) \
            or next((v for v in vs if (v["accent"] or "").lower().startswith("british")), None) or (vs[0] if vs else None)
        if pick:
            return [(f"{pick['name']} ({pick['accent']}, {pick['gender']})", pick["voice_id"])]
    except TTSError as e:
        print("the key cannot list voices (" + str(e)[:90] + "...): trying premade voices by id")
    return FALLBACK_VOICES


def narrate(a, out, candidates):
    for label, voice_id in candidates:
        cfg = {"kokoro": {}, "openai": {},
               "elevenlabs": {"voice_id": voice_id, "env_file": a.env_file, "base_url": a.base_url,
                              "model_id": "eleven_multilingual_v2", "output_format": "pcm_24000",
                              "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0}},
               "pronunciations": {}}
        (out / "tts").mkdir(parents=True, exist_ok=True)
        (out / "tts" / "voice-config.json").write_text(json.dumps(cfg), encoding="utf-8")
        r = subprocess.run([sys.executable, str(HERE / "narrate_tts.py"), "--provider", "elevenlabs",
                            "--config", str(out / "tts" / "voice-config.json"), "--out", str(out / "tts"),
                            "--only", NARRATION_SCENES, "--send"], capture_output=True, text=True)
        if r.returncode == 0:
            print(f"narration voice: {label}, id {voice_id}")
            print(r.stdout.strip()[-900:])
            return
        print(f"voice {label}: {(r.stdout.strip() or r.stderr.strip())[-260:]}")
    raise TTSError("narration failed for every candidate voice")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice-id", default="", help="skip the voice lookup and use this id")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--max-credits", type=int, default=1500)
    ap.add_argument("--base-url", default=ex.BASE)
    ap.add_argument("--no-convert", action="store_true", help="skip afconvert (used by the tests)")
    a = ap.parse_args()
    out = Path(a.out)
    narr_chars = 190  # S12 plus the three sentences of S19, about
    est = {"narration": narr_chars, "sfx": sum(ex.est_sfx_credits(s) for _, _, s in SFX),
           "music": sum(ex.est_music_credits(s) for _, _, s in MUSIC)}
    total = sum(est.values())
    print(key_status(ex.NAME, a.env_file))
    print(f"plan: narration {est['narration']} + sound effects {est['sfx']} + music {est['music']} = about {total} credits "
          f"(estimates; free credits are 10,000)")
    if total > a.max_credits:
        print(f"REFUSED: {total} is above --max-credits {a.max_credits}")
        sys.exit(2)
    if not a.send:
        print("DRY RUN: nothing sent. Add --send to run it.")
        for name, text, secs in SFX:
            print(f"  sfx {name}: {secs} s  {text}")
        for name, text, secs in MUSIC:
            print(f"  music {name}: {secs} s  {text[:80]}...")
        return
    try:
        before = None
        try:
            before = ex.status(a.env_file, a.base_url)
            print("credits before:", before)
        except TTSError as e:
            print("credit status not available (continuing on estimates):", str(e)[:120])
        narrate(a, out, pick_candidates(a))
        (out / "sfx").mkdir(parents=True, exist_ok=True)
        for name, text, secs in SFX:
            data = ex.sound_effect(text, secs, 0.3, a.env_file, a.base_url)
            (out / "sfx" / f"{name}.mp3").write_bytes(data)
            print(f"sfx {name}: {len(data)} bytes")
        (out / "music").mkdir(parents=True, exist_ok=True)
        for name, text, secs in MUSIC:
            data = ex.music(text, secs, a.env_file, a.base_url)
            (out / "music" / f"{name}.mp3").write_bytes(data)
            print(f"music {name}: {len(data)} bytes")
        if not a.no_convert:
            for f in list((out / "sfx").glob("*.mp3")) + list((out / "music").glob("*.mp3")):
                subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", str(f), str(f.with_suffix(".wav"))], check=False)
        try:
            after = ex.status(a.env_file, a.base_url)
            print("credits after:", after)
            if before and before.get("used") is not None and after.get("used") is not None:
                print("credits spent by this test:", after["used"] - before["used"])
        except TTSError:
            pass
    except TTSError as e:
        print("STOPPED:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
