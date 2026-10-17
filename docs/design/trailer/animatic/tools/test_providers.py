"""Checks tts_providers.py and narrate_tts.py against a local fake server. No network, no key, no cost.

  python test_providers.py            (run with the Python that has numpy)

It proves the request shapes the code builds (URL, header names, body fields), that a WAV and a raw PCM
response are decoded, that the key is read from the environment and never printed, and that the dry run of
narrate_tts.py sends nothing. It does not prove that the real services accept the requests.
"""
import io
import json
import os
import subprocess
import sys
import threading
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tts_providers import ElevenLabsProvider, OpenAIProvider, TTSError  # noqa: E402

SEEN = []


def tone(seconds, sr=24000, f=220.0):
    t = np.arange(int(seconds * sr)) / sr
    return (np.sin(2 * np.pi * f * t) * 0.4 * 32767).astype("<i2")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        SEEN.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": None})
        if self.path == "/v1/user/subscription":
            n = sum(1 for s in SEEN if s["path"].startswith(("/v1/sound-generation", "/v1/music", "/v1/text-to-speech/")))
            data = json.dumps({"tier": "free", "character_count": 100 * n, "character_limit": 10000}).encode()
        elif self.path == "/v1/voices":
            data = json.dumps({"voices": [{"voice_id": "V1", "name": "Fake Brit", "category": "premade", "labels": {"accent": "british", "gender": "female"}},
                                          {"voice_id": "V2", "name": "Fake US", "category": "premade", "labels": {"accent": "american", "gender": "male"}}]}).encode()
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
        if self.path.startswith("/v1/audio/speech"):
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
                w.writeframes(tone(1.0).tobytes())
            data, ctype = buf.getvalue(), "audio/wav"
        elif self.path.startswith("/v1/text-to-speech/"):
            data, ctype = tone(2.0).tobytes(), "audio/pcm"
        elif self.path.startswith("/v1/sound-generation") or self.path.startswith("/v1/music"):
            data, ctype = b"ID3fake-mp3-bytes", "audio/mpeg"
        else:
            self.send_response(404); self.end_headers(); return
        self.send_response(200); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)


def main():
    srv = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + name)
        ok = ok and cond

    os.environ["TEST_OPENAI_KEY"] = "sk-test-not-real"
    os.environ["TEST_ELEVEN_KEY"] = "xi-test-not-real"
    oa = OpenAIProvider({"voice": "v", "base_url": base + "/v1", "api_key_env": "TEST_OPENAI_KEY"})
    a, sr = oa.synth("Hello there.", direction="Calm.")
    r = SEEN[-1]
    check("openai: path and auth header", r["path"] == "/v1/audio/speech" and r["headers"]["authorization"] == "Bearer sk-test-not-real")
    check("openai: body has model, input, voice, instructions, wav", r["body"] == {"model": "gpt-4o-mini-tts", "input": "Hello there.", "voice": "v", "response_format": "wav", "instructions": "Calm."})
    check("openai: WAV decoded (1.0 s at 24 kHz)", sr == 24000 and abs(len(a) / sr - 1.0) < 0.01 and a.dtype == np.float32)
    check("openai: dry-run plan lists header names, not values", "sk-test" not in json.dumps(oa.plan("x", "y")))

    el = ElevenLabsProvider({"voice_id": "VID", "base_url": base, "api_key_env": "TEST_ELEVEN_KEY", "voice_settings": {"stability": 0.4, "similarity_boost": 0.7, "style": 0.0}})
    a, sr = el.synth("Hello there.", speed=1.1, prev_text="Before.", next_text="After.")
    r = SEEN[-1]
    check("elevenlabs: path, query and key header", r["path"] == "/v1/text-to-speech/VID?output_format=pcm_24000" and r["headers"]["xi-api-key"] == "xi-test-not-real")
    check("elevenlabs: body has text, model, voice settings with speed, neighbours", r["body"]["text"] == "Hello there." and r["body"]["model_id"] == "eleven_multilingual_v2" and r["body"]["voice_settings"]["speed"] == 1.1 and r["body"]["previous_text"] == "Before." and r["body"]["next_text"] == "After.")
    check("elevenlabs: raw PCM decoded (2.0 s at 24 kHz)", sr == 24000 and abs(len(a) / sr - 2.0) < 0.01)

    os.environ.pop("TEST_OPENAI_KEY")
    try:
        oa.synth("x")
        check("openai: refuses without a key", False)
    except TTSError as e:
        check("openai: refuses without a key, and names only the variable", "TEST_OPENAI_KEY" in str(e) and "sk-" not in str(e))

    # narrate_tts: a dry run sends nothing; a --send run against the fake server writes fitted files and caches them
    cfg = {"openai": {"voice": "v", "base_url": base + "/v1", "api_key_env": "TEST_OPENAI_KEY"},
           "elevenlabs": {"voice_id": "VID", "base_url": base, "api_key_env": "TEST_ELEVEN_KEY"}, "pronunciations": {}}
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / "tts-provider-test"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "cfg.json").write_text(json.dumps(cfg))
    before = len(SEEN)
    p = subprocess.run([sys.executable, str(HERE / "narrate_tts.py"), "--provider", "openai", "--config", str(tmp / "cfg.json"), "--out", str(tmp / "dry")], capture_output=True, text=True)
    check("narrate_tts: dry run prints DRY RUN and sends nothing", "DRY RUN" in p.stdout and len(SEEN) == before and p.returncode == 0)
    os.environ["TEST_ELEVEN_KEY"] = "xi-test-not-real"
    p = subprocess.run([sys.executable, str(HERE / "narrate_tts.py"), "--provider", "elevenlabs", "--config", str(tmp / "cfg.json"), "--out", str(tmp / "live"), "--only", "S19", "--send"], capture_output=True, text=True)
    check("narrate_tts: --send for one scene calls the server for its three sentences, plus one fitted retry each (the fake line is too long for its window, and the provider has a speed setting)", p.returncode == 0 and len(SEEN) == before + 6)
    check("narrate_tts: files and report written", (tmp / "live" / "wav44" / "S19_1.wav").exists() and (tmp / "live" / "report.json").exists())
    n = len(SEEN)
    subprocess.run([sys.executable, str(HERE / "narrate_tts.py"), "--provider", "elevenlabs", "--config", str(tmp / "cfg.json"), "--out", str(tmp / "live"), "--only", "S19", "--send"], capture_output=True, text=True)
    check("narrate_tts: a second run is served from the cache (no new requests)", len(SEEN) == n)
    p = subprocess.run([sys.executable, str(HERE / "narrate_tts.py"), "--provider", "elevenlabs", "--config", str(tmp / "cfg.json"), "--out", str(tmp / "big"), "--budget-chars", "100", "--send"], capture_output=True, text=True)
    check("narrate_tts: refuses a run above the character budget", p.returncode == 2 and "REFUSED" in p.stdout)

    # extras: key from an env file (never printed), status, voices, sound effects, music, and the capped test run
    import elevenlabs_extras as ex
    envf = tmp / "fake.env"
    envf.write_text("OTHER=1\nexport ELEVENLABS_API_KEY='xi-from-file'  # a comment\n")
    os.environ.pop("ELEVENLABS_API_KEY", None)
    st = ex.status(str(envf), base)
    check("extras: key read from an env file, status parsed", SEEN[-1]["headers"]["xi-api-key"] == "xi-from-file" and st["limit"] == 10000 and st["left"] == st["limit"] - st["used"])
    vs = ex.voices(str(envf), base)
    check("extras: voices parsed (name, accent, gender, id)", vs[0] == {"name": "Fake Brit", "voice_id": "V1", "category": "premade", "accent": "british", "gender": "female", "age": None, "description": None})
    d = ex.sound_effect("a click", 0.5, 0.3, str(envf), base)
    r = SEEN[-1]
    check("extras: sound effect request shape", r["path"] == "/v1/sound-generation?output_format=mp3_44100_128" and r["body"] == {"text": "a click", "prompt_influence": 0.3, "duration_seconds": 0.5} and d.startswith(b"ID3"))
    d = ex.music("calm bed", 12, str(envf), base)
    r = SEEN[-1]
    check("extras: music request shape", r["path"] == "/v1/music?output_format=mp3_44100_128" and r["body"] == {"prompt": "calm bed", "music_length_ms": 12000} and d.startswith(b"ID3"))
    from tts_providers import key_status
    check("extras: key status never shows the value", "xi-from-file" not in key_status("ELEVENLABS_API_KEY", str(envf)) and "found in" in key_status("ELEVENLABS_API_KEY", str(envf)))
    n = len(SEEN)
    p = subprocess.run([sys.executable, str(HERE / "elevenlabs_test_run.py"), "--env-file", str(envf), "--out", str(tmp / "etest-dry"), "--base-url", base], capture_output=True, text=True)
    check("test run: dry run sends nothing and prints the plan", p.returncode == 0 and "DRY RUN" in p.stdout and len(SEEN) == n and "xi-from-file" not in p.stdout)
    p = subprocess.run([sys.executable, str(HERE / "elevenlabs_test_run.py"), "--env-file", str(envf), "--out", str(tmp / "etest"), "--base-url", base, "--send", "--no-convert"], capture_output=True, text=True)
    outdir = tmp / "etest"
    check("test run: --send wrote narration, 3 effects and 2 music beds, and picked the British voice",
          p.returncode == 0 and (outdir / "tts" / "wav44" / "S19_1.wav").exists() and len(list((outdir / "sfx").glob("*.mp3"))) == 3
          and len(list((outdir / "music").glob("*.mp3"))) == 2 and "Fake Brit" in p.stdout)
    check("test run: shows credits before and after, and never the key", "credits before" in p.stdout and "credits after" in p.stdout and "xi-from-file" not in p.stdout + p.stderr)
    p = subprocess.run([sys.executable, str(HERE / "elevenlabs_test_run.py"), "--env-file", str(envf), "--out", str(tmp / "etest2"), "--base-url", base, "--max-credits", "50", "--send"], capture_output=True, text=True)
    check("test run: refuses a plan above --max-credits", p.returncode == 2 and "REFUSED" in p.stdout)
    print("\nALL OK" if ok else "\nSOME CHECKS FAILED")
    sys.exit(0 if ok else 1)


main()
