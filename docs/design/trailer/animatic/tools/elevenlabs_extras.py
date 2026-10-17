"""ElevenLabs beyond narration: account status, voices, sound effects and music. Code only until a key is connected.

  python elevenlabs_extras.py status                                   # credits used and left
  python elevenlabs_extras.py voices                                   # names, accents, ids of the voices the key can use
  python elevenlabs_extras.py sfx   "a soft interface click" --seconds 0.5 --out click.mp3 [--send]
  python elevenlabs_extras.py music "calm warm ambient bed ..." --seconds 12 --out bed.mp3 [--send]

Every command that spends credits (sfx, music) is a DRY RUN unless `--send` is given. The key comes from the
environment (ELEVENLABS_API_KEY) or from ONE line of the env file given with --env-file; it is never printed.
The request shapes follow the public API as I know it and are checked only against a local fake server
(`test_providers.py`); a first real call may need a parameter adjusted.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tts_providers import TTSError, key_status, make_ssl_context, read_secret  # noqa: E402

BASE = "https://api.elevenlabs.io"
NAME = "ELEVENLABS_API_KEY"


def _key(env_file):
    k = read_secret(NAME, env_file)
    if not k:
        raise TTSError(f"{NAME} is not set" + (f" and not in {env_file}" if env_file else ""))
    return k


def _call(method, path, key, body=None, base=BASE, timeout=180):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"xi-api-key": key, "Accept": "application/json, audio/mpeg"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base.rstrip("/") + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=make_ssl_context()) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        detail = e.read()[:400].decode("utf-8", "replace")
        raise TTSError(f"HTTP {e.code} for {method} {path.split('?')[0]}: {detail}") from None
    except urllib.error.URLError as e:
        raise TTSError(f"could not reach {path.split('?')[0]}: {e.reason}") from None


def status(env_file=None, base=BASE):
    """{'tier', 'used', 'limit', 'left'} from the subscription endpoint (needs the user_read permission)."""
    s = json.loads(_call("GET", "/v1/user/subscription", _key(env_file), base=base))
    used, limit = s.get("character_count"), s.get("character_limit")
    return {"tier": s.get("tier"), "used": used, "limit": limit,
            "left": (limit - used) if isinstance(used, int) and isinstance(limit, int) else None}


def voices(env_file=None, base=BASE):
    """[{name, voice_id, category, accent, gender, age, description}] (needs the voices_read permission)."""
    v = json.loads(_call("GET", "/v1/voices", _key(env_file), base=base)).get("voices", [])
    out = []
    for x in v:
        lab = x.get("labels") or {}
        out.append({"name": x.get("name"), "voice_id": x.get("voice_id"), "category": x.get("category"),
                    "accent": lab.get("accent"), "gender": lab.get("gender"), "age": lab.get("age"),
                    "description": lab.get("description") or lab.get("descriptive")})
    return out


def sfx_request(text, seconds=None, influence=0.3, output_format="mp3_44100_128"):
    body = {"text": text, "prompt_influence": influence}
    if seconds:
        body["duration_seconds"] = seconds
    return f"/v1/sound-generation?output_format={output_format}", body


def music_request(prompt, seconds, output_format="mp3_44100_128", model_id=None):
    body = {"prompt": prompt, "music_length_ms": int(seconds * 1000)}
    if model_id:
        body["model_id"] = model_id
    return f"/v1/music?output_format={output_format}", body


def sound_effect(text, seconds=None, influence=0.3, env_file=None, base=BASE, output_format="mp3_44100_128"):
    path, body = sfx_request(text, seconds, influence, output_format)
    return _call("POST", path, _key(env_file), body, base=base)


def music(prompt, seconds, env_file=None, base=BASE, output_format="mp3_44100_128", model_id=None):
    path, body = music_request(prompt, seconds, output_format, model_id)
    return _call("POST", path, _key(env_file), body, base=base, timeout=300)


# Approximate credits, to cap a test; the real cost is on the account page. The older docs said 20 credits per second
# for a sound effect with a set duration and 100 with automatic duration; the music price is Diede's price list,
# $0.15 per minute, against $0.10 per 1,000 characters for speech (1 credit = 1 character), that is about 1,500
# credits per minute. All three are estimates.
def est_sfx_credits(seconds):
    return int(20 * seconds) if seconds else 100


def est_music_credits(seconds):
    return int(1500 * seconds / 60)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["status", "voices", "sfx", "music", "check"])
    ap.add_argument("text", nargs="?", default="")
    ap.add_argument("--seconds", type=float, default=None)
    ap.add_argument("--influence", type=float, default=0.3)
    ap.add_argument("--out", default="")
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--send", action="store_true")
    a = ap.parse_args()
    try:
        if a.cmd == "check":
            print(key_status(NAME, a.env_file))
        elif a.cmd == "status":
            print(status(a.env_file))
        elif a.cmd == "voices":
            for v in voices(a.env_file):
                print(f"{v['name']:<22} {v['category'] or '':<12} {v['accent'] or '':<12} {v['gender'] or '':<8} {v['voice_id']}")
        else:
            if not a.text or not a.out:
                ap.error("sfx and music need a text and --out")
            path, body = sfx_request(a.text, a.seconds, a.influence) if a.cmd == "sfx" else music_request(a.text, a.seconds or 10)
            est = est_sfx_credits(a.seconds) if a.cmd == "sfx" else est_music_credits(a.seconds or 10)
            print(f"{a.cmd}: about {est} credits (estimate). Request: POST {path}\n{json.dumps(body, ensure_ascii=False)}")
            if not a.send:
                print("DRY RUN: nothing sent. Add --send to spend credits.")
                return
            data = sound_effect(a.text, a.seconds, a.influence, a.env_file) if a.cmd == "sfx" else music(a.text, a.seconds or 10, a.env_file)
            Path(a.out).write_bytes(data)
            print(f"wrote {a.out} ({len(data)} bytes)")
    except TTSError as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
