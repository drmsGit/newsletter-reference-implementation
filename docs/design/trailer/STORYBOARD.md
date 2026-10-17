---
type: reference
status: draft
created: 2026-10-17
---

# Trailer storyboard

Twenty scenes, about 4:10. Read [[TRAILER-BRIEF]] first: it holds the decisions, the look, the claim ledger and the checks that must be done before any frame is built. [[VOICEOVER]] has both narration scripts clean for recording. `storyboard.html` shows these scenes as cards with their reference frames.

**How to read a scene.** *See* is the shot, in order. *Source* is where the frame comes from, as a path under `docs/design/`. **Live** is a capture in `ux-audit-2026-10-17/screenshots/` (brand Grathaus Outdoor, real demo data, German email content). **Render** is a drawn board in `renders/` (brand Nordlicht Kaffee, invented data: layout only). *Text* is burned-in on screen. *A* and *B* are the narration (third person, first person). *Evidence* is the ADR or code that makes the scene true. *Check* is what has to be confirmed before the frame is built. **T** marks a scene that is in the 60 to 75 second teaser.

All UI frames are drawn at 1440×810 logical px and rendered at 3840×2160. Where a live capture and a render disagree, the live capture wins.

---

## Act 0: Hook (0:00 to 0:14)

### S01 · 0:00 to 0:14 · The question · T
- **See.** Black. A low drone and a pulse, one beat a second. Three push-ins of about two seconds, each tight on one row with no navigation or chrome around it, a muted hit on each: (1) the Deliveries row `sent · 123 / 0 / 0` for Familienherbst; (2) the Decision slots row "Für Sie ausgewählt, Familienherbst / Deutsch, recipient_top_score, 369 picks"; (3) one reader's "As sent" message, the email filling the frame. Then black again.
- **Source.** Live `29-deliveries.jpg`, `33-slot-detail.jpg`, `31-as-sent.jpg`.
- **Text.** "One campaign." (with shot 1) "123 readers." "369 choices." then, alone, "Could you say why?"
- **A.** One campaign. A hundred and twenty-three readers. Three hundred and sixty-nine choices. Could you say why each one was made?
- **B.** One campaign. A hundred and twenty-three readers. Three hundred and sixty-nine choices. I wanted to be able to say why each one was made.
- **Sound.** Drone, pulse, three hits on the three numbers, a held half-second of silence after the question.
- **Evidence.** Pillar 1 ("I can't see what the system is doing, or why"). [[ADR-127 — Decision Execution May Use Recipient Context]], [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]].
- **Check.** The numbers are the live demo's. 123 readers × 3 picks = 369; 15 distinct pieces of content. Re-read all three after a fresh reset and rewrite the line from what the reset gives.

---

## Act 1: The idea (0:14 to 0:58)

### S02 · 0:14 to 0:30 · Two ends of the market · T (shortened)
- **See.** Abstract, flat, in the film's own tokens; no UI and no brand. Left: a small box made of locked slots with a lock glyph, the text "Easy, until you outgrow it." Right: a tower of grey blocks that climbs out of the top of the frame, the text "Powerful, until you try to change it." The two ends slowly pull apart; the space between them stays empty.
- **Source.** Built for the film. No existing frame.
- **Text.** "Easy, until you outgrow it." "Powerful, until you try to change it."
- **A.** Most companies end up choosing between two things. A tool that's easy, until they outgrow it. And a system that's powerful, until they try to change it, or leave it.
- **B.** I kept meeting companies caught between two things. A tool that's easy, until you outgrow it. And a system that's powerful, until you try to change it, or leave it.
- **Sound.** Strings begin to rise. A low hit on "Powerful".
- **Evidence.** `docs/playbook-strategy.md` §2 and §3 and the November presentations note. It is a positioning argument, not a measurement.
- **Check.** No numbers, years or vendor names on screen.

### S03 · 0:30 to 0:44 · The owned core · T (shortened)
- **See.** The same ground, now calm. A square in the middle, labelled in four small lines: content, campaigns, rules, consent. Around it, three sockets: Delivery, AI, Channels. A plug in each. One plug is pulled and a different one slides in; then another socket; then the third. The square never moves.
- **Source.** Built for the film, in the diagram style of the presentation material (flat, hairlines, petrol for the one thing that matters).
- **Text.** "Your core." and, small, under each socket, "replaceable".
- **A.** What if the company kept the core, its content, its campaigns, its rules, its consent, and everything around it were a part you could replace?
- **B.** So I started from the other end. The company keeps the core: its content, its campaigns, its rules, its consent. Everything around it is a part you can replace.
- **Sound.** The strings resolve into the first warm piano note as the last plug settles.
- **Evidence.** [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] ("The platform owns communication state. Providers consume delivery artifacts."), [[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]], [[ADR-171 — Nothing Required to Run This Platform Is Commercial]].
- **Check.** Do not draw "all data stays inside". The adopter chooses what each provider receives.

### S04 · 0:44 to 0:58 · The title · T
- **See.** The square collapses to a point, the point opens into the title card: the product's name (read from `product.json` at render time), under it "Building a communication system you control.", under that "By Diede Slembrouck". Hold.
- **Source.** Built for the film.
- **Text.** The name; the tagline; the author line.
- **A.** This is a reference for building a communication system you control.
- **B.** This is what I built: a reference for a communication system you control.
- **Sound.** The first full music hit on the card; then the manager's pulse begins.
- **Evidence.** The approved author-led framing of 2026-10-12 (`docs/design/presentation/CONTENT-DRAFT.md`, last section) and `README.md`.
- **Check.** The name is a neutral working title. No logo. No claim that a brand is chosen or cleared.

---

## Act 2: The manager (0:58 to 2:20)

The manager's world is linen and petrol, three columns. The signed-in avatar is an initials circle for "Anke Voss" (AV).

### S05 · 0:58 to 1:06 · Content
- **See.** Content, Records. The list scrolls; one record opens ("Tagestouren im Chiemgau: Die Rückfahrt zuerst planen"). On its page, the category scores 1 to 10. A slow push-in on the scores.
- **Source.** Live `14-records.jpg`, `15-record-detail.jpg`, `17-categories.jpg`.
- **Text.** "Content" as the screen's own title; small caption "Tours in the Chiemgau: plan the return first".
- **A.** A manager starts with content. Written once, kept in one place, and scored by what it's about.
- **B.** It starts with content. Written once, kept in one place, scored by what it's about.
- **Sound.** Soft ticks on the cursor; the piano pulse continues.
- **Evidence.** [[ADR-012 — Content Records Represent Communication Units]], [[ADR-030 — Separate Global and Repeatable Structures]].
- **Check.** Not the Graph tab: the live graph has overlapping labels and is not shown.

### S06 · 1:06 to 1:16 · A campaign points to it
- **See.** The variant editor. The module stack on the left with the cue chips "Record", "Slot", "Typed in". On the right the open module: a headline is edited and its label turns "overridden here"; the line "Back to the catalogue value" appears beside it. A second pass: "Change Headline in catalogue" is shown but not clicked.
- **Source.** Render `21-editor.png` for the chips and the override group; live `05-variant-editor.jpg` for the real module data and the layout.
- **Text.** None beyond the app's own labels.
- **A.** A campaign doesn't copy it; it points to it. When one headline has to change, only that email changes.
- **B.** A campaign doesn't copy it. It points to it. When one headline has to change, only that email changes.
- **Sound.** A single soft tick as the label changes.
- **Evidence.** [[ADR-040 — Introduce Override Layer]], [[ADR-041 — Override Precedence]], [[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]].
- **Check.** The cue chips are drawn in the render and may differ in the live app; follow the live app.

### S07 · 1:16 to 1:36 · One slot, three readers, three picks · HERO · T
- **See.** (1) In the editor a module row "Slot" and its settings: "Für Sie ausgewählt", strategy `recipient_top_score`, shows up to 3. (2) The Preview sheet opens; "Preview for a recipient" is filled with reader A; the email shows three pieces of content. (3) The same sheet, reader B, three different pieces. (4) Reader C. The three previews end side by side as a triptych, the same email shell, three different sets, the German headlines captioned in English underneath. (5) Pull back to the Decision slots screen: the slot's page with "369 picks, 123 distinct recipients, 15 distinct content", "What it chooses from" and "What it has picked".
- **Source.** Live `06-preview.jpg` (the sheet), `33-slot-detail.jpg` (the slot's page); render `23-editor-slot.png` and `32-decision-slots.png` for the settings group.
- **Text.** "Same email. Three readers. Three picks." Under the slot's page: "Every pick has a reason."
- **A.** Now one email with a slot in the middle. The slot picks for each reader, from content a person approved. Same email, three readers, three different picks. And every pick can be explained.
- **B.** Then one email with a slot in the middle. The slot picks for each reader, from content a person approved. Same email, three readers, three different picks. And I can see why each pick was made.
- **Sound.** The piano pulse lifts; a tick for each preview; one low hit as the triptych locks.
- **Evidence.** [[ADR-081 — AI Ranks Within Governed Candidate Sets]], [[ADR-082 — AI May Recommend but Not Publish]], [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]], [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]], [[ADR-085 — Decision Resolution Should Be Optionally Explainable]], [[ADR-127 — Decision Execution May Use Recipient Context]].
- **Check.** Find three readers who really get different picks. The live "Preview for a recipient" is a text field, not a chip: draw the field. "From content a person approved" is true only for approved content records: confirm the candidates the slot shows are approved.

### S08 · 1:36 to 1:50 · AI proposes, a person decides · HERO
- **See.** (1) The envelope group: the button "Suggest with AI". Three suggested subjects appear, each with a "Use this" button, a caution line ("Suggestions can be wrong. Check the subject before you use it.") and the provenance line as the app writes it (tokens, provider, prompt version). One is chosen. (2) Cut to Approvals: a request waits, "Approve and run" under it. The cursor presses it; the request leaves the list.
- **Source.** Render `21-editor.png` (suggestions), `01-approvals-light.png` (the inbox); live `41-ai-prompts.jpg`.
- **Text.** None beyond the app's labels.
- **A.** AI can suggest and draft. A person decides what goes out. Even when a machine asks to send, someone has to say yes.
- **B.** AI can suggest and draft. A person decides what goes out. Even when a machine asks to send, someone has to say yes.
- **Sound.** Two soft ticks; a firm tick on "Approve and run".
- **Evidence.** [[ADR-140 — AI Capability Layer]], [[ADR-141 — In-App Assistive AI Actions]], [[ADR-142 — Autonomous Workflows and the Automation Boundary]] (the approval boundary only), [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]], [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]].
- **Check.** (a) The demo AI is the mock: write believable German or English suggestions but keep the provenance line as the app writes it, never a vendor model name. (b) What creates a held "Apply an AI-suggested subject" request is not verified. If it is not a plain path, use "Send a campaign" requested by an integration, as the render does. (c) Approvals is empty after a reset: seed it first.

### S09 · 1:50 to 2:00 · The send is planned first
- **See.** The Send screen, steps one to four in a column: what goes out; send a test; plan the send (the plan freezes what will be sent, and a line says who was left out for consent and who for suppression); then the docked step four, "Send to N". The cursor presses it.
- **Source.** Live `11-send.jpg`; render `25-send-plan.png`, `26-send-ready.png`.
- **Text.** None beyond the app's labels.
- **A.** Before anything leaves, the system plans the send, leaves out whoever said no, and tells you who and why.
- **B.** Before anything leaves, the system plans the send, leaves out whoever said no, and tells me who and why.
- **Sound.** A tick per step; a deeper hit on the final press.
- **Evidence.** [[ADR-163 — Per-Channel Consent and Addressability]], [[ADR-086 — Decision Slots Fail Gracefully]], [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]].
- **Check.** With the mock provider the button reads "Send to N", never "Send real email". The numbers excluded for consent and suppression come from the reset, not from the render.

### S10 · 2:00 to 2:12 · Exactly what each person got · HERO
- **See.** Deliveries. A send is chosen; its recipients table; one reader is opened and "As sent" shows the subject, the preheader and the message with its three pieces of content. A last three seconds: a stranded send with a flag and a "Release" button, a person presses it.
- **Source.** Live `31-as-sent.jpg`; render `30-delivery-stranded.png` and `31-delivery-as-sent.png`.
- **Text.** Under the message: "The content this reader received."
- **A.** Afterwards, open any reader's message: the content they received, and the reason anyone was left out.
- **B.** Afterwards I can open any reader's message: the content they received, and the reason anyone was left out.
- **Sound.** The pulse thins to the piano alone; one low tick on "Release".
- **Evidence.** [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]], [[ADR-086 — Decision Slots Fail Gracefully]], [[ADR-192 — A Stranded Send Is Flagged, and a Person Releases It]].
- **Check.** Say "content", never "byte for byte": the live screen warns that the layout is today's. Redraw the unsubscribe link without `localhost`. The stranded send is only drawn in the render; the demo cannot produce it, so mark the frame as a drawing in the shot notes. Never "the snapshot stores the final HTML".

### S11 · 2:12 to 2:20 · The signal comes back
- **See.** The campaign's Results card: the delivery table, then the engagement table with clicks, unique clickers, the click rate and unsubscribes. A fading curve draws beside it. Back in the slot, the next pick shifts by one row.
- **Source.** Render `20-campaigns.png` for the layout; the figures come from the live demo after the reset.
- **Text.** "Clicks count. They fade."
- **A.** Their clicks come back as signals that fade with time, and shape the next pick.
- **B.** Their clicks come back as signals that fade with time, and shape the next pick.
- **Sound.** A rising line of three soft ticks, then the music drops away.
- **Evidence.** [[ADR-110 — Insight Layer Transforms Events Into Signals]], [[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]], [[ADR-112 — Signals Use Time-Based Decay]], [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]].
- **Check.** Clicks only; the app itself says opens are not counted. Never show or say an open rate. The decay curve is drawn from the real half-life values; read them from the code before drawing.

---

## Act 3: The developer (2:20 to 3:20)

The developer's world is the project's dark values: ground `#14110f`, card `#1e1b18`, accent `#6fc3dd`, text `#f4eee6`, system monospace.

### S12 · 2:20 to 2:28 · Behind the screens
- **See.** A hard cut from linen to dark. A terminal and an editor side by side on the repo tree: `storage/`, `backend/app/`. A cursor blinks. A small caption: "The developer".
- **Source.** Built for the film from the real folder names.
- **Text.** "The developer".
- **A.** Behind the screens, a developer keeps it growing. Not by asking a vendor. By adding a file.
- **B.** Behind the screens, someone has to keep it growing. I wanted that to mean adding a file.
- **Sound.** The music thins to a pulse; a restrained whoosh on the cut only.
- **Evidence.** `docs/playbook-strategy.md` §4 (convention-based extension, not no-code).
- **Check.** Draw only folder and file names that exist.

### S13 · 2:28 to 2:40 · Drop a content block · T
- **See.** In the editor, two new files appear beside `hero.json` and `hero.html`: `storage/modules/email/quote.json` and `quote.html` (and `quote.mjml`, its source). In the terminal `npm run build:modules` runs and ends clean. A low hit as the files land. Cut to the manager's variant editor: "Add a module" opens; "Quote" is in the list; it is added; it renders in the stack and in the preview.
- **Source.** `storage/modules/email/hero.json` for the manifest shape; live `05-variant-editor.jpg` for the "Add a module" control.
- **Text.** The file names, as typed.
- **A.** A new content block: a manifest and a template. It appears in the editor.
- **B.** A new content block: a manifest and a template. It appears in the editor.
- **Sound.** One low hit on the files landing; a tick on the manager's side.
- **Evidence.** [[ADR-131 — Email Module Templates Use MJML as Source Format]] (and its addendum), [[ADR-198 — The Email Block Set Is Seven Blocks, Square Images and Text Links]]; the module registry rescans when the folder changes.
- **Check.** The block "quote" is invented for the film and must really be built, on a scratch branch. A manifest may only name fields already defined in `storage/fields.json`. Confirm whether the editor shows the new block without a refresh, and show exactly that.

### S14 · 2:40 to 2:52 · Drop a decision strategy
- **See.** `backend/app/decision/strategies/recency_boost.py`, a class with `meta` and `rank`, shaped like `top_score.py`; the first lines of the real `top_score.py` sit beside it. The file is saved. Cut to the slot settings in the manager's editor: the Strategy list shows "Recency boost" beside `top_score` and `recipient_top_score`; it is chosen.
- **Source.** `backend/app/decision/strategies/top_score.py` for the shape; render `23-editor-slot.png` for the settings group.
- **Text.** The file name, as typed.
- **A.** A new way to decide who sees what: one file, written by whoever knows the data.
- **B.** A new way to decide who sees what: one file, written by whoever knows the data.
- **Sound.** One low hit as the file saves.
- **Evidence.** The strategy registry; `docs/playbook-strategy.md` §4 (a BI team contributes a strategy as a file).
- **Check.** The strategy must be written and must run on scratch data. The scene shows the file and the list entry, not a result.

### S15 · 2:52 to 3:04 · Drop an AI task
- **See.** `backend/app/ai/tasks/…py`: the `META` and a short default prompt, the docstring's line "the prompt itself is not here" visible. Cut to Settings, AI prompts: a new record appears; the manager opens it and rewrites the prompt text in the app.
- **Source.** `backend/app/ai/tasks/subject_preheader.py` for the shape; render `44-settings-ai-prompts.png` and live `41-ai-prompts.jpg` for the screen.
- **Text.** The file name, as typed.
- **A.** A new AI task. The developer defines what it may read and return; the wording of the prompt belongs to the manager.
- **B.** A new AI task. The developer decides what it may read and return. The wording of the prompt stays with the manager.
- **Sound.** One low hit on the save; a tick on the manager's side.
- **Evidence.** [[ADR-140 — AI Capability Layer]] §4, [[ADR-141 — In-App Assistive AI Actions]], [[ADR-143 — AI-Assisted Development Boundary]].
- **Check.** Show the entry appearing, not the task running: running a task needs a screen the film does not have. Verify the entry appears without a restart.

### S16 · 3:04 to 3:20 · Swap the delivery provider · T
- **See.** `backend/app/delivery/providers/` with `base.py`, `mock.py`, `resend.py`; a new `example_mail.py` is added beside them. `factory.py` opens: an `elif` branch, a label line and a tuple entry are added. The terminal shows the server reloading. Cut to the manager's send step: the provider picker lists `mock`, `resend` and `example_mail`.
- **Source.** `backend/app/delivery/providers/factory.py` and `resend.py` for the real shape; live `11-send.jpg` for the picker.
- **Text.** "A file. A few lines. A reload."
- **A.** Even the delivery provider is a part, not a foundation. A file and a few lines, and the company can change who sends, without touching a single campaign.
- **B.** Even the delivery provider is a part, not a foundation. A file and a few lines, and the company changes who sends, without touching a single campaign.
- **Sound.** Two low hits (the file, then the factory); the pulse swells into the next act.
- **Evidence.** [[ADR-100 — Provider Layer as Send and Feedback Adapter]], [[ADR-101 — Provider Capabilities Are Explicit]], [[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]].
- **Check.** Say "a file and a few lines", never "a file". The provider must declare the channels it carries or the picker will not list it. Do not name a real vendor other than Resend (the repo's own worked example). Do not quote `docs/how-to-swap-send-provider.md`.

---

## Act 4: One system (3:20 to 3:52)

### S17 · 3:20 to 3:34 · Email and push
- **See.** A split screen: the manager's linen app on the left, the developer's dark editor on the right. The campaign page shows two variants, Email and Push. The push editor with its one module, then the push preview. A small label, in the app's own words, says nothing is sent.
- **Source.** Live `58-push-editor.jpg`, `60-push-preview.jpg`.
- **Text.** None beyond the app's labels.
- **A.** One campaign: an email for some readers, a push notification for others, each shaped for its channel.
- **B.** One campaign: an email for some readers, a push notification for others, each shaped for its channel.
- **Sound.** The swell builds; the developer's pulse and the manager's piano meet on one beat.
- **Evidence.** [[ADR-160 — Channel Model and Composition]], [[ADR-161 — Channel Execution Shapes]], [[ADR-162 — Channel Rendering and Artifacts]], [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]].
- **Check.** No phone, no lock screen, no buzz: push goes only through the mock provider. The push frames come from the audit and may predate later changes: re-capture.

### S18 · 3:34 to 3:46 · Everything else, in one breath
- **See.** Twelve one-second shots on the beat, each a push-in on one screen: Audiences with its rules, Recipients, a brand profile, Personalisation (the salutation), Roles, an integration key, Monitoring, Deliveries, AI prompts, the approvals history. The navigation's "you are here" in Pale Pink steps down the list as the screens change.
- **Source.** Live `21-audiences.jpg`, `27-recipients.jpg`, `35-profiles.jpg`, `38-personalisation.jpg`, `46-roles.jpg`, `49-integrations.jpg`, `12-monitoring.jpg`, `29-deliveries.jpg`, `41-ai-prompts.jpg`; render `40-decision-history.png`.
- **Text.** None.
- **A.** Audiences. Brands. Roles. Consent. A record of who did what. All in one place, all of it yours.
- **B.** Audiences. Brands. Roles. Consent. A record of who did what. All in one place, and all of it the company's.
- **Sound.** A tick on every cut; the full swell.
- **Evidence.** [[ADR-150 — Tenancy and Access Model]], [[ADR-153 — Audit and Accountability]], [[ADR-163 — Per-Channel Consent and Addressability]], [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]].
- **Check.** Screens 20 to 45 are not designed for dark or for narrow widths: stay light and desktop. No Graph.

### S19 · 3:46 to 3:52 · The three lines
- **See.** Linen ground, nothing else. One line at a time, large, left-aligned: "See what it does." "Change it with a file." "Keep the core." After the third, one beat of silence.
- **Source.** Built for the film.
- **Text.** The three lines.
- **A.** See what it does. Change it with a file. Keep the core.
- **B.** See what it does. Change it with a file. Keep the core.
- **Sound.** The swell peaks on the third line and cuts to silence.
- **Evidence.** The three pillars (`docs/playbook-strategy.md` §3).
- **Check.** The phrase "Keep the core" stays within the claim ledger: the core is the company's content, campaigns, rules and consent.

---

## Act 5: End card (3:52 to 4:10)

### S20 · 3:52 to 4:10 · Title and call to action · T
- **See.** The name (from `product.json`), the tagline "Building a communication system you control.", "By Diede Slembrouck". Then three lines: "The playbook." "The working code." "A conversation." with the address left as an empty slot. Small print at the foot: "A local proof of concept. Email and push built. Demo data is fictional."
- **Source.** Built for the film.
- **Text.** All of the above.
- **A.** Building a communication system you control.
- **B.** I'm Diede Slembrouck. Come and see how it works.
- **Sound.** One piano note under the tagline; silence for the last three seconds.
- **Evidence.** `README.md` (status, licence not chosen), [[PRESENTATIONS-2026-11]].
- **Check.** No "open source", no "free", no URL until one exists.
