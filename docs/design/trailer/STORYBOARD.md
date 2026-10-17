---
type: reference
status: draft
created: 2026-10-17
---

# Trailer storyboard

Twenty scenes, about 4:10. Read [[TRAILER-BRIEF]] first: it holds the decisions, the look, the claim ledger and the checks that must be done before any frame is built. [[VOICEOVER]] has both narration scripts clean for recording. `storyboard.html` shows these scenes as cards with their reference frames.

**How to read a scene.** *See* is the shot, in order. *Source* is where the frame comes from, as a path under `docs/design/`. **Live** is a capture in `ux-audit-2026-10-17/screenshots/` (brand Grathaus Outdoor, real demo data, German email content). **Render** is a drawn board in `renders/` (brand Nordlicht Kaffee, invented data: layout only). *Text* is burned-in on screen. *A* and *B* are the narration (third person, first person). *Evidence* is the ADR or code that makes the scene true. *Check* is what has to be confirmed before the frame is built. **T** marks a scene that is in the 60 to 75 second teaser.

All UI frames are drawn at 1440×810 logical px and rendered at 3840×2160. Where a live capture and a render disagree, the live capture wins.

**Corrected 2026-10-17, after the pre-production checks** ([[PREPRODUCTION-CHECKS]]): S01, S06 and S07 to S16 carry what was verified on a scratch copy of the demo. The narration of S07, S09 and S10 changed (see [[VOICEOVER]]), and three of the corrections are Claude's choices that Diede has not reviewed ([[TRAILER-BRIEF]], end of section 16). That the film says nothing about unsubscribing is Diede's decision (section 16, decision 8), applied to S09 to S11 and S13.

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
- **Check.** Verified on scratch and identical after two resets: 123 readers × 3 picks = 369; 15 distinct pieces of content. Say "readers" or "recipients", never "delivered" (the app shows 122 delivered). Re-read after the final reset, and do not reset again after the captures.

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
- **Check.** The cue chips were seen in the live app on 2026-10-17: the stack shows "Record", "Slot" or "Typed in" beside each module. The override label and the line "Back to the catalogue value" were not re-checked; follow the live app.

### S07 · 1:16 to 1:36 · One slot, three readers, three picks · HERO · T
- **See.** (1) In the editor a module row "Slot" and its settings: "Für Sie ausgewählt", strategy `recipient_top_score`, shows up to 3. (2) The Preview sheet opens. "Preview for a recipient (optional)" is a search field: part of an address is typed (`lea.huber.32`), a result button with the full address appears, it is pressed, and the sheet says "For lea.huber.32@example.com." The email shows the slot's three pieces of content in one slot module, below a shared top (Hero Banner "Vier Dinge im Wald finden", Editorial, Image Left, Image Right). (3) The same sheet for `michael.zimmermann.127`. (4) And for `peter.mueller.330`. The three previews end side by side as a triptych: one shared top, three different tails, the headlines the emails show (the module headline fields, not the records' titles) captioned in English underneath. (5) Pull back to the Decision slots screen: the slot's page with "369 picks, 123 distinct recipients, 15 distinct content", "What it chooses from" and "What it has picked".
- **Source.** Live `06-preview.jpg` (the sheet), `33-slot-detail.jpg` (the slot's page); render `23-editor-slot.png` and `32-decision-slots.png` for the settings group.
- **Text.** "Same email. Three readers. Three picks." Under the slot's page: "Every pick has a reason."
- **A.** Now one email with a slot in the middle. The slot picks for each reader, from content a person marked ready. Same email, three readers, three different picks. And every pick can be explained.
- **B.** Then one email with a slot in the middle. The slot picks for each reader, from content a person marked ready. Same email, three readers, three different picks. And I can see why each pick was made.
- **Sound.** The piano pulse lifts; a tick for each preview; one low hit as the triptych locks.
- **Evidence.** [[ADR-081 — AI Ranks Within Governed Candidate Sets]], [[ADR-082 — AI May Recommend but Not Publish]], [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]], [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]], [[ADR-085 — Decision Resolution Should Be Optionally Explainable]], [[ADR-127 — Decision Execution May Use Recipient Context]].
- **Check.** The three readers are verified: Lea Huber (#32), Michael Zimmermann (#127), Peter Müller (#330), whose picks do not overlap, in both resets. Their ids and themes are stable (family; animal watching; family hiking), their individual headlines are not (tied candidates are ordered at random), so read the headlines after the final reset and caption those. Draw the Preview field as it is: search, result button, "For <address>.", a way back to the generic preview. With no reader chosen the slot shows nothing ("picks per recipient — name a recipient above"). "Marked ready" is the app's rule (active, machine ready, ready for the channel, with a published version); the app never says "approved". Honest limit for the shot notes: 101 of 123 readers share the first two picks and differ in the third. Every pick has a reason, but never "the best pick": most reasons read "tied … ordered randomly".

### S08 · 1:36 to 1:50 · AI proposes, a person decides · HERO
- **See.** (1) The envelope group: the button "Suggest with AI". Three suggested subject and preheader pairs appear, each with a "Use this" button, and under them the app's own provenance line (`… tokens · mock-1 · prompt v1`). One is chosen. The suggestion text is drawn in believable German and the frame is marked as a drawing in the shot notes. (2) Cut to Approvals: a request waits, "Send a prepared campaign", requested by the integration "Acme Agency (demo)", with the audience line and the facts under it. The cursor presses "Approve and run"; the request leaves the list and the send runs.
- **Source.** Render `21-editor.png` (the suggestions' layout), `01-approvals-light.png` (the inbox); live `41-ai-prompts.jpg`. The real screens of both shots are described in [[PREPRODUCTION-CHECKS]], sections 3.1 and 3.2.
- **Text.** None beyond the app's labels.
- **A.** AI can suggest and draft. A person decides what goes out. Even when a machine asks to send, someone has to say yes.
- **B.** AI can suggest and draft. A person decides what goes out. Even when a machine asks to send, someone has to say yes.
- **Sound.** Two soft ticks; a firm tick on "Approve and run".
- **Evidence.** [[ADR-140 — AI Capability Layer]], [[ADR-141 — In-App Assistive AI Actions]], [[ADR-142 — Autonomous Workflows and the Automation Boundary]] (the approval boundary only), [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]], [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]].
- **Check.** The two shots are two modes, not one flow (verified). Shot 1 is the default "applied directly" mode. Shot 2 is a different request. A held AI request, "Use an AI-suggested subject line", lists its three options inside Approvals as a pick-one and the editor then has no "Use this", so the two can never be the same suggestion. Do not draw the caution line "Suggestions can be wrong…" or the words "Example provider": they exist only in the design canvases. The mock's own text is "Mock subject 1 — Mock preheader 1"; the film draws believable text and says so in the shot notes, but keeps `mock-1` in the provenance line. Preparation: publish "Subject & preheader" as version 1 in Settings once (a fresh reset has none and the button then reports "No published prompt"); plan a draft send, then run `backend/scripts/seed_pending_actions.py` on the demo database. **The alternative for shot 2,** if the film should show the AI request in Approvals: set the task's Output to "held for review", press "Suggest with AI", and pick one of the three options in Approvals, "Approve and run"; the chosen subject is written onto the variant. Both run for real.

### S09 · 1:50 to 2:00 · The send is planned first
- **See.** The Send screen as the app has it. Step 1, what goes out (the frozen preview and the subject). Step 2, send a test. Step 3, plan the send: the name of the send (pre-filled with the campaign's name), the audience group with its line "123 of 123 in this group can be reached on email now", the provider, "Plan the send". After planning, step 3 is replaced by step 4: "Goes to 123 recipients as of now, through mock (nothing is sent)." and the docked button "Send to 123". The cursor presses it.
- **Source.** Live `11-send.jpg`; render `25-send-plan.png`, `26-send-ready.png`. The real wording of every step is in [[PREPRODUCTION-CHECKS]], section 4.
- **Text.** None beyond the app's labels.
- **A.** Before anything leaves, the system plans the send, shows how many people it can reach, and freezes what they will get.
- **B.** Before anything leaves, the system plans the send, shows me how many people it can reach, and freezes what they will get.
- **Sound.** A tick per step; a deeper hit on the final press.
- **Evidence.** [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]], [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]. (ADR-163 and ADR-191 leave this scene: they carried the left-out and unsubscribe claims.)
- **Check.** **Unsubscription is not built yet (Diede, 2026-10-17), so this scene, in picture, caption and voice, says nothing about consent, suppression, opt-out, unsubscribing or readers left out.** The demo also has no exclusions (verified: all five sent campaigns record Excluded 0 and every audience group reads "N of N can be reached"), and the one reader who unsubscribed is still reachable because of the seed's row order, so there is nothing to draw even if the claim were wanted. The first narration, "… leaves out whoever said no, and tells you who and why", does **not** come back when the demo seed is fixed: it comes back only once unsubscription is built ([[TRAILER-BRIEF]], section 16, decision 8). With the mock provider the button reads "Send to N", never "Send real email". The 123 is the audience group's size, the same group as the hook, read after the final reset; do not imply it is the same send as Familienherbst.

### S10 · 2:00 to 2:12 · Exactly what each person got · HERO
- **See.** Deliveries. A send is chosen; its recipients table; one reader is opened and "As sent" shows the subject, the preheader and the message with its pieces of content. A cut of two seconds to the slot's page, "Reasons given": one line for that reader's pick, as the app writes it (`recipient_top_score: recipient=127, … = 268.3 (tied at score … ordered randomly)`). A last three seconds: a stranded send with a flag and a "Release" button, a person presses it.
- **Source.** Live `31-as-sent.jpg`, `33-slot-detail.jpg`; render `30-delivery-stranded.png` and `31-delivery-as-sent.png`.
- **Text.** Under the message: "The content this reader received."
- **A.** Afterwards, open any reader's message: the content they received, and the reason each piece was picked.
- **B.** Afterwards I can open any reader's message: the content they received, and the reason each piece was picked.
- **Sound.** The pulse thins to the piano alone; one low tick on "Release".
- **Evidence.** [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]], [[ADR-086 — Decision Slots Fail Gracefully]], [[ADR-192 — A Stranded Send Is Flagged, and a Person Releases It]].
- **Check.** Capture "As sent" before the first file drop: after a fresh reset the two template notices are gone, and any change in `storage/modules/email/` brings them back (verified; S10 comes before S13, so the story order is right). Say "content", never "byte for byte": the live screen warns that the layout is today's. The envelope table has a `list_unsubscribe` row whose link reads `http://localhost:8000/unsubscribe/<token>`: either crop that row out or redraw the link with a neutral address, and never speak of it (unsubscription is not built yet, see S09). The reasons are verified; never say "the best pick", because most reasons end "tied … ordered randomly". The narration no longer mentions readers left out: the demo has none (see S09). The stranded send is only drawn in the render; the demo cannot produce it, so mark the frame as a drawing in the shot notes. Never "the snapshot stores the final HTML".

### S11 · 2:12 to 2:20 · The signal comes back
- **See.** The campaign's Results card: the delivery table, then the engagement table with clicks, unique clickers and the click rate (the Unsubscribes column is cropped out). A fading curve draws beside it. Back in the slot, the next pick shifts by one row.
- **Source.** Render `20-campaigns.png` for the layout. The figures, verified identical after two resets, campaign Familienherbst: Recipients 123, Sent 123, Delivered 122, Failed 0, Excluded 0, Bounced 1, Complaints 0; Clicks 25, Unique clickers 17, Click rate 13.8 %, Unsubscribes 1.
- **Text.** "Clicks count. They fade."
- **A.** Their clicks come back as signals that fade with time, and shape the next pick.
- **B.** Their clicks come back as signals that fade with time, and shape the next pick.
- **Sound.** A rising line of three soft ticks, then the music drops away.
- **Evidence.** [[ADR-110 — Insight Layer Transforms Events Into Signals]], [[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]], [[ADR-112 — Signals Use Time-Based Decay]], [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]].
- **Check.** Clicks only; the app itself says opens are not counted. Never show or say an open rate. Delivered is 122, not 123. The decay curve uses the real values (`backend/app/insight/signals.py`, shown in Settings): a contribution's weight falls as `weight × 0.5 ^ (age in days ÷ half-life)`, with half-lives of click 45, manual 180, unsubscribe 120 and open 45 days, and weights click 5, manual 40, unsubscribe −50, open 0. Unsubscription is not built yet (Diede, 2026-10-17): crop out the Unsubscribes column and the card's footnote (it speaks of unsubscribes and sits oddly with the table's count of one), and draw the click curve only; the unsubscribe weight and half-life are in the code but the film never mentions them.

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
- **See.** In the editor, two new files appear beside `hero.json` and `hero.mjml`: `storage/modules/email/quote.json` and `quote.mjml`. In the terminal `npm run build:modules` runs (0.58 s), writes `quote.html` and ends "11 compiled blocks are current"; a low hit as the files land. Cut to the manager's variant editor and the page is reloaded (a beat: the reload is part of the story). "Add a module" opens; "Quote" is in the list; it is added; its fields appear, "Text" with a German quotation typed in and "Heading" left empty, and it renders in the stack and in the preview.
- **Source.** `storage/modules/email/hero.json` for the manifest shape; live `05-variant-editor.jpg` for the "Add a module" control.
- **Text.** The file names, as typed.
- **A.** A new content block: a manifest and a template. It appears in the editor.
- **B.** A new content block: a manifest and a template. It appears in the editor.
- **Sound.** One low hit on the files landing; a tick on the manager's side.
- **Evidence.** [[ADR-131 — Email Module Templates Use MJML as Source Format]] (and its addendum), [[ADR-198 — The Email Block Set Is Seven Blocks, Square Images and Text Links]]; the module registry rescans when the folder changes.
- **Check.** Done for real on scratch; the exact files are in [[PREPRODUCTION-CHECKS]], appendix A and B. **After the build the page must be reloaded:** without a reload the open editor lists the block by its file name, `quote`, and its panel says "This channel has no module called quote, so it cannot be edited or rendered", which a viewer would take for a failure. The manifest names fields already in `storage/fields.json` (`text` required, `heading` optional); a quote's attribution has no field of its own, so it would show as "Heading" with the Headline block's note. **Leave "Heading" empty in the frame** (it is optional) so the mislabel never shows, and do not caption the quote with an author; adding one more file (`storage/fields.json`) to the scene stays open as an alternative ([[TRAILER-BRIEF]], section 16, decision 9). After a variant is edited the editor shows "You are editing this variant … Unblock" and, until the text is typed, "1 required field empty": draw them as they are or crop them out, but do not invent a cleaner editor. A manifest saved before its `.html` logs `Manifest quote.json has no matching .html file — skipping…`; the scene may show that line. "A manifest and a template" is the narration: the template is the `.mjml`, built into the `.html`, so three files appear and the build runs; never say "two files". Every earlier "As sent" now carries the templates-changed notice: S10 is captured before this scene.

### S14 · 2:40 to 2:52 · Drop a decision strategy
- **See.** `backend/app/decision/strategies/recency_boost.py`, a class with `meta` and `rank`, shaped like `top_score.py`; the first lines of the real `top_score.py` sit beside it. The file is saved. Cut to the slot settings in the manager's editor, after a page reload: the Strategy list shows the labels "Recency boost", "Recipient Top Score" and "Top Score"; "Recency boost" is chosen and the settings show its extra field "recency weight".
- **Source.** `backend/app/decision/strategies/top_score.py` for the shape; render `23-editor-slot.png` for the settings group.
- **Text.** The file name, as typed.
- **A.** A new way to decide who sees what: one file, written by whoever knows the data.
- **B.** A new way to decide who sees what: one file, written by whoever knows the data.
- **Sound.** One low hit as the file saves.
- **Evidence.** The strategy registry; `docs/playbook-strategy.md` §4 (a BI team contributes a strategy as a file).
- **Check.** Done for real on scratch ([[PREPRODUCTION-CHECKS]], appendix C). The file must declare the slot's settings keys, `content_score_weight` and `preference_score_weight`, plus its own `recency_weight` (the 108-line final version): the first, 71-line version declared none and choosing it failed on every demo slot with "strategy_config has key(s) not declared by this strategy". The list entry needs a page reload. On the demo a recency bonus has no visible effect, because every record was written by the reset a moment ago: show the file and the list entry, never a result.

### S15 · 2:52 to 3:04 · Drop an AI task
- **See.** `backend/app/ai/tasks/…py`: the `META` and a short default prompt, the docstring's line "the prompt itself is not here" visible. Cut to Settings, AI prompts: the new record is in the list (it appears when the window regains focus or Settings is re-entered, no reload); the manager opens it, sees the pre-filled prompt and "Publish as version 1", and rewrites the prompt text in the app.
- **Source.** `backend/app/ai/tasks/subject_preheader.py` for the shape; render `44-settings-ai-prompts.png` and live `41-ai-prompts.jpg` for the screen.
- **Text.** The file name, as typed.
- **A.** A new AI task. The developer defines what it may read and return; the wording of the prompt belongs to the manager.
- **B.** A new AI task. The developer decides what it may read and return. The wording of the prompt stays with the manager.
- **Sound.** One low hit on the save; a tick on the manager's side.
- **Evidence.** [[ADR-140 — AI Capability Layer]] §4, [[ADR-141 — In-App Assistive AI Actions]], [[ADR-143 — AI-Assisted Development Boundary]].
- **Check.** Done for real on scratch ([[PREPRODUCTION-CHECKS]], appendix D, a 49-line `headline_polish.py`). Show the entry appearing, not the task running: no screen runs this task. No restart is needed. The detail page's Model select lists vendor model names: crop it or draw around it.

### S16 · 3:04 to 3:20 · Swap the delivery provider · T
- **See.** `backend/app/delivery/providers/` with `base.py`, `mock.py`, `resend.py`; a new `example_mail.py` is added beside them; it declares `channels = frozenset({"email"})` and `reaches_real_inboxes = False`. `factory.py` opens and four edits are made: the import, an `elif` branch, a label line and a tuple entry (six lines in four places). The terminal shows the server reloading, 1.4 s. Cut to the manager's send step, with the window back in focus: the picker lists "mock (nothing is sent)", "resend (real)" and "example_mail (nothing is sent)".
- **Source.** `backend/app/delivery/providers/factory.py` and `resend.py` for the real shape; live `11-send.jpg` for the picker.
- **Text.** "A file. A few lines. A reload."
- **A.** Even the delivery provider is a part, not a foundation. A file and a few lines, and the company can change who sends, without touching a single campaign.
- **B.** Even the delivery provider is a part, not a foundation. A file and a few lines, and the company changes who sends, without touching a single campaign.
- **Sound.** Two low hits (the file, then the factory); the pulse swells into the next act.
- **Evidence.** [[ADR-100 — Provider Layer as Send and Feedback Adapter]], [[ADR-101 — Provider Capabilities Are Explicit]], [[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]].
- **Check.** Done for real on scratch ([[PREPRODUCTION-CHECKS]], appendix E and F). Say "a file and a few lines", never "a file". The restart comes only from the `factory.py` edit; a new file alone restarts nothing. The picker updates on refocus, no reload. The provider must declare the channels it carries (a push variant does not offer it) and, because `reaches_real_inboxes` defaults to True, say False if the adapter is not real. Do not name a real vendor other than Resend (the repo's own worked example). Do not quote `docs/how-to-swap-send-provider.md`.

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
