"""Text-to-speech providers behind one small interface, so the narrator's voice is a single swap.

Kokoro (local, free), OpenAI (gpt-4o-mini-tts, takes written instructions) and ElevenLabs (paid). The two paid
providers are CODE ONLY here: nothing in this file runs against a live service unless `send=True` is passed and
the API key is in the environment, and `test_providers.py` exercises them against a local fake server. The request
shapes follow the providers' public APIs as I know them and have NOT been tried against the real services:
the first real call should be one short line (`narrate_tts.py --only S19 --send`).

Every provider returns mono float32 samples and the sample rate.
"""
import hashlib
import io
import json
import os
import urllib.error
import urllib.request
import wave

import numpy as np


class TTSError(RuntimeError):
    pass


def apply_pronunciations(text, mapping):
    """Replace whole words before sending, for example {"CRM": "C R M"}. Captions keep the original text."""
    import re
    for word, spoken in (mapping or {}).items():
        text = re.sub(r"\b" + re.escape(word) + r"\b", spoken, text)
    return text


def read_secret(name, env_file=None):
    """The value of one variable: from the environment first, else from one line of an env file.
    The file is parsed for that NAME only; nothing else in it is kept, and the value is never printed or put in an
    error message. Returns "" when it is not there."""
    v = os.environ.get(name, "")
    if v or not env_file:
        return v
    try:
        with open(os.path.expanduser(env_file), encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s.startswith("export "):
                    s = s[7:].lstrip()
                if s.startswith("#") or "=" not in s:
                    continue
                k, _, val = s.partition("=")
                if k.strip() != name:
                    continue
                val = val.strip()
                if val[:1] in ("'", '"'):                      # quoted: up to the closing quote
                    end = val.find(val[0], 1)
                    return val[1:end] if end > 0 else val[1:]
                return val.split(" #")[0].strip()              # unquoted: drop an inline comment
    except OSError:
        return ""
    return ""


def key_status(name, env_file=None):
    """A report about a key that is safe to print: where it was found and how long it is, never the value."""
    if os.environ.get(name):
        return f"{name}: found in the environment ({len(os.environ[name])} characters)"
    v = read_secret(name, env_file)
    if v:
        return f"{name}: found in {env_file} ({len(v)} characters)"
    return f"{name}: NOT found in the environment" + (f" or in {env_file}" if env_file else "")


def make_ssl_context():
    """A normal, verifying TLS context. The python.org build of Python has no root certificates of its own, so when the
    default store is empty the macOS system bundle (or certifi, if installed) is loaded. Verification is never turned off."""
    import ssl
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats().get("x509_ca", 0) == 0:
        candidates = []
        try:
            import certifi
            candidates.append(certifi.where())
        except ImportError:
            pass
        candidates += ["/etc/ssl/cert.pem", "/opt/homebrew/etc/ca-certificates/cert.pem"]
        for c in candidates:
            if os.path.exists(c):
                ctx.load_verify_locations(c)
                break
    return ctx


def _wav_bytes_to_float(data):
    with wave.open(io.BytesIO(data)) as w:
        sr, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise TTSError(f"expected 16-bit WAV, got {8 * width}-bit")
    a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    return a, sr


def _pcm_bytes_to_float(data):
    return np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0


def _post(url, headers, body, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=make_ssl_context()) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode("utf-8", "replace")
        raise TTSError(f"HTTP {e.code} from {url.split('?')[0]}: {detail}") from None
    except urllib.error.URLError as e:
        raise TTSError(f"could not reach {url.split('?')[0]}: {e.reason}") from None


class Provider:
    name = "base"
    supports_speed = False
    uses_direction = False   # does free-text direction (tone) change the result?

    def __init__(self, cfg):
        self.cfg = cfg

    def cache_key(self, text, direction, prev_text, next_text, speed):
        payload = json.dumps([self.name, self.cfg, text, direction, prev_text, next_text, speed], sort_keys=True)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    def plan(self, text, direction="", speed=None, prev_text="", next_text=""):
        """What would be sent: url, header NAMES (never values) and body. Used for the dry run."""
        return {"provider": self.name}

    def synth(self, text, direction="", speed=None, prev_text="", next_text=""):
        raise NotImplementedError


class KokoroProvider(Provider):
    """Local and free. cfg: models_dir, voice, lang, espeak_lib, espeak_data."""
    name = "kokoro"
    supports_speed = True

    def __init__(self, cfg):
        super().__init__(cfg)
        self._k = None

    def _kokoro(self):
        if self._k is None:
            from kokoro_onnx import Kokoro
            from kokoro_onnx.config import EspeakConfig
            md = self.cfg["models_dir"]
            esp = EspeakConfig(lib_path=self.cfg.get("espeak_lib", "/opt/homebrew/lib/libespeak-ng.dylib"),
                               data_path=self.cfg.get("espeak_data", "/opt/homebrew/share/espeak-ng-data"))
            self._k = Kokoro(os.path.join(md, "kokoro-v1.0.onnx"), os.path.join(md, "voices-v1.0.bin"), espeak_config=esp)
        return self._k

    def synth(self, text, direction="", speed=None, prev_text="", next_text=""):
        audio, sr = self._kokoro().create(text, voice=self.cfg["voice"], speed=speed or 0.95, lang=self.cfg.get("lang", "en-gb"))
        return audio.astype(np.float32), sr


class OpenAIProvider(Provider):
    """gpt-4o-mini-tts with written instructions (tone, pace, how to end a question). No speed parameter.
    cfg: voice, model, base_url, api_key_env, timeout. The instructions are the 'direction'."""
    name = "openai"
    uses_direction = True

    def _request(self, text, direction):
        base = self.cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")
        body = {"model": self.cfg.get("model", "gpt-4o-mini-tts"), "input": text,
                "voice": self.cfg["voice"], "response_format": "wav"}
        if direction:
            body["instructions"] = direction
        return f"{base}/audio/speech", body

    def plan(self, text, direction="", speed=None, prev_text="", next_text=""):
        url, body = self._request(text, direction)
        return {"provider": self.name, "url": url, "headers": ["Authorization", "Content-Type"], "body": body}

    def synth(self, text, direction="", speed=None, prev_text="", next_text=""):
        key = read_secret(self.cfg.get("api_key_env", "OPENAI_API_KEY"), self.cfg.get("env_file"))
        if not key:
            raise TTSError(f"{self.cfg.get('api_key_env', 'OPENAI_API_KEY')} is not set")
        url, body = self._request(text, direction)
        data = _post(url, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, body,
                     self.cfg.get("timeout", 120))
        return _wav_bytes_to_float(data)


class ElevenLabsProvider(Provider):
    """ElevenLabs text-to-speech. Raw 16-bit PCM back. Tone comes from the voice settings and the voice itself;
    free-text direction is not sent. cfg: voice_id, model_id, base_url, output_format, voice_settings, stitch,
    api_key_env, env_file, timeout. `stitch` sends the neighbouring lines as previous_text / next_text so intonation
    carries across lines; set it to false for a model that rejects those fields."""
    name = "elevenlabs"
    supports_speed = True

    def _sample_rate(self):
        fmt = self.cfg.get("output_format", "pcm_24000")
        if not fmt.startswith("pcm_"):
            raise TTSError("output_format must be a pcm_* format (raw 16-bit samples)")
        return int(fmt.split("_")[1])

    def _request(self, text, speed, prev_text, next_text):
        base = self.cfg.get("base_url", "https://api.elevenlabs.io").rstrip("/")
        url = f"{base}/v1/text-to-speech/{self.cfg['voice_id']}?output_format={self.cfg.get('output_format', 'pcm_24000')}"
        vs = dict(self.cfg.get("voice_settings", {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0}))
        if speed:
            vs["speed"] = speed
        body = {"text": text, "model_id": self.cfg.get("model_id", "eleven_multilingual_v2"), "voice_settings": vs}
        if self.cfg.get("stitch", True):
            if prev_text:
                body["previous_text"] = prev_text
            if next_text:
                body["next_text"] = next_text
        return url, body

    def plan(self, text, direction="", speed=None, prev_text="", next_text=""):
        url, body = self._request(text, speed, prev_text, next_text)
        return {"provider": self.name, "url": url, "headers": ["xi-api-key", "Content-Type", "Accept"], "body": body}

    def synth(self, text, direction="", speed=None, prev_text="", next_text=""):
        key = read_secret(self.cfg.get("api_key_env", "ELEVENLABS_API_KEY"), self.cfg.get("env_file"))
        if not key:
            raise TTSError(f"{self.cfg.get('api_key_env', 'ELEVENLABS_API_KEY')} is not set")
        url, body = self._request(text, speed, prev_text, next_text)
        data = _post(url, {"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/pcm"}, body,
                     self.cfg.get("timeout", 120))
        return _pcm_bytes_to_float(data), self._sample_rate()


PROVIDERS = {"kokoro": KokoroProvider, "openai": OpenAIProvider, "elevenlabs": ElevenLabsProvider}


def make_provider(name, cfg):
    if name not in PROVIDERS:
        raise TTSError(f"unknown provider {name!r}; choose one of {', '.join(PROVIDERS)}")
    return PROVIDERS[name](cfg)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "--check":
        print(key_status(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
    else:
        print("usage: python tts_providers.py --check NAME [env file]   (prints whether a key is there, never its value)")
