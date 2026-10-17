---
type: reference
status: draft
created: 2026-10-17
---

# Trailer render: build plan

How the first full render of the trailer is made, and what each part needs. Read [[TRAILER-BRIEF]], [[STORYBOARD]] and the animatic ([[PACING]]) first. Decided by Diede on 2026-10-17: the app screens are **captures of the real app used as animated layers**; everything else is built as HTML; ffmpeg and Playwright are installed (approved).

## The pipeline

```
animatic/assets-eleven (narration cache, music, effects)  ->  mix.wav (done: animatic/tools/mix_eleven.py)
captures/ (real app, light, 2x)  +  scenes.html (render(T): a pure function of time)  ->  Playwright frames (24 fps)
frames + mix.wav + captions  ->  ffmpeg  ->  out/trailer-v1.mp4
```

- **Scenes** are one HTML file: no framework, no CSS transitions, no timers. Every scene is a function of the time `T` in seconds on the film's timeline, so any frame can be rebuilt exactly. The timeline is the storyboard's (22 scenes, 4:46); the narration start times come from `animatic/tools/placed.json`; scenes key their animation to those times.
- **Frame capture:** Playwright through the installed Google Chrome (`channel: "chrome"`), 1920×1080 JPEG at 24 fps, several workers in parallel (12 cores).
- **Layers from the real app:** every manager screen is a PNG in `render/captures/`, taken from the running app on the `trailer_capture` database at a recorded commit, in light theme, at 1440×810 CSS px with a device scale of 2. A scene positions, scales and moves the layer (camera push-ins, a cursor, highlight rings); it never redraws the app. Some screens scroll: those are captured **tall** (a viewport up to 1440×2400) so a scene can scroll the layer.
- **Built as HTML:** the title and end cards, the three diagrams (S02, S03, S03b), the developer scenes (S12 to S16b: editor, terminal, ADR reader, repository tree, in the dark-warm values), the three-line card (S19), and the drawn AI results of S08.
- **Music and voice:** `mix_eleven.py` already writes the mix. A re-read line or a re-generated music segment changes the mix and `placed.json`; the scenes follow, so a changed pause means re-rendering, not re-drawing.
- **Captions** are burned in from `captions.srt` (62 cues), at least 4 percent of the frame high.

## Who does what

1. **Capture pass** (a session of its own): the real-app screens listed in [[CAPTURE-LIST]], with `CAPTURE-LOG.md` recording the commit, the date, the database and the ports. Needs writes on the `trailer_capture` database (publishing prompts, seeding Approvals, making the email-plus-push campaign), and throwaway file drops in a worktree for S13 to S16.
2. **Scenes and harness** (this session): `scenes.html`, the render script, the muxing, the built scenes, then the integration of the captures.
3. **Review** by Diede, then the details (sentences, pauses, phrasing) by re-reading lines and re-rendering.

## Rules that carry over

- The frames follow the app at the recorded commit, never the audit captures of 16:54 ([[TRAILER-BRIEF]], section 8).
- Light theme only for the manager world (`data-theme="light"` on the page and `colorScheme: "light"` in the browser context); the developer world is the dark-warm look.
- Nothing from the claim ledger is broken: no exclusion, opt-out or unsubscribe on screen; no vendor names (crop the AI prompts' Model select, the Integrations rows of the development database); no phone receiving a push; the film says "in the same repository", never "public".
- Never read `backend/.env`. The capture session signs in with a login code from the scratch api's log and does not print any email address.
- The render outputs, captures and node modules are gitignored.

## How it is built now (2026-10-17, first full render)

- `./build.sh [name]` runs `build-data.py`, `render.mjs` (6864 frames in about a minute, 8 workers) and the ffmpeg mux. The captions are drawn by the scenes themselves from the cues of `captions.srt`, so the mux adds no subtitle step.
- `data/placed.json` is the file the last mix wrote (`mix_eleven.py`); the older `animatic/tools/placed.json` belongs to the draft and has other narration lengths. `build-data.py` prefers `data/placed.json`.
- **Ticks follow the screen.** Every cursor press and every cut to a new screen registers its time (`EVENTS` in `lib.js`); `node ticks.mjs` writes `data/ticks.json`, and `TICKS_JSON=data/ticks.json python3 ../animatic/tools/mix_eleven.py <narration wav44> <music segments> <sfx> <out>` places one tick at each. Nothing before 14 s gets a tick: the hook has drone and hits only.
- The captures are real, taken at commit `b230571` (see `captures/CAPTURE-LOG.md`, local). Lines the film must not show are cropped in the scenes: the `list_unsubscribe` row of "As sent", the step 2 note of the Send screen, the Unsubscribes column and footnote of Results, the `localhost` image address of the push preview, the Model select of AI prompts, "best match" in the slot settings, and the history's "123 delivered" line. The stranded send of S10 is drawn in HTML (the demo cannot produce one); the AI results of S08 are the capture session's drawings.
- Re-check before any new render: `git log b230571..main -- frontend/src frontend/index.html storage/modules` (empty on 2026-10-17).
