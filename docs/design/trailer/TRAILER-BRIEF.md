---
type: reference
status: draft
created: 2026-10-17
---

# Trailer brief: the Omnichannel Orchestration Reference

The creative brief for a 3 to 5 minute product trailer. It is read together with [[STORYBOARD]] (every scene), [[VOICEOVER]] (both narration scripts) and `storyboard.html` (the same scenes as a visual board).

**Status, 2026-10-17.** Nothing is built. This brief was made from the architecture decision records, the business documents, the design handoff and the live captures of the demo, and from an interview with Diede on the same day. The decisions in section 2 are Diede's. The scene content, the narration and the claim ledger were Claude's draft; Diede reviewed the storyboard scene by scene on 2026-10-17 and the result is in the second update below. The point of the brief is that the later build needs little feedback: everything the build needs to know is here or in the storyboard, and what had to be checked first is in section 15.

**Update, 2026-10-17, later the same day.** The checks of section 15 were run on scratch data ([[PREPRODUCTION-CHECKS]]) and this brief was corrected from what they found: scenes S01 and S07 to S16 in [[STORYBOARD]], the narration of S07, S09 and S10, the known flaws in section 8, the claim ledger in section 11 and the four drops in section 12. Three of the corrections are Claude's choices, not Diede's, and can be reversed: they are listed at the end of section 16. A fourth change, that the film says nothing about unsubscribing, is Diede's decision (section 16, decision 8).

**First animatic, 2026-10-17.** `animatic/` holds a playable animatic (open `animatic.html` in Chrome): the reference stills in storyboard order, a synthetic read of script A (macOS voice Daniel), a full-length mood score and captions, with a pacing report in `animatic/PACING.md`. It tests the pacing; it is not the trailer.

**Second update, 2026-10-17, after Diede's review of the storyboard.** Every scene was marked okay except where noted. Changes: S02 stays and the AI premise goes into S03 and S12 (a placement Claude chose, with reasons in S03); S03 also shows other systems reaching the core, as a new scene S03b; S08 shows creating a content record and a variant, then Approvals; S16 is about any sending service, not email only; a new scene S16b says that the reasons live in the same repository as the code; S20 gains "Always adapting to your business."; the music is decided as two moods with no strings and no piano; the narrator is a synthetic read first. The film is now 22 scenes and about 4:46. Section 16 lists what is decided and what is still open.

## 1. The film in one sentence

Two people, a marketing manager and a developer, run one communication system, and the film shows that they can see exactly what it does, change it by adding a file, and keep its core in the company's hands.

## 2. What was decided

| Question | Decision |
|---|---|
| Where it plays | Both: the November 2026 talks with two agencies and one prospective client ([[PRESENTATIONS-2026-11]]), and later online. It must stand alone, so it works watched without Diede in the room and without sound. |
| Story spine | **Two people, one system.** The manager (the linen manager app) is cross-cut with the developer (editor and terminal). They meet at one send and the signal coming back. |
| Voice | **Voice-over led.** The primary script is a neutral narrator in the third person, **read first by a synthetic voice**. A second script tells the same beats in the first person, for Diede to record later ([[VOICEOVER]]). |
| Tone | Quiet confidence as the base. Trailer-style hits, a hook and a strong first 15 seconds are allowed, so it stays catchy when nobody explains it. |
| Production | **Everything rebuilt as animated frames** from the real tokens and the real layout. No screen recordings. It can be re-rendered when the name or the design changes. |
| Developer chapter | Four file drops: a content block, a decision strategy, an AI task, a swapped send provider (email or push). The line "two files" is not used (sections 12 and 13). A short beat shows that the decisions behind the code live in the same repository (S16b). |
| Hero functions | One slot, three readers, three picks. Exactly what each person got. AI proposes, a person decides (a content record and a variant, then Approvals). Push is a beat in the montage, not a hero. |
| Content language | German demo content as it is (the fictional brand Grathaus Outdoor), English interface and narration, key lines captioned in English. Names and content on screen are the demo's own; none is invented for the film. |
| Claims | Built things only. No brand or competitor names. No "designed next" beat. |
| Ending | "The playbook. The working code. A conversation." with Diede's LinkedIn address on screen for now, and the line "Always adapting to your business." under the tagline. No "open source" and no "free". |
| Music | Two moods, no strings and no piano: **A, a quiet machine** for the manager's world, **B, a driven pulse** for the developer's. The two samples in `audio/` set the direction; the final score is composed or licensed. |
| Cuts | A master of about 4:46 and a teaser of 60 to 75 seconds. |
| Developer look | Dark-warm. |
| Persona | Initials avatars only; the avatar is the demo's own. |
| Name | Parameterised: the end card reads `product.json` at render time. |

## 3. Audience and what they should do

**Primary:** agencies and independent specialists who serve mid-sized companies, the audience the positioning names ([[POSITIONING]], rule 1). **Also:** one prospective client's team, and developers who find it online later.

They should leave thinking: *I could build this for a client, and the client would own it.* They should do one thing: ask for a conversation. The film is not a feature tour and does not try to look like a finished commercial product. The reference is meant to be read, taught from and tailored, and the film says so by showing the seams, not by saying "easy".

Not the audience: a shop owner who wants good-looking newsletters fast. The film does not compete on production speed.

## 4. The message

One idea, three supports. Each support answers a client complaint that the playbook names (`docs/playbook-strategy.md` §3).

| Support | The complaint it answers | What the film shows |
|---|---|---|
| **See what it does.** | "I can't see what the system is doing, or why." | Per-reader picks that can be explained. Exactly what each reader received, and the reason each piece was picked. The decisions behind the code, in the same repository. |
| **Change it with a file.** | "Anything complex needs developers." | A content block, a strategy, an AI task and a provider added as files. The manager app changes in answer. |
| **Keep the core.** | "Standards don't fit my workflow." | The company's content, campaigns, rules and consent in the middle. Delivery, AI and channels as parts that can be replaced. Other systems (a CRM, a shop, a warehouse, analytics) reaching the core through the API with their own keys. |

The title line, "Building a communication system you control.", is the idea in one sentence. The author is Diede Slembrouck.

## 5. The spine: two people, one system

- **The manager** works in the manager app: linen ground, three columns, calm and dense. Shown by an initials avatar only (the demo's own rule: the colour comes from the name), the one the demo shows for its signed-in user ("IA" in the live captures). No invented persona name and no faces anywhere in the film: the names on screen are the demo's.
- **The developer** works in an editor and a terminal, drawn in the project's own dark values, so the two worlds look different but come from one design system.
- **They meet** in Act 3, where each file the developer drops is answered by a change in the manager's screen, and in Act 4, where the two are on one screen with one campaign.

## 6. Tone

Quiet confidence: slow, precise camera moves over the real interface, warm linen and petrol, an ambient pulse, soft mallet tones and a low drone, restraint, and one big rise at the first file drop. Then the parts of a movie trailer that make it catchy: a cold open with a question, hits on the key numbers, hard cuts on the beat, and a held silence before the end card. It must never overclaim; drama comes from rhythm and from the screens, not from adjectives.

## 7. Structure and timing

Master cut, about 4:46. Scene by scene in [[STORYBOARD]].

| Act | Time | Job |
|---|---|---|
| 0 Hook | 0:00 to 0:14 | A question made of three numbers: "Could you say why each choice was made?" |
| 1 The idea | 0:14 to 1:14 | The two ends of the market, the owned core (with the AI premise), other systems reaching it through the API, the title |
| 2 The manager | 1:14 to 2:44 | Content, campaign, one slot three readers, AI proposals and a person's decision, send, as sent, the signal back |
| 3 The developer | 2:44 to 4:00 | Four file drops, each answered by the manager app, and the reasons that stay with the code |
| 4 One system | 4:00 to 4:28 | Email and push from one campaign, a montage of everything else, the three-line pillar card |
| 5 End card | 4:28 to 4:46 | Title, tagline, author, call to action, small print |

About 460 spoken words in script A (about 490 in B), roughly 3:25 of speech: about 70 percent of the film is narrated. If the animatic feels crowded, S03b and S16b are the first to compress or cut.

**Teaser cut, 60 to 75 seconds:** the scenes marked T in [[STORYBOARD]] (S01 to S04, S07, S13, S16, S20; S03b and S16b stay out), each trimmed to its strongest beat. Same frames, same narration lines, no new material.

## 8. Production: everything rebuilt as animated frames

**What "real design and layout" means.** Every product frame is rebuilt as a code-drawn page from the real tokens (`docs/design/tokens.css`) and the real layout of the React manager app (`frontend/src/screens/`, `frontend/src/index.css`), then animated. It is a re-drawing, not a capture, so it has to be faithful: same columns, same labels, same data. Where a drawn render and the live app disagree, the live app wins ([[HANDOFF]], section 10: "the code wins").

**Canvas.** Build each frame at 1440×810 logical px, the width of the design renders. Render at 3840×2160. Render on macOS so the system font is SF Pro, as in the app.

**Source material.** Two sets, used for different things.

| Set | Where | Use it for | Do not use it for |
|---|---|---|---|
| **Live captures** | `docs/design/ux-audit-2026-10-17/screenshots/` (brand Grathaus Outdoor, real demo data, German emails with images; 1456×755; taken at commit `01e6992`, 2026-10-17 16:54, so older than the app now) | Layout, labels, data and real rendered emails | Anything affected by the known flaws below |
| **Design renders** | `docs/design/renders/` (brand Nordlicht Kaffee, invented data; light theme except 02, 04, 05, 14, 16) | The intended layout where the live app has an open defect, the editor's cue chips, the send steps, the stranded send | Data, names and figures: they are invented |

**Which version of the app the frames draw** (from Diede's feedback, 2026-10-17 evening, after the board still showed the old create dialog with its title beside the field). The audit captures and the design renders are **references for layout, never the source**. The source is the running app at a **recorded commit**:

1. The frame project records the commit it draws from. Every frame is checked against the running app at that commit, in light theme, from the final reset, and screens are captured fresh for that purpose.
2. Right before rendering, run `git log <recorded commit>..main -- frontend/src frontend/index.html storage/modules`. Any change that touches a screen in the film means that screen is looked at again. The queue's UX audit task (task-392) is still open, so the app keeps moving.
3. **Stale references as of this writing:** `16-new-record.jpg` shows the "New content record" dialog with the title beside its field and "Create" before "Cancel"; the app now stacks each label above its field and ends with Cancel, then Create, like every dialog. In general every audit capture of a dialog, the image sheet, a fact row, a field row with a button, a long text field and the navigation foot predates the fixes of the evening. The visual board marks every audit image as a reference taken before those fixes.
4. Round 2 checked labels, states and behaviour on a scratch app at the commit of that day. It did not re-capture the audit images, so a frame is never built from an audit image alone.

**Known flaws of the demo that a frame must not inherit.**

Verified present or absent on a fresh scratch reset ([[PREPRODUCTION-CHECKS]], section 6).

- The unsubscribe link in "As sent" points at `http://localhost:8000/unsubscribe/<token>` (`PUBLIC_BASE_URL` is unset). Still present. Crop the row, or redraw it with a neutral demo address; the film never speaks of it (unsubscription is not built yet).
- "As sent" shows two notices about changed templates only when the template folder changed after the send. After a fresh reset they are gone; any change in `storage/modules/email/`, a drop included, brings them back. Capture "As sent" before the first drop. S10 comes before S13 in the film, so the story order is already right.
- The demo AI is a mock ("Mock subject 1 — Mock preheader 1", provenance `mock-1`), and on a fresh reset it does not run at all until a prompt is published in Settings. The caution line "Suggestions can be wrong. Check the subject before you use it." and the words "Example provider" exist only in the design canvases, not in the app. A frame that shows believable suggestions is a drawing and is marked as one in the shot notes.
- Approvals is empty after a reset. The seed script (`backend/scripts/seed_pending_actions.py`) makes only "Send a prepared campaign" requests, from the integration "Acme Agency (demo)", and needs a planned draft send first.
- Sent campaigns still carry the status "draft" in the list and on the campaign page. Redraw the status as Sent.
- **No reader is excluded for consent or suppression anywhere in the demo**, and the one reader who unsubscribed stays reachable, because the seed writes the unsubscribe before the opt-in. The film cannot draw an exclusion from the demo.
- The dated fields ("Last pick", "Updated" on drafts) show the reset's clock, while sent campaigns carry fixed dates. Choose the reset date on purpose and do not reset again after the captures.
- Readers whose language is English can be among the recipients of the German email (reader #4). None of the three readers of S07 is affected.
- The app shows 122 delivered where the reset script prints 123. Say "readers" or "recipients", never "delivered".
- **Round 2 findings a frame can inherit** ([[PREPRODUCTION-CHECKS-2]], section 6): the push send step says "Planning freezes the email as it is now" and has no step 2; `http://localhost:8000/media/…` appears as a push image address; the demo data names its own tooling ("Grathaus demo segment (task-71)", "(seed_pending_actions.py)"); the audience page shows opt-out and exclusion wording and a count; a freshly sent mock campaign shows "Delivered 0" while the approvals history says "123 delivered"; topic proposals are chosen among the newest 60 records; the slot built from a topic is labelled "From the topic" in English; a blank variant opens with the "You are editing this variant … Unblock" banner; a freshly reset database has no integration until the approvals seed creates one.
- **The email frames change:** the demo brands' profiles now give their emails a look (Grathaus Outdoor's wear the platform palette, Grathaus Touren's an alpine look), so every email frame is captured again from the final reset ([[HANDOFF-2026-10-17]]). Every frame with the navigation carries a "Keyboard shortcuts" button above Sign out.
- **Capture in light.** The app follows the system theme and renders dark on a dark machine; force `data-theme="light"` on the page after each load. The film's manager world is light only.
- Not built in the live app and not to be drawn as if they were: drag handles in the preview sheet, the P-key hint chip on "Open preview", search boxes on lists without server search (only Campaigns, Recipients and Audiences have one).
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

- **A, neutral narrator, third person.** The master. A calm, unhurried read, no trailer growl. **Decided 2026-10-17: a synthetic read first.**
- **B, first person, Diede.** For a later recording. It ends on "I'm Diede Slembrouck. … Come and see how it works." It changes "the manager" and "you" into "I" and "me" and nothing else.

**Music.** Licence-clean instrumental only: composed for the film or a library track whose licence allows the use. No track from a commercial catalogue. **Decided by Diede, 2026-10-17: no strings and no piano; they sound too romantic and over the top.** The sound is a low pulse, soft mallet or kalimba tones, muted plucks, small ticks and a low drone with open fifths. The arc: a sparse drone and a pulse in the hook; a low pad rising under the problem; a quiet mallet motif for the manager; a tick per click and one low hit per file drop for the developer; a full swell into the pillar card; then silence before the end card, with one soft mallet note under it. Two mood samples, synthesised from nothing so there is nothing to license, are in `audio/` (`mood-a-quiet-machine.m4a` for the manager's world, `mood-b-driven-pulse.m4a` for the developer's; `audio/synth.py` makes them again). **Decided 2026-10-17: both moods for the first round; if only one can be used, the developer mood, B.** They are a direction, not the score: the final music is composed or licensed along these two.

**Sound design.** Soft interface ticks, a muted hit for each file landing, a restrained whoosh only on the hard cut into the developer world. The narration ducks the music.

**Captions.** Burned-in captions of the narration, always on, because the film is built to be watched without sound. A separate SRT file as well. German email text gets a small English caption wherever a line matters (S07 above all). Caption height at least 4 percent of the frame.

## 11. Claim ledger

The positioning rule is that a claim must be demonstrable in the repository ([[POSITIONING]], rule 2): an accepted ADR shows a design, not a capability. Each line below rests on the sweeps of 2026-10-17, which read the code behind the decision records. The file drops and the demo numbers were run on a scratch copy on 2026-10-17; the results are in [[PREPRODUCTION-CHECKS]].

### Safe to show or say

| Claim | Evidence | Caution |
|---|---|---|
| Content is written once and referenced, never copied | [[ADR-012 — Content Records Represent Communication Units]], [[ADR-030 — Separate Global and Repeatable Structures]] | Within one brand. Across brands content is copied. |
| An edit in a campaign changes that campaign; changing the shared library is a deliberate click | [[ADR-040 — Introduce Override Layer]], [[ADR-041 — Override Precedence]], [[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]] | |
| A decision slot picks per reader, from content a person has marked ready and published, and the pick is explainable | [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]], [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]], [[ADR-085 — Decision Resolution Should Be Optionally Explainable]], [[ADR-127 — Decision Execution May Use Recipient Context]] | Built: up to five picks per slot, ranked, the empty-send floor. Not built: minimum items and fallback content. The app does not use the word "approved": the rule is active, machine ready, marked ready for the channel, with a published version. Every pick has a reason, but never say "the best pick": most reasons read "tied … ordered randomly". In the demo most readers share the first two picks and differ in the third. |
| AI suggests, a person decides | [[ADR-081 — AI Ranks Within Governed Candidate Sets]], [[ADR-082 — AI May Recommend but Not Publish]], [[ADR-140 — AI Capability Layer]], [[ADR-141 — In-App Assistive AI Actions]] | The demo AI is the mock; the one real adapter is a US vendor's. Never "EU-hosted" or "GDPR-friendly AI". |
| When a machine asks to send, a person approves | [[ADR-142 — Autonomous Workflows and the Automation Boundary]] (the approval boundary only), [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]], [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] | Only the approvals inbox is built. Autonomous workflows are not. |
| A send is planned first and frozen: what goes out, and how many it reaches, are fixed before it is pressed | [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]], [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] | Never "GDPR compliant": the adopter takes the liability, the platform supplies mechanisms. Say nothing about who is left out or about unsubscribing: unsubscription is not built yet (Diede, 2026-10-17), and the demo has no exclusions to draw. |
| Open a reader's message and see the content they received | [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]], [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] | Say "content". The app itself notes that the layout is today's. [[ADR-062 — Snapshot Stores Final Render State]] is superseded by ADR-183: never say the snapshot stores the final HTML. |
| AI suggests and drafts, a person ticks or builds, and a machine's send request waits for a yes | [[ADR-141 — In-App Assistive AI Actions]] (addenda of 2026-10-16 and 2026-10-17), [[ADR-082 — AI May Recommend but Not Publish]], [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]], [[ADR-142 — Autonomous Workflows and the Automation Boundary]] (the approval boundary only), [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] | "Draft with AI" fills the fields a person ticks on a record the person created; "Prepare from a topic" builds an empty variant's blocks and subject, creates no records. Confirmed by running (round 2): "Draft with AI" also proposes categories, which a person ticks too. Neither AI result waits in Approvals (Settings says "no approval step"); the request in Approvals is a machine's send. Never "approved" for an AI result; AI cannot set "Machine ready". The demo AI is a mock that returns nothing readable, so result frames are drawings. |
| Other systems reach the core through the API, each with its own key and permissions | [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]], [[ADR-150 — Tenancy and Access Model]], [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]], [[ADR-120 — CRM as Customer Source of Truth]], [[ADR-126 — Maintain Local Recipient Projection]] | Built and tested for a CRM: contacts and consent in, read back. A shop and a warehouse or analytics tool are only possible through the API: no export, no sync, no connector. Draw doorways into the core, never plugs; no vendor names; no "n8n" row from the development database. |
| A developer, or an AI assistant under review, adds a file at the supported seams | [[ADR-143 — AI-Assisted Development Boundary]] §1 and §7 | The supported seams are exactly the four drops. The AI's output is a proposal, never a deployment. Never "no developers needed", never "AI builds your system", never a claim about dev-data safety (the pseudonymisation guard is not built). Never an assistant's brand or name. |
| The reasons stay with the code: decisions, tasks and changes in the same repository | `README.md` (`docs/` is part of the repository), [[ADR-143 — AI-Assisted Development Boundary]], `docs/CLAUDE.md` | Say "in the same repository". **The repository is public on GitHub with no licence** (verified 2026-10-17), so "public" is true and the film may say it if Diede wants; "open source", "free" and "use it" are never said, because without a licence nothing is granted. A published playbook (website or e-book) is planned and does not exist. Confidential decisions, the logo work and the counsel material are gitignored and never shown. |
| A stranded send is flagged and a person releases it | [[ADR-192 — A Stranded Send Is Flagged, and a Person Releases It]] | |
| Clicks come back as signals that fade with time and shape the next pick | [[ADR-110 — Insight Layer Transforms Events Into Signals]], [[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]], [[ADR-112 — Signals Use Time-Based Decay]], [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] | Clicks only. Opens are not counted and are never shown as a rate. |
| A dropped file is picked up: a content block, a decision strategy, an AI task | The registries for modules, strategies and AI tasks rescan on change; [[ADR-131 — Email Module Templates Use MJML as Source Format]], [[ADR-198 — The Email Block Set Is Seven Blocks, Square Images and Text Links]] | Run on scratch. Each has its own file count; a block and a strategy show in the open editor only after a page reload, an AI task on refocus (section 12). |
| The delivery provider can be swapped with a file and a few lines | [[ADR-100 — Provider Layer as Send and Feedback Adapter]], [[ADR-101 — Provider Capabilities Are Explicit]], [[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]] | Run on scratch: one new file and six inserted lines in four places in `factory.py` per provider (eleven for two); the server restarts by itself because `factory.py` was edited. A push-only provider is listed for the push variant and not for the email one (run, round 2). |
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
- **"No developers needed", "AI builds it for you", "AI deploys".** Extension is convention, not no-code, and the AI's output is a proposal (ADR-143).
- **"Syncs with", "connectors", "integrates with" a product, "native", "out of the box", "plug-and-play", "feeds your warehouse", "exports to", "tracks conversions", "real-time", "continuously updated", "self-learning".** None is built or shown.
- **"Open", "open source" or "free" documentation or code.** The repository is public but has no licence; "public" is true, the others are not.
- **Unsubscribing, opt-out, "leaves out whoever said no", counts excluded for consent or suppression.** Unsubscription is not built yet (Diede, 2026-10-17), and the demo has no excluded reader. Crop the Unsubscribes column and its footnote on the Results card, and the unsubscribe row of the envelope on "As sent".
- **"Byte for byte", "exactly what was sent" for the layout.** The content is exact; the layout is today's.
- **"Real email" on the mock provider.** The button reads "Send to N".
- **Hosted, SaaS, "try it".** It is a local proof of concept.
- **A competitor's or a vendor's name or logo.** The market is described without names.
- **The category Graph.**

## 12. The four drops, as the code allows them

These are the exact seams for Act 3. Each was performed for real on a scratch copy on 2026-10-17; the exact files, console lines and timings are in [[PREPRODUCTION-CHECKS]] (section 5 and its appendix).

**Why the manager app lags.** The server finds a new file at once: the registries for blocks, strategies and AI tasks rescan when their folder changes, and a new file never restarts the server. The manager app caches some lists until a page reload (block manifests, the strategy list) and refetches others when the window regains focus (the settings read, which carries the AI tasks and the providers). That is the whole difference between the rows below.

| Drop | Where | What is really needed | What the manager then sees |
|---|---|---|---|
| **A content block** | `storage/modules/email/<name>.json` and `<name>.html`; the `.mjml` source is optional and compiled by `npm run build:modules` in `frontend/` (0.58 s) | A manifest that names fields already defined in `storage/fields.json` (a field that is not defined gets the block skipped), and the template. The MJML route is three files plus the build; a hand-written template with no MJML is two files and no build. CI checks that the committed `.html` matches the `.mjml`. | **After a page reload.** Before it the open editor lists the block by its file name and says it "cannot be edited or rendered". After a reload it shows "Quote" with its fields. A quote's attribution has no field of its own, so the block uses `heading`, which the editor labels "Heading". |
| **A decision strategy** | `backend/app/decision/strategies/<name>.py`, shaped like `top_score.py` (a class with `meta` and `rank`) | One file, found by a package scan. **It must declare the slot's settings keys** (`content_score_weight`, `preference_score_weight` on the demo slots), or choosing it fails with "strategy_config has key(s) not declared by this strategy". | **After a page reload**, as a label ("Recency boost") in the slot's Strategy list. On the demo a recency bonus has no visible effect, because every record was written by the reset a moment ago: show the file and the list entry, never a result. |
| **An AI task** | `backend/app/ai/tasks/<name>.py` with a `META` object and a default prompt | One file. The developer fixes what it reads and what it returns; the prompt text lives in the database and belongs to the manager ([[ADR-140 — AI Capability Layer]] §4). | **On refocus or on re-entering Settings**, no reload: a new record under Settings, AI prompts, with its default prompt and "Publish as version 1". The Model select lists vendor model names, so crop it. Running it needs a screen, so show the entry, not a run. |
| **A delivery provider** | `backend/app/delivery/providers/<name>.py` beside `resend.py`, plus in `factory.py` the import, a branch, a label and the tuple entry | A file **and** six inserted lines in four places in the factory. The provider must declare which channels it carries (a push variant does not offer an email provider) and `reaches_real_inboxes`, which defaults to True. | The server restarts by itself, 1.4 s, **because `factory.py` is an edited file**; a new file alone restarts nothing. The picker lists it **on refocus**, under the label added to `PROVIDER_LABELS`. |

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

What the pre-production checks changed, each of which would otherwise read as a mistake:

- **The hook's numbers held, the picks did not.** 123, 369 and 15 are identical after every reset, but the individual picks reshuffle, because tied candidates are ordered at random. Any frame that shows what a named reader got is read after the final reset.
- **"From content a person approved" became "marked ready".** The app does not use the word "approved".
- **The AI scene is two modes, not one flow.** "Use this" in the editor and a request in Approvals cannot be the same suggestion. The film shows the default mode, then a different request in Approvals (S08).
- **The demo has no exclusions, and unsubscription is not built yet.** The consent and suppression counts the send scene was built on do not exist, and Diede has decided (2026-10-17) that the film makes no claim about unsubscribing, so the send and "As sent" scenes no longer claim to show them (S09, S10), and the Results card is cropped around its Unsubscribes column (S11).
- **A new block needs a page reload.** The film shows the reload (S13).

What Diede's review of the storyboard changed, with the reasons:

- **The AI premise sits in S03 and S12, not in S02.** "AI has changed what a company, or its agency, can build for itself" is a premise, not a feature claim, and a muted viewer meets it in the first 30 seconds. In S03 it bridges into the core; S12 and S16b carry its proof in picture (ADR-143 lists the four drops as the supported seams for AI-assisted work, and says the architecture has been built that way). "Or its agency" is deliberate: the audience is agencies. No "faster", no "no developers needed".
- **S08 follows the app's real flows,** "Draft with AI" after "New record" and "Prepare from a topic" in an empty variant. Neither result waits in Approvals, so the Approvals shot is a machine's send request. With the demo's mock AI the results are drawings.
- **Other systems are shown as doorways into the core,** not plugs, because the core calls none of them (S03b). Only a CRM path is built; the others are possible through the API.
- **S16 is about any sending service** for the channels that exist, email and push: one interface, a file and a few lines. It does not promise other channels.
- **S16b says where the reasons live:** in the same repository as the code. **Correction, same evening:** an earlier version of this brief said that what is published was not decided. The repository is in fact public on GitHub (no licence), and its documentation with it; the handoff of the evening session recorded it. The film may say "public" if Diede wants, and never "open source" or "free".
- **S20's second line is a tone,** "Always adapting to your business.", not a claim about updates.

## 14. Deliverables of the film

1. Master, 16:9, 3840×2160, 24 fps, narration A (the synthetic read), burned-in captions, plus a captions-off version.
2. Narration B version (when Diede records it).
3. Teaser, 60 to 75 seconds.
4. SRT captions and a plain transcript.
5. One poster frame: the S07 triptych or the S01 numbers.
6. The frame project itself (the code that draws the frames), reading the name from `product.json`, so a rename or a design change is a re-render, not a rework.

## 15. Pre-production checks

Run on 2026-10-17, on a scratch database and a throwaway worktree, never on the real development data. Checks 1 to 5 are done and recorded in [[PREPRODUCTION-CHECKS]]; check 6 is open.

1. **Done.** Reset the demo on scratch and re-read every number the film uses. The hook's 123, 369 and 15 held across two resets. The counts excluded for consent and suppression are zero.
2. **Done.** Three readers who get different picks: Lea Huber (#32), Michael Zimmermann (#127), Peter Müller (#330), disjoint in both resets. Their ids and themes are stable, their individual picks are not.
3. **Done.** Seed Approvals and trace the AI request. It needs a published prompt, the task's Output set to "held for review", and a press of "Suggest with AI". The seed script makes only "Send a prepared campaign" requests.
4. **Done.** All four drops performed for real (section 12).
5. **Done.** "As sent" re-captured: the notices are gone after a fresh reset and return after any drop. The flaws of section 8 are listed with their state.
6. **Decided 2026-10-17.** The name is parameterised: the end card reads `product.json` at render time. The name is a neutral working title until a brand is chosen; no brand is cleared.

**The second round is done** ([[PREPRODUCTION-CHECKS-2]]): (a) S08 flows, verified with the mock (nothing readable) and with a stand-in reply whose labels were all seen; (b) a push-only provider, verified; (c) the S16b files and four change-history lines, verified; (d) the Integrations screen, verified on scratch; (e) S05, S06, S17 and S18: S05 and S06 match with small differences, **S17 and S18 differ from the first storyboard** and the scenes are corrected. What remains is Diede's decision on a real model, the capture of the final reset, and the follow-ups of that file's section 8 (project defects, not film work).

**Re-read after the final reset (read-only, on the development database, 2026-10-17, 20:06 UTC, after Diede's reset at 19:44 UTC).** The hook's numbers hold: the Familienherbst slot has 369 picks, 123 readers and 15 distinct content; the send is 123 sent, 0 failed, 0 excluded. The three readers of S07 are unchanged and their picks still do not overlap (record titles, in rank order). Lea Huber (#32): "Kinderregenjacke für 49 Euro: Die Kapuze gehört zur Probe", "Augsburg: Naturheft für Kinder am 15. Mai", "Sitzmatte für Familienpausen: 9 Euro gegen die kalte Bank". Michael Zimmermann (#127): "Tierspuren im Schnee: Erst den Maßstab dazulegen", "Kompaktfernglas für 89 Euro: 8-fach und 310 Gramm", "Rosenheim: Spuren und Fotos lesen am 30. Oktober". Peter Müller (#330): "Grathaus Basis Kinderregenhose: 35 Euro und Platz zum Hinhocken", "Familienrunde als Ausflugstagebuch: Drei Fragen genügen", "Familienwandern im Chiemgau: Drei gute Pausen statt Gipfelziel". 101 of the 123 readers share the two most common picks. The headlines the emails show (the module headline fields) are read in the capture pass. **The capture database.** A copy of this data, the database `trailer_capture`, was made on 2026-10-17 (a dump of `app` restored into a new database on the same Postgres container; same numbers, same picks), so that the capture pass can write (publish the two AI prompts, seed Approvals, make the email-plus-push campaign, issue an integration key) without touching the demo. It holds the development users, so no Users screen is captured. It is dropped when the captures are done.

**Order for the real capture.** Reset once, on purpose, on the date the film should show. Capture everything that needs the demo as it is (S01, S05 to S11, S17, S18). Seed Approvals and publish the AI prompt before S08. Perform the four drops last, because each change in `storage/modules/email/` brings the "As sent" notices back. Do not reset again after the captures: the picks would reshuffle.

## 16. Decisions and open questions

### Decided by Diede on 2026-10-17, reviewing the storyboard

1. **Cuts.** A master and a teaser of 60 to 75 seconds.
2. **The developer world in the dark-warm look.**
3. **Initials avatars only, no faces,** and the avatar is the demo's own. Names and content on screen are the demo's (the outdoor brand): none is invented for the film.
4. **The narrator:** the synthetic read of script A first. Script B is for Diede to record later.
5. **The name** is parameterised and read from `product.json`.
6. **Music:** both moods of the two samples, no strings and no piano.
7. **"Consent" stays** in S03 and S18, as long as the film never talks about or shows exclusion, opt-out or unsubscription (decision 8).
8. **Exclusions and unsubscribing: unsubscription is not built yet, so the film makes no claim about it.** S09 and S10 draw only what the demo has and never speak of readers left out; S11 crops the Unsubscribes column and its footnote. Fixing the demo seed (opted-out and suppressed readers, an unsubscribe that sticks) is a change to the project's demo data, not to the film, and does **not** bring the "who was left out and why" shot back: that waits until unsubscription is built. The first wording of S09 and S10 is kept at the end of this section for that day.
9. **The quote block's attribution** has no field of its own. The film leaves "Heading" empty in the frame and gives the quote no author (S13). Adding one more file (`storage/fields.json`) to the scene stays open as an alternative.
10. **S08:** the AI subject-line suggestion is dropped; the scene shows creating a content record and a variant, then Approvals.
11. **S16:** about any sending service, not email only.
12. **S20:** the twist "Always adapting to your business." under the unchanged tagline.
13. **S03:** show how other systems (CRM, data warehouse, shop, analytics) reach the core.
14. Scenes S01, S04, S05, S06, S07, S09, S10, S11, S12, S13, S14, S15, S17 to S19 were marked okay.

### Decided later the same evening

15. **S08's result frames are drawings,** with exact labels (the stand-in replies of round 2). No real model.
16. **Music:** both samples are accepted for the first round; if only one can be used, the developer mood, B.
17. **The end card's address is Diede's LinkedIn profile for now** (`linkedin.com/in/diede-slembrouck`, text only). Whether to add an email address (`ds@diede-slembrouck.de`) or a domain (`thisisdiede.com`) later is open. The frame project takes the contact as one value, so changing it is a re-render. The repository's own address is not shown: it still carries the retired working name.
18. **The film does not say "public".** The default holds: "in the same repository" (S16b). The word appears only in this brief's notes, nowhere in a narration line or on a card.
19. **The demo data is final and may be used.** Diede reset the demo on the development database on 2026-10-17 (about 21:45 local, 19:44 UTC). The hook's numbers were re-read from it, read-only, at 20:06 UTC: see section 15. The demo must not be reset again after the captures.

### Still open

1. **The final music.** Composed or licensed along the two moods; the source is to be chosen.
2. **S17's two-variant campaign.** The demo has none. The default is to make one on the capture database (a minute, no project file changes); the alternatives are a change to the demo seed or showing two campaigns side by side.
3. **The email address or domain** for the end card, later (decision 17).
4. **Pacing.** About 70 percent of the film is narrated. The first animatic with the synthetic read will show whether it needs air; S03b and S16b are the first to compress.

### Choices made when the checks were applied

These were Claude's, made on 2026-10-17 after the checks. Diede then reviewed the storyboard and marked S07, S09 and S10 okay, so they stand; they can still be reversed in the storyboard and the narration. S08 was changed by Diede (decision 10).

1. **S08 used the default AI mode, then a different request in Approvals.** Superseded: Diede replaced the subject-line suggestion with creating a content record and a variant (decision 10). What stays from the checks: the Approvals shot is the seeded "Send a prepared campaign" request from "Acme Agency (demo)", and an AI result never waits there.
2. **S09 and S10 no longer talk about exclusions.** The demo has none, so the picture cannot show them. S09 now says the system plans the send, shows how many people it reaches and freezes what they will get; S10 says the reader's message shows what they received and why each piece was picked. The first wording was: S09 "… leaves out whoever said no, and tells you who and why." S10 "… and the reason anyone was left out." It does not come back until unsubscription is built (decision 8).
3. **S07 says "marked ready", not "approved".**

### Choices made after the review

These are Claude's, made on 2026-10-17 while applying Diede's feedback, and not yet reviewed.

1. **The AI premise sits in S03 and S12,** with "or its agency", and not in S02 (reasons in S03 of the storyboard and in section 13).
2. **S08 shows the app's real flows,** "Draft with AI" after "New record" and "Prepare from a topic" in an empty variant, then the machine's send request in Approvals; it does not caption the AI results as approved there.
3. **S03b is a new scene** for the other systems: doorways into the core, with the CRM path built and the others only possible.
4. **S16b is a new scene** for the documentation in the same repository, built on the factory file of S16, ADR-101 and ADR-143.
5. **S16 adds a push provider** next to the email one. It has not been run.
6. **The persona** is the demo's own avatar ("IA"), not a named person.
7. **The film grew to about 4:46** with the two new scenes; the end card and S04 were shortened to make room.
8. **S17 is built from a campaign made to carry both variants** (the demo has none), and its "nothing is sent" words come from the send step.
9. **S18 is ten shots, in the navigation's order,** with the Audiences and Recipients screens cropped so that no exclusion, opt-out or funnel count shows.
10. **S08's result frames are drawings with exact labels** (the stand-in replies of round 2), not a real model's output.

## 17. Sources

- `docs/business/PRESENTATIONS-2026-11.md`, `docs/business/POSITIONING.md`, `docs/business/BRIEF.md`, `README.md`, `docs/playbook-strategy.md` (§1 to §5).
- `docs/design/HANDOFF.md`, `docs/design/DESIGN.md`, `docs/design/CONSTRAINTS.md`, `docs/design/tokens.css`, `docs/design/renders/README.md`.
- `docs/design/ux-audit-2026-10-17/` (live captures and findings).
- The decision records named in section 11.
- Code read for the file seams: `backend/app/modules/registry.py`, `backend/app/decision/strategies/`, `backend/app/ai/tasks/`, `backend/app/delivery/providers/factory.py`, `backend/app/channels/registry.py`, `storage/`.
- The demo seed: `backend/app/demo/` and `backend/scripts/demo_reset.py`.
- [[PREPRODUCTION-CHECKS]], the results of the checks of section 15, with the exact files of the four drops.
- The sweeps of 2026-10-17 for S08 (the AI flows and Approvals, read from the code) and S03b (what is built for other systems), summarised in the storyboard checks and in section 11.
- `audio/`: the two mood samples and `synth.py`, which makes them.
- [[PREPRODUCTION-CHECKS-2]], the second round, and [[HANDOFF-2026-10-17]], the evening handoff (what reached `main`, what stays out of the public repository, the screens that changed).
