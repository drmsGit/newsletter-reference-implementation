# Animatic tools

Three scripts that build the animatic from the storyboard. Python 3 only; macOS `say` and `afconvert` (nothing is installed).

1. `python3 narrate.py <out>/nar Daniel 150` reads script A from `VOICEOVER.md`, one file per scene, and prints how long each line takes against its scene. The voice cannot read slower than rate 150; sentence pauses are added with `[[slnc N]]`.
2. `python3 score.py <out>/nar <out>/out` arranges the full-length score on the scene timeline (it imports `../../audio/synth.py`), ducks it under the voice, and writes `mix.wav`, `music.wav`, `narration.wav` and `placed.json`. Convert them with `afconvert -f m4af -d aac -b 160000`.
3. `python3 build_player.py <out>/out` writes `animatic.html`, `captions.srt` and `PACING.md` here and copies the three audio files next to them.

The scripts carry absolute paths of the author's machine and are a starting point, not a tool. Scene timings are the `DUR` table in `score.py`; keep it equal to the storyboard's.
