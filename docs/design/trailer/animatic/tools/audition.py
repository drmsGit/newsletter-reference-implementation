"""Render the same three narration lines in several Kokoro voices, so the narrator can be chosen by ear."""
import re
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
from kokoro_onnx.config import EspeakConfig

models = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

ESPEAK = EspeakConfig(lib_path="/opt/homebrew/lib/libespeak-ng.dylib", data_path="/opt/homebrew/share/espeak-ng-data")
k = Kokoro(str(models / "kokoro-v1.0.onnx"), str(models / "voices-v1.0.bin"), espeak_config=ESPEAK)
print("voices:", " ".join(sorted(k.get_voices())))

LINES = [
    "But AI has changed what a company, or its agency, can build for itself. So what if it kept the core, its content, its campaigns, its rules, its consent, and everything around it were a part you could replace?",
    "A CRM, a shop, a warehouse, an analytics tool: other systems reach the core through the API, each with its own key and its own permissions.",
    "Behind the screens, a developer keeps it growing, by hand or with an AI assistant. Not by asking a vendor. By adding a file.",
]
SPELL = [(r"\bAI\b", "A I"), (r"\bAPI\b", "A P I"), (r"\bCRM\b", "C R M")]


def spoken(t):
    for pat, rep in SPELL:
        t = re.sub(pat, rep, t)
    return t


VOICES = [("bm_george", "en-gb"), ("bm_lewis", "en-gb"), ("bf_emma", "en-gb"), ("af_heart", "en-us"), ("am_michael", "en-us")]
SPEED = 0.95
for voice, lang in VOICES:
    t0 = time.time()
    parts = []
    for line in LINES:
        audio, sr = k.create(spoken(line), voice=voice, speed=SPEED, lang=lang)
        parts.append(audio.astype(np.float32))
        parts.append(np.zeros(int(sr * 1.2), dtype=np.float32))
    y = np.concatenate(parts)
    y = y / max(1e-6, float(np.abs(y).max())) * 0.85
    sf.write(str(out / f"{voice}.wav"), y, sr)
    print(voice, "ok", round(len(y) / sr, 1), "s audio in", round(time.time() - t0, 1), "s")
