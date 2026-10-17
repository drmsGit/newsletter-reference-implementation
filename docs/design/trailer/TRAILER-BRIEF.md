---
type: reference
status: draft
created: 2026-10-17
---

# Trailer brief: the Omnichannel Orchestration Reference

The creative brief for a 3 to 5 minute product trailer. It is read together with [[STORYBOARD]] (every scene), [[VOICEOVER]] (both narration scripts) and `storyboard.html` (the same scenes as a visual board).

**Status, 2026-10-17.** Nothing is built. This brief was made from the architecture decision records, the business documents, the design handoff and the live captures of the demo, and from an interview with Diede on the same day. The decisions in section 2 are Diede's. The scene content, the narration and the claim ledger are Claude's draft and have not been reviewed scene by scene. The point of the brief is that the later build needs little feedback: everything the build needs to know is here or in the storyboard, and what must be checked first is in section 15.

## 1. The film in one sentence

Two people, a marketing manager and a developer, run one communication system, and the film shows that they can see exactly what it does, change it by adding a file, and keep its core in the company's hands.

## 2. What was decided

| Question | Decision |
|---|---|
| Where it plays | Both: the November 2026 talks with two agencies and one prospective client ([[PRESENTATIONS-2026-11]]), and later online. It must stand alone, so it works watched without Diede in the room and without sound. |
| Story spine | **Two people, one system.** The manager (the linen manager app) is cross-cut with the developer (editor and terminal). They meet at one send and the signal coming back. |
| Voice | **Voice-over led.** The primary script is a neutral narrator in the third person. A second script tells the same beats in the first person, for Diede to record later ([[VOICEOVER]]). |
| Tone | Quiet confidence as the base. Trailer-style hits, a hook and a strong first 15 seconds are allowed, so it stays catchy when nobody explains it. |
| Production | **Everything rebuilt as animated frames** from the real tokens and the real layout. No screen recordings. It can be re-rendered when the name or the design changes. |
| Developer chapter | Four file drops: a content block, a decision strategy, an AI task, a swapped email provider. The line "two files" is not used (sections 12 and 13). |
| Hero functions | One slot, three readers, three picks. Exactly what each person got. AI proposes, a person decides. Push is a beat in the montage, not a hero. |
| Content language | German demo content as it is (the fictional brand Grathaus Outdoor), English interface and narration, key lines captioned in English. |
| Claims | Built things only. No brand or competitor names. No "designed next" beat. |
| Ending | "The playbook. The working code. A conversation." with the address left open. No "open source" and no "free". |

## 3. Audience and what they should do

**Primary:** agencies and independent specialists who serve mid-sized companies, the audience the positioning names ([[POSITIONING]], rule 1). **Also:** one prospective client's team, and developers who find it online later.

They should leave thinking: *I could build this for a client, and the client would own it.* They should do one thing: ask for a conversation. The film is not a feature tour and does not try to look like a finished commercial product. The reference is meant to be read, taught from and tailored, and the film says so by showing the seams, not by saying "easy".

Not the audience: a shop owner who wants good-looking newsletters fast. The film does not compete on production speed.

## 4. The message

One idea, three supports. Each support answers a client complaint that the playbook names (`docs/playbook-strategy.md` §3).

| Support | The complaint it answers | What the film shows |
|---|---|---|
| **See what it does.** | "I can't see what the system is doing, or why." | Per-reader picks that can be explained. Exactly what each reader received. Who was left out and why. |
| **Change it with a file.** | "Anything complex needs developers." | A content block, a strategy, an AI task and a provider added as files. The manager app changes in answer. |
| **Keep the core.** | "Standards don't fit my workflow." | The company's content, campaigns, rules and consent in the middle. Delivery, AI and channels as parts that can be replaced. |

The title line, "Building a communication system you control.", is the idea in one sentence. The author is Diede Slembrouck.

## 5. The spine: two people, one system

- **The manager** works in the manager app: linen ground, three columns, calm and dense. Shown by an initials avatar only (the demo's own rule: the colour comes from the name). Working name "Anke Voss", AV. No faces anywhere in the film.
- **The developer** works in an editor and a terminal, drawn in the project's own dark values, so the two worlds look different but come from one design system.
- **They meet** in Act 3, where each file the developer drops is answered by a change in the manager's screen, and in Act 4, where the two are on one screen with one campaign.

## 6. Tone

Quiet confidence: slow, precise camera moves over the real interface, warm linen and petrol, an ambient pulse and a piano, restraint, and one big rise at the first file drop. Then the parts of a movie trailer that make it catchy: a cold open with a question, hits on the key numbers, hard cuts on the beat, and a held silence before the end card. It must never overclaim; drama comes from rhythm and from the screens, not from adjectives.

## 7. Structure and timing

Master cut, about 4:10. Scene by scene in [[STORYBOARD]].

| Act | Time | Job |
|---|---|---|
| 0 Hook | 0:00 to 0:14 | A question made of three numbers: "Could you say why each choice was made?" |
| 1 The idea | 0:14 to 0:58 | The two ends of the market, the owned core, the title |
| 2 The manager | 0:58 to 2:20 | Content, campaign, one slot three readers, AI and approval, send, as sent, the signal back |
| 3 The developer | 2:20 to 3:20 | Four file drops, each answered by the manager app |
| 4 One system | 3:20 to 3:52 | Email and push from one campaign, a montage of everything else, the three-line pillar card |
| 5 End card | 3:52 to 4:10 | Title, tagline, author, call to action, small print |

About 380 spoken words, roughly 2:45 of speech, so more than a third of the film is picture and music only.

**Teaser cut, 60 to 75 seconds:** the scenes marked T in [[STORYBOARD]] (S01 to S04, S07, S13, S16, S20), each trimmed to its strongest beat. Same frames, same narration lines, no new material.

## 8. Production: everything rebuilt as animated frames

**What "real design and layout" means.** Every product frame is rebuilt as a code-drawn page from the real tokens (`docs/design/tokens.css`) and the real layout of the React manager app (`frontend/src/screens/`, `frontend/src/index.css`), then animated. It is a re-drawing, not a capture, so it has to be faithful: same columns, same labels, same data. Where a drawn render and the live app disagree, the live app wins ([[HANDOFF]], section 10: "the code wins").

**Canvas.** Build each frame at 1440×810 logical px, the width of the design renders. Render at 3840×2160. Render on macOS so the system font is SF Pro, as in the app.

**Source material.** Two sets, used for different things.

| Set | Where | Use it for | Do not use it for |
|---|---|---|---|
| **Live captures** | `docs/design/ux-audit-2026-10-17/screenshots/` (brand Grathaus Outdoor, real demo data, German emails with images; 1456×755; untracked in git) | Layout, labels, data and real rendered emails | Anything affected by the known flaws below |
| **Design renders** | `docs/design/renders/` (brand Nordlicht Kaffee, invented data; light theme except 02, 04, 05, 14, 16) | The intended layout where the live app has an open defect, the editor's cue chips, the send steps, the stranded send | Data, names and figures: they are invented |

**Known flaws of the demo that a frame must not inherit.**

- The unsubscribe link in "As sent" points at `http://localhost:8000/`. Redraw it with the neutral demo address.
- "As sent" shows two notices about changed templates in the captured data. Re-capture after a fresh reset, or redraw without them.
- The demo AI is a mock that returns placeholder text. Write believable suggestions, but keep the app's own provenance line ("Example provider", the prompt version) on screen so the film does not pretend to a real model.
- Approvals is empty after a reset. It needs seeding before it can be shown.
- Sent campaigns still carry the status "draft" in the list. Redraw the status as Sent.
- Not built in the live app and not to be drawn as if they were: drag handles in the preview sheet, the P-key hint chip on "Open preview", search boxes on lists without server search.
- The category Graph is the weak screen (overlapping labels, all-green circles). It is not in the film.
- Phone and tablet layouts, and dark mode for screens 20 to 45, are not designed. The film is desktop only. The developer world's dark look is the editor and terminal, not the app in dark mode.

## 9. Look and motion

**Manager world** (`tokens.css`, [[DESIGN]], [[CONSTRAINTS]])

- Ground Linen `#fcf8f2`; cards and the list column white; navigation `#f3ecdf`; text `#1f1b16`; hairline `#e4daca`.
- **Petrol `#1a5d74` is the one action colour:** the primary button, links, navigation icons and the focus ring.
- **Pale Pink `#f4bebb` is only the navigation's "you are here".** It is never a status and never a surface, because it sits at the same hue as the failed red.
- Statuses: waiting `#7a4a00` on `#fff0d6`, approved `#1d6b34` on `#e1f4e6`, running `#0a5eb0` on `#e3effb`, failed `#fde8e6`, expired and withdrawn neutral. A glyph and a word on every status: colour is never the only signal.
- Three full-height columns: navigation 232 px (an icon rail of 56 px when collapsed), list 380 px, details flexible. One text indent per column. Groups are white cards with hairlines; the action group is docked at the foot with a soft fade, no rule.
- Type: the system font (SF Pro) and the system monospace for ids and counts. Large title 26/32 bold, title 22/28, group title 15/20, body 13/18, caption 12/16. Controls 24, 28 or 36 px high. Radii 6 for controls, 10 for cards, a capsule for chips. Icons: Lucide, 16 px, stroke 1.75.

**Developer world.** The project's own dark values: ground `#14110f`, card `#1e1b18`, sidebar `#191614`, accent `#6fc3dd`, text `#f4eee6`, system monospace. It must read as the same family as the linen world.

**Never.** Gradients, illustration, emoji, glass, blur or translucency on a UI plane, colour as the only signal, Pale Pink as a status. The hierarchy of the app does not change for the film. There is no logo: the earlier identity is retired and the shell shows the name as text.

**Camera and motion.** The product itself has no motion except a spinner. The film adds motion outside the UI: slow push-ins, two-dimensional parallax between layers, hard cuts on the beat, one hold per hero scene. Depth of field and vignettes only on the empty ground around a UI plane, never on the UI. No flashing faster than three times a second anywhere, hook included.

## 10. Voice, sound and captions

**Voice.** Two scripts in [[VOICEOVER]], same beats and timings.

- **A, neutral narrator, third person.** The master. A calm, unhurried read, no trailer growl. A synthetic read is acceptable for the first cut.
- **B, first person, Diede.** For a later recording. It ends on "I'm Diede Slembrouck. Come and see how it works." It changes "the manager" and "you" into "I" and "me" and nothing else.

**Music.** Licence-clean instrumental only: composed for the film or a library track whose licence allows the use. No track from a commercial catalogue. The arc: a sparse drone and a one-second pulse in the hook; rising strings under the problem; a warm piano pulse for the manager; a tick per click and one low hit per file drop for the developer; a full swell into the pillar card; then silence before the end card; one piano note under it.

**Sound design.** Soft interface ticks, a muted hit for each file landing, a restrained whoosh only on the hard cut into the developer world. The narration ducks the music.

**Captions.** Burned-in captions of the narration, always on, because the film is built to be watched without sound. A separate SRT file as well. German email text gets a small English caption wherever a line matters (S07 above all). Caption height at least 4 percent of the frame.

## 11. Claim ledger

The positioning rule is that a claim must be demonstrable in the repository ([[POSITIONING]], rule 2): an accepted ADR shows a design, not a capability. Each line below rests on the sweeps of 2026-10-17, which read the code behind the decision records. "Not run" means read from the code and not yet performed on a scratch copy; section 15 lists what has to be run first.

### Safe to show or say

| Claim | Evidence | Caution |
|---|---|---|
| Content is written once and referenced, never copied | [[ADR-012 — Content Records Represent Communication Units]], [[ADR-030 — Separate Global and Repeatable Structures]] | Within one brand. Across brands content is copied. |
| An edit in a campaign changes that campaign; changing the shared library is a deliberate click | [[ADR-040 — Introduce Override Layer]], [[ADR-041 — Override Precedence]], [[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]] | |
| A decision slot picks per reader, from approved content, and the pick is explainable | [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]], [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]], [[ADR-085 — Decision Resolution Should Be Optionally Explainable]], [[ADR-127 — Decision Execution May Use Recipient Context]] | Built: up to five picks per slot, ranked, the empty-send floor. Not built: minimum items and fallback content. |
| AI suggests, a person decides | [[ADR-081 — AI Ranks Within Governed Candidate Sets]], [[ADR-082 — AI May Recommend but Not Publish]], [[ADR-140 — AI Capability Layer]], [[ADR-141 — In-App Assistive AI Actions]] | The demo AI is the mock; the one real adapter is a US vendor's. Never "EU-hosted" or "GDPR-friendly AI". |
| When a machine asks to send, a person approves | [[ADR-142 — Autonomous Workflows and the Automation Boundary]] (the approval boundary only), [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]], [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] | Only the approvals inbox is built. Autonomous workflows are not. |
| A send is planned first and records who was left out and why | [[ADR-163 — Per-Channel Consent and Addressability]], [[ADR-086 — Decision Slots Fail Gracefully]], [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] | Never "GDPR compliant": the adopter takes the liability, the platform supplies mechanisms. |
| Open a reader's message and see the content they received | [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]], [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] | Say "content". The app itself notes that the layout is today's. [[ADR-062 — Snapshot Stores Final Render State]] is superseded by ADR-183: never say the snapshot stores the final HTML. |
| A stranded send is flagged and a person releases it | [[ADR-192 — A Stranded Send Is Flagged, and a Person Releases It]] | |
| Clicks come back as signals that fade with time and shape the next pick | [[ADR-110 — Insight Layer Transforms Events Into Signals]], [[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]], [[ADR-112 — Signals Use Time-Based Decay]], [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] | Clicks only. Opens are not counted and are never shown as a rate. |
| A dropped file is picked up: a content block, a decision strategy, an AI task | The registries for modules, strategies and AI tasks rescan on change; [[ADR-131 — Email Module Templates Use MJML as Source Format]], [[ADR-198 — The Email Block Set Is Seven Blocks, Square Images and Text Links]] | Each has its own file count. Not run. |
| The delivery provider can be swapped with a file and a few lines | [[ADR-100 — Provider Layer as Send and Feedback Adapter]], [[ADR-101 — Provider Capabilities Are Explicit]], [[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]] | Register it in the factory by hand; the server reloads. Not run. |
| Email and push are channels of one campaign | [[ADR-160 — Channel Model and Composition]], [[ADR-161 — Channel Execution Shapes]], [[ADR-162 — Channel Rendering and Artifacts]], [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] | Push is delivered only by the mock provider. |
| One company, several brands; roles and keys; an audit record | [[ADR-150 — Tenancy and Access Model]], [[ADR-153 — Audit and Accountability]], [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] | One install is one company. |
| Nothing commercial is required to run it | [[ADR-171 — Nothing Required to Run This Platform Is Commercial]] | The mock providers are the default. |

### Never show or say

- **"Two files."** There is no universal two-file path (sections 12 and 13).
- **"A weekend, not half a year."** It is a developer claim that must be demonstrable in the repository; it has not been demonstrated.
- **"Open source", "free", a licence.** None has been chosen.
- **GDPR compliance, erasure, deletion, retention.** [[ADR-154 — Erasure and Retention]] is designed and not built; nothing in the platform is erased.
- **EU-hosted AI.** Not built.
- **Autonomous workflows, n8n flows, a flow canvas.** Not built; only the approvals inbox is.
- **Paid social, letter, SMS.** Not built.
- **A phone receiving a push.** Push goes only through the mock provider; there is no device delivery.
- **Open rates.** Opens are not counted.
- **"Byte for byte", "exactly what was sent" for the layout.** The content is exact; the layout is today's.
- **"Real email" on the mock provider.** The button reads "Send to N".
- **Hosted, SaaS, "try it".** It is a local proof of concept.
- **A competitor's or a vendor's name or logo.** The market is described without names.
- **The category Graph.**

## 12. The four drops, as the code allows them

These are the exact seams for Act 3. They were read from the code and not run.

| Drop | Where | What is really needed | What the manager then sees |
|---|---|---|---|
| **A content block** | `storage/modules/email/<name>.json` and `<name>.html`; the `.mjml` source is optional and compiled by `npm run build:modules` in `frontend/` | A manifest that names fields already defined in `storage/fields.json` (a field that is not defined gets the block skipped), and the template. CI checks that the committed `.html` matches the `.mjml`. | The block in "Add a module" for that channel. No migration. |
| **A decision strategy** | `backend/app/decision/strategies/<name>.py`, shaped like `top_score.py` (a class with `meta` and `rank`) | One file; found by a package scan. | The strategy in the slot settings. |
| **An AI task** | `backend/app/ai/tasks/<name>.py` with a `META` object and a default prompt | One file. The developer fixes what it reads and what it returns; the prompt text lives in the database and belongs to the manager ([[ADR-140 — AI Capability Layer]] §4). | A new record under Settings, AI prompts. Running it needs a screen, so show the entry, not a run. |
| **A delivery provider** | `backend/app/delivery/providers/<name>.py` beside `resend.py`, plus the branch, the label and the tuple entry in `factory.py` | A file **and** a few edited lines in the factory; the provider must declare which channels it carries; under `uvicorn --reload` the server restarts on its own. | The provider in the send picker, beside `mock` and `resend`. |

**What is not simple:** adding a whole channel takes a manifest, a module manifest, a renderer, an address-key edit, a provider with a factory edit and consent rows, and the playbook's own addendum says so. The film shows a channel only as a thing that exists (push), never as a file you drop.

`docs/how-to-swap-send-provider.md` is stale (it describes an older contract and says "an hour's work"); do not quote it.

## 13. What the sweeps changed in the story

Kept here because each one would otherwise come back as a "mistake" in review.

- **"Dropping two files" could not be kept.** Six kinds of extension are found by dropping in a file, but the count differs per seam, and providers also need a factory edit. The film's line is "Change it with a file", and every drop shows the real number of files.
- **The live demo is Grathaus Outdoor, in German.** The design renders use an invented brand, Nordlicht Kaffee. The film uses the live demo's content and numbers; renders are for layout only.
- **Push has no real provider.** It is shown as a channel and a preview, never as a delivery to a phone.
- **The demo's AI is a mock.** The film keeps the app's own provenance line.
- **The "As sent" screen carries honest warnings** (the layout is today's). The film says "the content they received".
- **Competitor names are out.** The presentation draft names two vendors as reference points; the film does not, because the draft itself says it is not a current feature or price audit.

## 14. Deliverables of the film

1. Master, 16:9, 3840×2160, 24 fps, narration A, burned-in captions, plus a captions-off version.
2. Narration B version (when recorded).
3. Teaser, 60 to 75 seconds.
4. SRT captions and a plain transcript.
5. One poster frame: the S07 triptych or the S01 numbers.
6. The frame project itself (the code that draws the frames), reading the name from `product.json`, so a rename or a design change is a re-render, not a rework.

## 15. Pre-production checks

All on a scratch database and a throwaway branch, never on the real development data. Nothing below has been done.

1. Reset the demo on scratch and re-read every number the film uses: the hook's 123, 369 and 15 (from the Familienherbst slot), the results, the counts excluded for consent and suppression.
2. Find three readers who really get different picks from one slot, and note their names (they are fictional addresses on the demo domain).
3. Seed Approvals, and trace what produces "Apply an AI-suggested subject". If the path is not plain, S08 uses "Send a campaign" requested by an integration instead.
4. Perform each of the four drops for real: write the files, build, reload, and keep the exact file contents, the console lines and the time it takes. Confirm what the editor shows without a restart or a refresh, and show exactly that.
5. Re-capture "As sent" so the stale-template notices are gone, and fix or redraw the flaws in section 8.
6. Decide the name handling: the end card reads `product.json`. The name is a neutral working title until a brand is chosen; no brand is cleared.

## 16. Open decisions (the default is assumed unless you say otherwise)

1. **Cuts.** A master of about 4:10 and a teaser of 60 to 75 seconds.
2. **The developer world in the dark-warm look.**
3. **Initials avatars only, no faces,** for the manager and for any developer mark.
4. **Music:** composed or a licence-clean library track; the source is to be chosen.
5. **A first-person ending only** (script B) if a full recording is not made: the last line, in Diede's voice, over narrator A.
6. **The address on the end card** stays open until a website or repository exists.
7. **The hook's numbers.** They are the live demo's and may change at the next reset; the hook is rewritten from whatever the reset gives.

## 17. Sources

- `docs/business/PRESENTATIONS-2026-11.md`, `docs/business/POSITIONING.md`, `docs/business/BRIEF.md`, `README.md`, `docs/playbook-strategy.md` (§1 to §5).
- `docs/design/HANDOFF.md`, `docs/design/DESIGN.md`, `docs/design/CONSTRAINTS.md`, `docs/design/tokens.css`, `docs/design/renders/README.md`.
- `docs/design/ux-audit-2026-10-17/` (live captures and findings).
- The decision records named in section 11.
- Code read for the file seams: `backend/app/modules/registry.py`, `backend/app/decision/strategies/`, `backend/app/ai/tasks/`, `backend/app/delivery/providers/factory.py`, `backend/app/channels/registry.py`, `storage/`.
- The demo seed: `backend/app/demo/` and `backend/scripts/demo_reset.py`.
