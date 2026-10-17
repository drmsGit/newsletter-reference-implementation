---
type: reference
status: draft
created: 2026-10-17
---

# Trailer pre-production checks: results

The checks of [[TRAILER-BRIEF]] section 15, run on 2026-10-17, read against [[STORYBOARD]]. Nothing was built for the film: no frame, no animation, no video. This file records what the running demo does, so that the later build draws what is true.

**Every result below is marked verified or not verified.** Verified means it was done and seen on the running scratch app or in its database, not only read from code. Where a result is a reading of code, it says so.

**What this file does not do.** It does not edit `TRAILER-BRIEF.md` or `STORYBOARD.md`. The changes those two need are proposed in section 8.

## 0. How the checks were run

- **A scratch database, not the development one.** `trailer_scratch` was created on the existing development Postgres container and dropped again at the end. The one setting that picks a database is the environment variable `DATABASE_URL` (`backend/app/database.py`); it was set inline for the scratch processes only, never written to a file. The demo reset refuses any database whose name contains `_test`, so the name avoids it. The real `app` database was not touched.
- **Own servers, own ports.** A scratch api on :8100 and a scratch client on :5273, started from a throwaway git worktree. The real api (:8000) and client (:5173) were left alone. The client's dev proxy is hard-coded to :8000, so `frontend/vite.config.ts` was edited in the worktree for the scratch run and reverted afterwards.
- **No `.env`.** The worktree has none, and none was read. `INITIAL_ADMIN_EMAIL` was set inline to a scratch address. Mock provider only, no Resend. The send cap was never changed (a fresh scratch database starts at the default).
- **Sign-in as the dev flow intends.** Code requested in the app, read from the api log, typed in.
- **A cookie trap worth knowing.** Browser cookies do not separate by port, so a sign-in on `localhost:5273` shares its cookie with the real app on `localhost:5173`. The scratch session was silently signed out once, and a real dev session in the same browser pane may have been signed out by the scratch sign-in at about 18:00. The scratch app was then used on `http://[::1]:5273/manager/`, a different cookie host. Whoever captures frames next should do the same, or use a separate browser profile.
- **A throwaway worktree.** The four drops (section 5) were made in it, uncommitted, and removed afterwards. Exact copies of every dropped file are in the shared notes folder under `preproduction-drops/`, and in the appendix below.

| What | How long |
|---|---|
| Demo reset (twice) | about 51 s wall clock each, 27 s of CPU |
| `npm run build:modules` for one new block | 0.58 s |
| The api restarting after an edit to an existing `.py` file | 1.4 s measured; a few seconds at most in the other runs |

## 1. The demo, reset on scratch: every number the film uses

**Result: verified, twice.** The reset was run twice on the scratch database. The film's numbers were the same both times.

### 1.1 The hook (S01)

| Number | Where the app shows it | After reset 1 | After reset 2 |
|---|---|---|---|
| 123 readers | Deliveries row `sent · 123 / 0 / 0`, campaign Familienherbst; Decision slot detail "Distinct recipients" | 123 | 123 |
| 369 picks | Decision slots list row "369 picks"; slot detail "Picks made" | 369 | 369 |
| 15 distinct content | Slot detail "Distinct content"; campaign page, Decision slots table | 15 | 15 |

The two rows S01 names read exactly as the storyboard says. Deliveries: `Familienherbst / Familienherbst / Deutsch / sent · 123 / 0 / 0 / 8.10.2026, 08:30:00`. Decision slots: `Für Sie ausgewählt / Familienherbst / Deutsch / recipient_top_score / 369 picks`.

**What is stable and what is not.** The three numbers, the score range (168.79 / 425.33 / 794.05), the readers and the results all came out identical twice. The individual picks did not: `recipient_top_score` shuffles candidates that tie on score (`random.shuffle`, `backend/app/decision/strategies/recipient_top_score.py`), and many do tie. Across the two resets only 8 of the 123 readers kept the same ordered picks, and 19 the same set. So 369 and 15 are safe to quote, but any frame that shows which content a named reader got must be read after the final reset, and the reset must not be run again afterwards.

**One more thing the slot page tells, which the film must not contradict.** The picks are concentrated: 101 of the 123 readers get both "Augsburg: Naturheft für Kinder am 15. Mai" and "Kinderregenjacke für 49 Euro" (27.4 % of all picks each), and differ in the third pick. The personalisation is real, but it is mostly in the third pick and in the minority of readers (section 2).

**Word for the numbers.** The reset script's own printout says "123 delivered". The app says Recipients 123, Sent 123, **Delivered 122**, Bounced 1. The hook may say 123 readers or 123 recipients. It must not say "123 delivered".

### 1.2 The results (S11), Familienherbst, campaign page, Results card

Identical after both resets:

| Delivery table | | Engagement table | |
|---|---|---|---|
| Recipients | 123 | Clicks | 25 |
| Sent | 123 | Unique clickers | 17 |
| Delivered | 122 | Click rate | 13.8 % |
| Failed | 0 | Unsubscribes | 1 |
| Excluded | 0 | | |
| Bounced | 1 | | |
| Complaints | 0 | | |

The card's own footnote, as it reads: "Counted per delivery. Click rate is unique clickers over sent. Opens are not counted. Unsubscribes made before 12.10.2026 are not counted." The footnote and the count of 1 sit oddly together (the one unsubscribe is dated 11 October in the seed). The app shows both; the film should show the table and leave the footnote out of focus rather than explain it.

The decay values S11 wants ("read them from the code before drawing") are in the code and in the Settings read (`GET /settings`, signals block; `backend/app/insight/signals.py`): a contribution's weight falls as `weight × 0.5 ^ (age in days ÷ half-life)`, with half-lives in days of click 45, manual 180, unsubscribe 120, open 45, and weights click 5, manual 40, unsubscribe −50, open 0. Opens carry weight 0, which agrees with "opens are not counted".

### 1.3 The counts excluded for consent and suppression (S09)

**Result: verified, and the finding is that there are none.** In the reset demo no one is excluded anywhere:

- All five sent campaigns record Excluded 0.
- The Send screen's reachability line, for each of the three audience groups, reads "N of N in this group can be reached on email now": 162 of 162 (Wintersport), 178 of 178 (Wandern), 123 of 123 (Familie & Kinder).
- Planning a send for the draft campaign Reparaturwoche on the Familie & Kinder group gave "Goes to 123 recipients", and it fired as 123 sent, 0 excluded.

So S09's line "who was left out for consent and who for suppression" cannot be drawn from the demo. What the live app has instead is the single reachability line above and, after a send, the Delivery detail facts "Excluded" and "Excluded: <stage>" (one row per stage, present only when a stage excluded someone). See section 8, S09.

**A related demo defect, found on the way.** The one reader who unsubscribed from Familienherbst (a different reader each reset: #422 the first time, #533 the second) is not excluded from the next send. The seed writes the unsubscribe dated 2026-10-11 and the same reader's demo opt-in at reset time, so the later opt-in wins and the reader is reachable again. The Reparaturwoche send did go to that reader. The demo therefore shows an unsubscribe that has no effect, which is the opposite of what S09 is about. It is not a defect of the product's consent logic; it is the order of two rows in the demo seed.

### 1.4 "As sent" and the stale-template notices (S10)

**Result: verified.** After a fresh reset the notices are gone. For the executions read, `templates_match` and `hash_matches` are both true, and the screen shows no notice.

**But they come back by themselves.** The app decides `templates_match` by hashing every file in `storage/modules/email/` (names and bytes; `backend/app/rendering/frame.py`, `templates_fingerprint`). Adding or changing any file in that folder flips it for every message already sent. After the content-block drop in section 5, every earlier "As sent" read `templates_match: false`, which is the notice "The templates have changed since this was sent. The content below is exactly what was sent; the layout is today's." That is the likely reason the earlier captures carried notices: the dev folder had been edited after the sends. (A drop of a new block flips only this one; an edit of an existing template would flip the screen's second notice, `hash_matches`, too.) Any new capture must be taken before a drop, and S10 comes before S13 in the film, so the order of the story is already right.

**What stays.** The unsubscribe link in the envelope still reads `http://localhost:8000/unsubscribe/<token>` (`PUBLIC_BASE_URL` is unset, so it falls back to the api's development address; the port is 8000 even though the scratch api ran on 8100). The film redraws it with a neutral address, as the brief already says.

## 2. Three readers who really get different picks (S07)

**Result: verified.** Three readers whose three picks do not overlap at all, in both resets:

| Reader | Address | Picks in the Familienherbst email (the module headlines the email shows, German) | Theme |
|---|---|---|---|
| **A: Lea Huber (#32)** | lea.huber.32@example.com | Reset 2: "Am 15. Mai wird gezeichnet", "49 Euro und Platz für eine Schicht", "Regenhose: einmal tief in die Hocke gehen". Reset 1: the same first two, then "Am 21. November planen Kinder mit" | Family and children |
| **B: Michael Zimmermann (#127)** | michael.zimmermann.127@example.com | Reset 2: "Spuren und Bilder besprechen", "49 Euro für ruhige Beobachtungen", "Achtfach, aber nicht unruhig". Reset 1: "Eine Spur ist noch keine Art", "Achtfach, aber nicht unruhig", "Spuren und Bilder besprechen" | Animal watching: tracks, binoculars, tripod |
| **C: Peter Müller (#330)** | peter.mueller.330@example.com | Reset 2: "Am 21. November planen Kinder mit", "Was ist heute aufgefallen?", "Kleine Sitzmatte, weniger Pausentheater". Reset 1: "Kleine Sitzmatte, weniger Pausentheater", "Am 29. Mai planen Familien", "44 Euro für ein Paar" | Family hiking |

All three are German-language, active, with a consented email address. They are the same people in both resets (ids and addresses are stable); **their item-level picks changed between the resets** (Lea's third pick; Michael's and Peter's order and partly their content). The themes did not. The three sets stayed pairwise disjoint both times. Re-read the headlines after the final reset and caption those.

How it was checked:

- Reset 1, in the app: the Preview sheet for Familienherbst took `lea.huber.32@example.com` through its search field. The emails of all three readers were read from the render endpoint the sheet uses, and each one differed. The slot's set was not looked at on screen for each reader in this run.
- Reset 2: the picks in the database, the render endpoint for all three, and the frozen "As sent" of all three agree with each other. For all three `hash_matches` is true.

**How the real Preview behaves, which S07 must draw as it is.**

- "Preview for a recipient (optional)" is a **search field with a result list**: type part of an address (`lea.huber.32`), a button with the full address appears, press it. The sheet then says "For lea.huber.32@example.com." with a button back to the generic preview. It is not a chip and not a plain text field (the brief already says "draw the field"; the extra step is the result button).
- A slot module shows its picks as **one module that lays out up to three pieces of content one after the other**, not three modules. The other modules of the Familienherbst email are the same for every reader: Hero Banner "Vier Dinge im Wald finden", Editorial, Image Left "39 Euro für den ersten Blick", Image Right "Ein Heft für Fundskizzen". Only the tail differs. The triptych will show a shared email with three different tails.
- With no recipient chosen, the slot module shows nothing, and the left list says: "Image Left · picks per recipient — name a recipient above to see their pick".
- What the email shows for a pick is the module's headline field ("Am 15. Mai wird gezeichnet"), not the record's title ("Augsburg: Naturheft für Kinder am 15. Mai"). The English captions translate what the email says.
- The Preview reads the stored pick set; it does not run the slot again, so it shows what was sent. A new send re-runs the slot and, because of the random ties, may pick differently.

**"From content a person approved" (S07 Check).** The app does not use the word. The slot detail says "34 active content records in categories #14, #6, #24, #7". The rule behind it (`candidate_query`, `backend/app/decision/strategies/base.py`) is: status active, **machine ready**, marked ready for the slot's channel, and a latest published version that fills the fields the slot's module needs. The true short form is "content a person has marked ready and published".

**"Every pick has a reason."** True. The reason is shown on the slot page ("Reasons given") and recorded per pick. It reads, for example: `recipient_top_score: recipient=127, category_ids=[14, 6, 24, 7], content_score=9×1 + preference_score=25.9×10 = 268.3 (tied at score 268.3 between 4 candidates, ordered randomly)`. Most picks carry the "tied … ordered randomly" clause. The film may say "every pick has a reason"; it must not say the pick is "the best one".

## 3. Approvals: seeding, and what makes "Use an AI-suggested subject line"

**Result: verified.** The seed script was run against scratch. The AI request was produced for real.

### 3.1 What `seed_pending_actions.py` does

It raises requests of one kind only: **"Send a prepared campaign"** (`send.fire_send_instance`), from a named demo integration, **Acme Agency (demo)**. It cannot produce the AI request. It needs a planned draft send to make an approvable request; after a reset there is none, so one was planned first in the app (campaign Reparaturwoche, mock provider). With that, the seed made four requests:

| Request | State | What it shows |
|---|---|---|
| Send "…Scratch plan family" (#6) | waiting, approvable | The one to press |
| Send "Familienherbst" (#5) | waiting, "already sent" warning | Approving it is refused |
| Send "Hüttensaison-Finale" (#4) | rejected | Rejected by the first active admin, with a reason |
| Send "Herbstauftakt" (#3) | expired | Lapsed for real |

The detail page of the approvable one reads: title "Send a prepared campaign"; the line "Before you decide: The audience is re-resolved at send time, so the number above is what matches now — not necessarily what will be mailed."; a facts block (Status, Requested by integration, Requested, Expires, Send, Provider, From, Audience "123 planned recipient(s)"); then "Decide" with a Reason box and **Approve and run** / **Reject**. Pressing Approve and run: the request left the waiting list at once, went through "executing" to "approved", and the send finished as 123 sent through the mock within seconds.

Two small things for the frames: the list's date column shows the **deadline** (`decided_at`, else `expires_at`), not the request time, and the script's closing hint still says `/ui/approvals` (the old Jinja path; the manager is under `/manager/approvals`).

### 3.2 What produces "Use an AI-suggested subject line"

The request's label in the app is **"Use an AI-suggested subject line"** (the storyboard's "Apply an AI-suggested subject" is the code's file name). It is not a plain path. It exists only when all three of these are true, each a step in Settings or the editor:

1. **A prompt has been published** for the task Subject & preheader (Settings, AI prompts, "Publish as version 1"; the default text is pre-filled). On a fresh reset none is published. "Suggest with AI" then answers "No published prompt for this task — publish one in Settings." and the run is `blocked`.
2. **The task's Output is set to "held for review"** (same screen, "Output of Subject & preheader"). The default is "applied directly".
3. **"Suggest with AI" is pressed** in the variant editor. In held mode the request is raised by that press (requested by the signed-in user; the action lets the requester decide, `requester_may_decide`).

What the two modes look like:

- **Applied directly (the default):** three options appear in the editor, each with a **Use this** button. No approval exists.
- **Held for review:** the same three options are listed in the editor **without** "Use this", under the line "These options wait for approval; one is picked there. Open it in Approvals". The request is in Approvals: title "Use an AI-suggested subject line"; facts (Status, Requested by, Requested, Expires in eight hours, Variant, Model, Cost "367 in / 36 out tokens", Prompt version "#1"); then "Decide, Choose one" with three radio options, a Reason box, **Approve and run**, **Reject**. Choosing option 2 and pressing Approve and run wrote the subject and preheader of option 2 onto the variant.

**So S08's two halves, as drawn, are two different modes.** Shot (1), "three suggested subjects each with a Use this button", is the applied-directly mode. Shot (2), the request waiting in Approvals, is either the held AI request (where the options are chosen in Approvals, not in the editor) or the "Send a prepared campaign" request. There is no flow in which the editor shows "Use this" and Approvals also holds the same suggestion.

**Things in S08 that do not exist in the live app.** The caution line "Suggestions can be wrong. Check the subject before you use it." and the provenance wording "Example provider" appear only in the design canvases (`docs/design/canvas-v2/`), not in the app's code. The real provenance line under the options is `403 tokens · mock-1 · prompt v1`. The mock's options read "Mock subject 1 — Mock preheader 1", "Mock subject 2 — …", "Mock subject 3 — …". The film must either show that placeholder text as it is, or mark a drawn frame with believable German as a drawing.

**A defect found on the way.** In held mode, a run that was `blocked` (no published prompt) still raised a request in Approvals, with nothing to choose ("No usable options could be read from the reply"). One was created before the prompt was published and was left waiting in the scratch database.

**Which request to use.** Both are real and run. The recommendation is in section 8, S08.

## 4. The Send screen as it is

Recorded here because S09 is drawn from it. The live Send screen for a draft variant: **1. What goes out** (the frozen preview and the subject); **2. Send a test (optional)** (address, "Show it as", provider, "Send a test"; "Not a delivery: no unsubscribe link, nothing counted or stored."); **3. Plan the send** (Name of the send, Audience group with the reachability line, Provider, When "When I send it" or "At a time", the checkbox "Don't send to someone who would get no content record", "Plan the send"). After planning, step 3 is replaced by **4. Send**: "Goes to 123 recipients as of now, through mock (nothing is sent)." and the button **Send to 123**, with "The delivery", "The campaign's results" and "Plan another send" below. The provider picker labels are "mock (nothing is sent)" and "resend (real)". The name field is pre-filled with the campaign's name.

## 5. The four developer drops, performed for real

**Result: verified for all four,** on a throwaway worktree against the scratch app. Exact file contents are in the appendix. For each: what was written, what the console said, how long it took, and **what the manager app shows without a restart or a refresh**.

### Summary

| Drop | Files | Server restart? | Shows in the manager app |
|---|---|---|---|
| Content block `quote` (MJML route) | `quote.json`, `quote.mjml`, `quote.html` (built) | No | In the open editor **not** until its composition is reloaded, and then by raw name; label and fields need a **page reload** |
| Content block, hand-written (no MJML) | `pull.json`, `pull.html` | No | Listed and accepted by the api; screen behaviour as above (not exercised on screen) |
| Decision strategy `recency_boost` | `recency_boost.py` | Not for a new file | In the open editor **not** until a **page reload**; choosing it fails on every demo slot unless the file declares the slot's settings keys |
| AI task `headline_polish` | `headline_polish.py` | Not for a new file | Appears in Settings, AI prompts **on refocus, or on re-entering Settings**, no reload |
| Delivery provider `example_mail` | `example_mail.py` plus 4 edits in `factory.py` | **Yes, automatic** (from the factory edit) | Appears in the send picker **on refocus**, no reload |

### 5.0 What decides each result (read from code, then confirmed)

- **The server finds new files by rescanning, and does not restart for them.** The three registries (modules, strategies, AI tasks) compare the folder's modification time on each request and rescan when it changed (`registry.py` of each). Uvicorn's `--reload` watches `.py` files, but a **new** file is registered silently: only a change to an **existing** `.py` file restarts it. So a dropped file never restarts the server, while an edit to `factory.py` does.
- **The manager app caches some lists forever and some not.** The module manifests and the strategy list are fetched with `staleTime: Infinity` ("until a page reload or a brand switch", `frontend/src/api/resources.ts`). The settings read, which carries the AI task list and the provider list, is not cached that way and refetches when the window regains focus and when a screen is entered. That is the whole difference between the rows above.

### 5.1 A content block: `quote`

Written, in `storage/modules/email/`: `quote.json` (manifest) and `quote.mjml` (source); then `npm run build:modules` in `frontend/` made `quote.html`. The manifest names two fields already in `storage/fields.json`: `text` (required) and `heading` (optional). A field not in that file would have got the block skipped.

Console, in order:

```
# before the .html existed, in the api log:
WARNING:app.modules.registry:Manifest quote.json has no matching .html file — skipping. Declare "has_template": false if this module renders without one.

$ npm run build:modules
> manager-client@0.0.0 build:modules
> node scripts/build-modules.mjs

Wrote 11 files to storage/modules/email.

$ npm run build:modules -- --check
11 compiled blocks are current.
```

Time: 0.58 s for the build. The compiled output of the existing blocks did not change (git showed only `quote.*` as new), so the CI check stays green.

What the manager sees, with the editor open and no reload:

1. The api lists `quote` on the next request (12 modules instead of 11; a restarted server logs `channels: email (12 modules, …)`).
2. **The open editor's "Add a module" does not show it** until the editor reloads its composition (leaving the editor and coming back is enough). It then appears under its **file name, `quote`**, not its label, because the list of ids comes fresh from the server while the labels come from the cached manifests.
3. Adding it works, but the module's panel reads **"This channel has no module called quote, so it cannot be edited or rendered."** and the stack shows `quote · Typed in`. That message is wrong, and a viewer of the film would take it for a failure.
4. After a **page reload**: the stack and the picker show the label ("Quote"); the panel shows the fields "Text (required)" with the markdown hint, and "Heading" with the note "The Headline block's H2, typed into the block (ADR-198)." Text typed in rendered in the preview (`.module-quote`).

So the honest sequence for S13 is: files, build, **reload the page**, then "Quote" in the list.

**A label problem for the film.** The attribution line of a quote has no field of its own in `fields.json`, so the block had to use `heading`, which the editor labels "Heading" with the Headline block's note. A properly labelled "Attribution" field would be a further edit (`storage/fields.json`), outside the "drop a block" story. Either show the block with "Heading", or add the field to the scene as a further file.

**Two files are possible.** A manifest and a hand-written `.html`, no MJML source and no build, was listed and accepted by the api (`pull.json`, `pull.html`; the CI check does not look at an `.html` without an `.mjml`). Rendering that block on screen was not exercised. So "a manifest and a template" is true for that route; the MJML route is three files and a build.

**Side effect to keep in mind.** The folder hash changed, so every previously sent message's "As sent" now carries the templates-changed notice (section 1.4).

### 5.2 A decision strategy: `recency_boost`

Written: `backend/app/decision/strategies/recency_boost.py`, shaped like `top_score.py` (a class with `meta` and `rank`, the same imports and helpers). The first version is 71 lines and declares **no** settings keys. The file was then edited once; that final version is 108 lines.

Console: **none for the new file.** The api log showed no restart and no message; the registry picked it up on the next request (`GET /decision/strategies` listed `recency_boost`, label "Recency boost"). For the edit of the existing file:

```
WARNING:  StatReload detected changes in 'app/decision/strategies/recency_boost.py'. Reloading...
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [52933]
INFO:main:channels: email (12 modules, max unbounded), push (1 modules, max 1)
INFO:main:auth: access control is enforced. Sign-in codes are written to THIS log (system mail provider is 'mock'), so read your code from here.
INFO:     Started server process [62102]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

It ran: called directly on scratch data it ranks, for Familienherbst and reader #32, three picks, with the recency bonus visible in the reason (`… + recency=20.0 = 622.7`).

What the manager sees:

1. The strategy list in the open editor does **not** change until a **page reload**. After the reload the Strategy select in the slot's settings lists "Recency boost", "Recipient Top Score", "Top Score" (labels, not the ids `top_score` and `recipient_top_score`).
2. **Choosing it failed on the demo slot with the first version:** "Not saved: strategy_config has key(s) not declared by this strategy: ['content_score_weight', 'preference_score_weight']. Allowed: (none — this strategy takes no keys here)". The editor's choice sends only the strategy name, the server validates the slot's **stored** settings against the new strategy, and every demo slot stores the two weights of `recipient_top_score`. Choosing `top_score` would fail the same way.
3. **The fix is in the file, not the app:** the final version declares the same two keys plus its own `recency_weight`. Then choosing it saved, the slot's settings showed the new "recency weight" field with no change to the app (the settings render from the strategy's declaration), and the slot's list row read `recency_boost`.

**On the demo data a recency strategy changes nothing you can see.** Every content record was written by the reset a moment ago, so all of them get the full bonus. The film shows the file and the list entry, as S14 already says, and must not imply an effect.

### 5.3 An AI task: `headline_polish`

Written: `backend/app/ai/tasks/headline_polish.py`, 49 lines: a docstring that says "The prompt itself is not here", `TASK_KEY`, `MAX_OUTPUT_TOKENS`, `DEFAULT_PROMPT`, a `META = TaskMeta(...)`, and a `gather_inputs` function. The registry only needs a module with a `META`. The docstring line S15 wants visible is present.

Console: none for the new file. No restart. `GET /settings` listed `headline_polish` among `ai_tasks` on the next request. (An edit of the existing file restarted the server, with the same lines as above.)

What the manager sees:

- The open Settings, AI prompts list did **not** update on its own, and **did** update, without a reload, as soon as the window regained focus, or on leaving and re-entering Settings. A later edit of the task's label showed the same way ("Headline polish" became "Headline polish (edited)" on refocus).
- The detail page of the new task is complete: description, a Model select, an Output select ("applied directly", "held for review"), the prompt text pre-filled with the default, and **Publish as version 1**. A manager can rewrite the prompt there and publish it. This is S15's second half, verified on screen.
- **Two cautions for the frame.** The Model select lists vendor model names ("claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"), which the brief's "no vendor names" rule excludes: crop it out or draw around it. And no screen runs this task, so the film shows the entry, never a run.

### 5.4 A delivery provider: `example_mail`

Written: `backend/app/delivery/providers/example_mail.py` (35 lines) beside `resend.py`, an adapter that sends nothing (it logs, as the mock does) and declares `channels = frozenset({"email"})`. Then four edits in `factory.py` (diff in the appendix: the import, an `elif` branch in `get_provider`, one line in `PROVIDER_LABELS`, and the entry in the tuple in `providers_for_channel`).

Console, for the `factory.py` edit (the new provider file alone caused nothing):

```
WARNING:  StatReload detected changes in 'app/delivery/providers/factory.py'. Reloading...
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [62815]
INFO:main:channels: email (12 modules, max unbounded), push (1 modules, max 1)
INFO:main:auth: access control is enforced. Sign-in codes are written to THIS log (system mail provider is 'mock'), so read your code from here.
INFO:     Started server process [63194]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Time: **1.4 s** from saving `factory.py` to a new server ready.

What the manager sees:

- The send step's provider picker did not change on its own. After the window regained focus (no reload) both pickers read "mock (nothing is sent)", "resend (real)", "**example_mail (nothing is sent)**". The label is the text added to `PROVIDER_LABELS`; without that line the picker would show the bare name.
- Because the file declares the channels it carries, the push variant's picker does not list it (`providers_for_channel("push")` gave `['mock']`), and asking for it on a push is refused: "provider 'example_mail' cannot deliver on the 'push' channel — it carries email".
- It works as an adapter: a call to `send` logged `example_mail send: to=… subject=… bytes=…` and returned success.
- **A default to know:** `reaches_real_inboxes` is True unless the adapter says otherwise, so a new adapter counts as real and a real send refuses an address that only works on this machine. The throwaway declares False. A frame that shows the class should show that line, or not present the adapter as a mock.
- **Nothing else needed editing.** A search for other places that name providers found the legacy Jinja form's default and a pydantic default of `"resend"`; neither blocks a new provider.

"A file and a few lines" is accurate: one new file, and six inserted lines across four places in `factory.py`.

## 6. The demo flaws of the brief's section 8, and which are still present

| Flaw (brief section 8) | Status after a fresh reset | Check |
|---|---|---|
| Unsubscribe link in "As sent" points at `http://localhost:8000/` | **Still present.** `http://localhost:8000/unsubscribe/<token>`, from an unset `PUBLIC_BASE_URL`. Redraw. | verified |
| "As sent" shows two stale-template notices | **Gone** on a fresh reset; **back** after any change in `storage/modules/email/` (any drop) | verified |
| The demo AI returns placeholder text | **Still present** ("Mock subject 1 — Mock preheader 1", `mock-1`); and on a fresh reset it does not run at all until a prompt is published | verified |
| Approvals is empty after a reset | **Still true.** Needs the seed script and a planned draft send first; the AI request needs the three steps of section 3.2 | verified |
| Sent campaigns still carry the status "draft" | **Still present** for all five sent campaigns, in the list and on the campaign page. The Deliveries list says "sent". Redraw as Sent. | verified |
| Drag handles in the preview sheet, the P-key hint chip on "Open preview", search boxes without server search | **Still not built.** The preview sheet has no drag handle; "Open preview" is a plain button; only Campaigns, Recipients and Audiences have a search box (Content, Deliveries, Decision slots, Approvals, Roles, Integrations have none). | verified |
| The category Graph is the weak screen | Not re-looked at (not in the film). The screen was still loading when checked. | not verified |
| Phone and tablet layouts, dark mode for screens 20 to 45 | Not checked; the brief says they are not designed. | not verified |

**New flaws found, not in the brief:**

- **An unsubscribe has no effect in the demo** (section 1.3).
- **No reader is excluded anywhere** (section 1.3).
- **The open editor lists a freshly dropped block by file name and says it "cannot be edited or rendered"** until the page is reloaded (section 5.1). That is a client defect (cached manifests), not a demo flaw, but any film that shows the live app will meet it.
- **Choosing a strategy that does not declare the slot's keys fails** (section 5.2).
- **A blocked AI run in held mode still raises an empty request** (section 3.2).
- **The dated figures in a capture are the reset's clock.** "Last pick" on the slot page and the "Updated" of the draft campaigns read the minute of the reset (here 17.10.2026), while the sent campaigns carry fixed dates (Familienherbst 8.10.2026, 08:30). Choose the reset date on purpose, and do not reset again after the captures.
- **Readers with language "en" get the German email.** Reader #4 (Daniel Turner, English) is among the 123 recipients of the German Familienherbst. None of the three triptych readers is affected.
- **The approvals list shows the deadline, not the request time, in its date column** (section 3.1).

## 7. The checks at a glance

| Check | Result |
|---|---|
| 1. Reset on scratch, re-read the numbers | **Verified.** 123, 369, 15 hold twice; the results hold twice; the consent and suppression counts are zero; the stale notices are gone, until a drop |
| 2. Three readers with different picks | **Verified.** Lea Huber (#32), Michael Zimmermann (#127), Peter Müller (#330) |
| 3. Seed Approvals, trace the AI request | **Verified.** The seed makes only "Send a prepared campaign" requests; the AI request needs a published prompt, "held for review", and a press of "Suggest with AI" |
| 4. The four drops for real | **Verified** (section 5) |
| 5. Re-capture "As sent" and list the flaws | **Verified** for what could be checked; two items not verified (Graph; phone, tablet and dark) |
| 6. The name on the end card | Not a check; not done |

Not checked, and not asked for in section 15: S06's override label and "Back to the catalogue value" line, S17's push frames (the reset does create the campaign "Testtag im Laden (Push)"), and the screens S18 uses. S17's own "re-capture" instruction stands. (S06's cue chips were seen: the stack shows "Record", "Slot" and "Typed in" beside each module, as the storyboard says.)

## 8. Changes the brief and storyboard need (proposed, not made)

Ordered by the scene they touch. "Brief" means [[TRAILER-BRIEF]], "SB" means [[STORYBOARD]].

**S01 (hook).** Keep 123, 369, 15; they are verified. Add to the check: say "readers" or "recipients", never "delivered" (the app says 122 delivered). Add: re-read after the final reset, and do not reset again after the captures.

**S07 (hero).**
- Name the three readers in the scene: Lea Huber (#32), Michael Zimmermann (#127), Peter Müller (#330); their picks must be re-read after the final reset (ids and themes are stable, items are not).
- Replace "From content a person approved" with "content a person marked ready and published", or with the app's "active content records". The word "approved" is not the app's.
- Replace "The live 'Preview for a recipient' is a text field, not a chip: draw the field" with: a search field; type part of the address; a result button; then "For <address>." and a way back to the generic preview.
- Say in the See line that the three picks sit in one slot module under a shared email, so the triptych shows one shared top and three different tails.
- Caption the headlines the email shows, not the records' titles.
- "Every pick has a reason": keep, and add "never 'the best pick'". The reason of most picks says "tied … ordered randomly".
- Add the honest limit in the shot notes: 101 of 123 readers share the first two picks.

**S08 (hero).** Rewrite the See and Check lines; the two halves are two modes.
- *Proposed sequence:* shot (1), the editor in the default **applied directly** mode: "Suggest with AI", three options with "Use this", the real provenance line `403 tokens · mock-1 · prompt v1`; shot (2), Approvals with the seeded **"Send a prepared campaign"** request from "Acme Agency (demo)": "Approve and run", and the request leaves the list. That keeps the narration ("AI can suggest and draft. A person decides what goes out. Even when a machine asks to send, someone has to say yes.") exactly true, with two requests the app really has.
- *The alternative,* if the film wants the AI request in Approvals: set the task to "held for review", press "Suggest with AI", and the request "Use an AI-suggested subject line" appears with the options **as a pick-one inside Approvals** (no "Use this" in the editor).
- *Preparation either way:* publish "Subject & preheader" as version 1 once; plan a draft send, then run `backend/scripts/seed_pending_actions.py` against the demo database. The demo is not ready for this scene straight after a reset.
- Delete the caution line "Suggestions can be wrong. Check the subject before you use it." and the provenance word "Example provider" from the See line: they exist only in the design canvases. If the film wants the caution line, it must be drawn and marked as a drawing.
- The request's label is "Use an AI-suggested subject line", and "Send a prepared campaign" for the other (not "Send a campaign").
- The mock's text is "Mock subject 1 — Mock preheader 1". Either show it, or draw believable German and mark the frame as a drawing.

**S09.** Remove the claim of a line saying who was left out for consent and suppression; the demo produces none. Either draw the line that exists, "123 of 123 in this group can be reached on email now", and say nothing of exclusions, or have the demo seed some opted-out and suppressed readers first (a demo-data change in the project, not in the film). Draw step 3 (the plan form) and step 4 ("Goes to 123 recipients as of now, through mock (nothing is sent)." and "Send to 123") as the live screen has them; step 3 is replaced by step 4 after planning, and the name field is pre-filled with the campaign's name.

**S10.** Keep: no notices on a fresh reset; keep the "redraw the unsubscribe link" instruction. Add: any change in `storage/modules/email/` brings the notices back, so capture before a drop (S10 precedes S13 in the film, so the story order is right).

**S11.** The figures are verified (section 1.2). Add: Delivered 122, not 123; and the decay values, half-lives in days of click 45, manual 180, unsubscribe 120, open 45 (weight 0).

**S13.** Rewrite the See and Check lines: **after the build, the page must be reloaded** before "Quote" appears with its label and fields; without a reload the editor lists it as `quote` and says it "cannot be edited or rendered". Say "a manifest and a template" only for the hand-written route (two files, no build); the MJML route is three files and a build (0.58 s). Note that a quote's attribution has only the field `heading` ("Heading", with the Headline block's note) unless a field is added to `storage/fields.json`. Add the console line a viewer could see when the manifest lands before its `.html`: `Manifest quote.json has no matching .html file — skipping…`.

**S14.** The Strategy list shows labels ("Recency boost", "Recipient Top Score", "Top Score"), not ids. Choosing a new strategy on the demo slot fails unless the file declares the slot's settings keys (`content_score_weight`, `preference_score_weight`): write the file that way (the 108 lines in the appendix), or drop the "it is chosen" beat. The list needs a page reload to show the new entry. A recency strategy shows no visible effect on the demo (every record is new); show the file and the entry only, as already written.

**S15.** The new task shows on refocus or on re-entering Settings, no reload. Show the detail page with its pre-filled prompt and "Publish as version 1". Crop or avoid the Model select (it lists vendor model names). The task cannot be run from any screen.

**S16.** The provider picker's entries are labels, not names: "mock (nothing is sent)", "resend (real)", and the new one as labelled in `PROVIDER_LABELS`. The restart comes **only** from the `factory.py` edit (a new file alone restarts nothing), with the console lines of section 5.4, 1.4 s. The picker updates on refocus. State the six inserted lines in four places, and that the file declares its channels (so a push does not offer it) and `reaches_real_inboxes`.

**Brief section 8, known flaws.** Update the bullet "As sent shows two notices": after a fresh reset they are gone, and any drop brings them back. Update "The demo AI is a mock": add that nothing runs until a prompt is published. Update "Approvals is empty after a reset": add the seed script's limits (section 3.1). Add the new flaws of section 6 that a frame can inherit: the ineffective unsubscribe, zero exclusions, the reset's clock on the dated fields.

**Brief section 11 (claim ledger).** The row "A dropped file is picked up…" and the row about the provider both say "Not run". They are now run, with the results of section 5 (the editor needs a reload for blocks and strategies; refocus is enough for AI tasks and providers; an edit of an existing `.py` file restarts the server, a new file does not).

**Brief section 12.** The table of the four drops should carry the "what the manager then sees" column as found: block, "after a page reload, not before"; strategy, "after a page reload, and only if the file declares the slot's settings keys"; AI task, "on refocus"; provider, "on refocus, after the automatic restart from the factory edit".

**Brief section 15.** Checks 1 to 5 can be marked done by this file. Check 6 (the name) is still open.

## 9. Follow-ups in the project, not in the film

These are real defects or gaps found while checking. None was changed here.

1. **Demo seed: make the unsubscribe stick and add excluded readers.** The seed writes the demo opt-in later than the unsubscribe, so the unsubscriber stays reachable; and nobody is opted out or suppressed, so the consent and suppression counts S09 is built on do not exist.
2. **A held AI run without a published prompt raises an empty request** (`backend/app/ai/orchestration.py`: the held request is raised after a `blocked` run).
3. **A freshly dropped module is offered under its file name and then reported as not existing** until a page reload, because the manifests are cached for ever while the module ids are not (`useModuleManifests`, `staleTime: Infinity`, against `accepted_module_types`).
4. **Choosing a different strategy on a slot with settings fails** unless the new strategy declares the same keys: the editor sends only the strategy name (`frontend/src/screens/SlotSettings.tsx`).
5. **`seed_pending_actions.py` closes with the stale path `/ui/approvals`.**

## 10. Decision of 2026-10-17: unsubscription is not built yet

Diede decided, after reading these results, that the film makes no claim about unsubscribing. That settles the question section 1.3 left open: the missing exclusions are not a demo gap to fill before filming, they are a feature that is not there yet. Applied to the committed files the same day:

- **[[STORYBOARD]]:** S09 loses ADR-163 and ADR-191 from its evidence and says outright that the scene never speaks of consent, suppression, opt-out, unsubscribing or readers left out (and that fixing the demo seed does not bring the first narration back); S10 crops or redraws the envelope's `list_unsubscribe` row and never speaks of it; S11 crops the Unsubscribes column and the card's footnote and draws the click curve only; S13 leaves the optional "Heading" field empty so the quote block's mislabel never shows, and notes the editor banners a frame will carry.
- **[[TRAILER-BRIEF]]:** the "See what it does" support no longer lists "who was left out and why"; the claim ledger row for the send becomes "planned first and frozen" with ADR-183 and ADR-005; a new "never say" bullet covers unsubscribing, opt-out and exclusion counts; section 16, decision 8 now reads as decided, decision 9 follows S13, and a new decision 10 records that the word "consent" in S03 and S18 stays for now and is open.
- **`storyboard.html`:** the seven changed rows of the visual board were patched to match the storyboard, row by row (it has no generator in the repository, so a later regeneration must start from the storyboard text).
- **[[VOICEOVER]]:** unchanged. The S09 and S10 lines of 2026-10-17 already say nothing about readers left out. S03 and S18 still say "consent" until decision 10 is made.

S14 needed no change: the committed scene already has the file declare the slot's two weights, the page reload, and "show the file and the list entry, never a result".

## Appendix: exact file contents of the drops

All of these are throwaway. They were created in a git worktree, uncommitted, and removed with it. Copies of every file, including the first version of the strategy, are in the shared notes folder under `preproduction-drops/`. The two labels were briefly edited during the refresh tests ("Quote" to "Quote (edited)", "Headline polish" to "Headline polish (edited)"); the contents below are the first-written ones.

### A. `storage/modules/email/quote.json`

```json
{
  "label": "Quote",
  "channel": "email",
  "description": "A short quotation, set apart, and who said it. Typed into the block.",
  "cms": false,
  "variables": [
    {
      "name": "text",
      "required": true
    },
    {
      "name": "heading",
      "required": false
    }
  ]
}
```

### B. `storage/modules/email/quote.mjml`

```xml
<mjml>
  <mj-head>
    <mj-include path="./_attributes.mjml" />
  </mj-head>
  <mj-body width="600px">
    <!-- Quote: a short quotation, set apart, and who said it. -->
    <mj-section>
      <mj-column border-left="4px solid {{ profile.colour_text or '#1a1a1a' }}" padding="0 12px 0 20px">
        <mj-text font-size="20px" line-height="1.4" padding="0 0 8px 0" css-class="module-quote">{{ text }}</mj-text>
        <mj-raw>{% if heading %}</mj-raw>
        <mj-text font-size="14px" padding="0">{{ heading }}</mj-text>
        <mj-raw>{% endif %}</mj-raw>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>
```

`quote.html` is generated from it by `npm run build:modules` (about 70 lines of MJML's table markup, starting with the line `{# Generated from quote.mjml by npm run build:modules (frontend/). Do not edit: edit the .mjml. #}`). The full text is in the notes folder.

### C. `backend/app/decision/strategies/recency_boost.py` (final version, 108 lines)

The first version (71 lines, in the notes folder) is the shape of `top_score.py` with the order changed to newest first, and declares **no** settings keys. The final version adds the three keys so that the demo slot accepts it:

```python
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionSlotDB
from app.content.service import get_latest_version_for_content
from app.decision.strategies.base import (
    ConfigField, DecisionStrategy, StrategyMeta, StrategyResult, best_per_record, candidate_query,
    sending_brand_id,
)
from app.insight.signals import operational_signals_for_recipient

DEFAULT_CONFIG = {
    "content_score_weight": 1,
    "preference_score_weight": 10,
    "recency_weight": 20,
}
RECENT_DAYS = 30


class RecencyBoostStrategy(DecisionStrategy):

    @property
    def meta(self) -> StrategyMeta:
        return StrategyMeta(
            name="recency_boost",
            label="Recency boost",
            description=(
                "Like Recipient Top Score, plus a bonus for content updated in "
                "the last 30 days: up to recency_weight points, falling to zero "
                "over the month."
            ),
            requires_recipient=True,
            candidate_filter_fields=[
                ConfigField(
                    name="category_ids",
                    type="list[int]",
                    default=[],
                    description="Restrict candidates to these category IDs (empty = all).",
                ),
            ],
            config_fields=[
                ConfigField(name="content_score_weight", type="number",
                            default=DEFAULT_CONFIG["content_score_weight"],
                            description="Weight applied to the content's own category score."),
                ConfigField(name="preference_score_weight", type="number",
                            default=DEFAULT_CONFIG["preference_score_weight"],
                            description="Weight applied to the recipient's preference score."),
                ConfigField(name="recency_weight", type="number",
                            default=DEFAULT_CONFIG["recency_weight"],
                            description="Most points a brand-new record can add."),
            ],
        )

    def rank(
        self,
        db: Session,
        slot: DecisionSlotDB,
        recipient_id: int | None = None,
        *,
        limit: int = 1,
        exclude: frozenset[int] = frozenset(),
    ) -> list[StrategyResult]:
        if recipient_id is None:
            return []

        candidate_filter = slot.candidate_filter or {}
        category_ids = candidate_filter.get("category_ids", [])
        brand_id = sending_brand_id(db, slot)
        config = {**DEFAULT_CONFIG, **(slot.strategy_config or {})}
        signals = operational_signals_for_recipient(db, recipient_id)
        now = datetime.now(timezone.utc)

        def bonus(updated_at) -> float:
            age_days = max((now - updated_at).total_seconds() / 86400, 0)
            return config["recency_weight"] * max(0.0, 1 - age_days / RECENT_DAYS)

        rows = [
            (record, content_score, signals[category_id])
            for (record, content_score, category_id) in candidate_query(db, slot, brand_id=brand_id).all()
            if category_id in signals
        ]
        rows.sort(
            key=lambda r: (r[1] * config["content_score_weight"]
                           + r[2] * config["preference_score_weight"]
                           + bonus(r[0].updated_at)),
            reverse=True,
        )

        picks = []
        for record, content_score, preference_score in best_per_record(
                rows, lambda row: row[0].id, exclude, limit):
            combined = (content_score * config["content_score_weight"]
                        + preference_score * config["preference_score_weight"]
                        + bonus(record.updated_at))
            latest_version = get_latest_version_for_content(
                db=db, content_record_id=record.id, brand_id=brand_id
            )
            picks.append(StrategyResult(
                content_record_id=record.id,
                content_version_id=latest_version.id if latest_version else None,
                score=float(combined),
                reason=(f"recency_boost: recipient={recipient_id}, category_ids={category_ids}, "
                        f"content_score={content_score}×{config['content_score_weight']} + "
                        f"preference_score={preference_score}×{config['preference_score_weight']} + "
                        f"recency={bonus(record.updated_at):.1f} = {combined:.1f}"),
            ))
        return picks
```

### D. `backend/app/ai/tasks/headline_polish.py` (49 lines)

```python
"""Task: suggest sharper headlines for one content record.

The dev-owned scaffold only: it declares what the task reads, what shape it
returns, and what it costs at worst. The prompt itself is not here: it lives in
settings, owned and versioned by the manager (ADR-140 §4).

PII: the model sees the record's own text and nothing about any recipient.
"""

from sqlalchemy.orm import Session

from app.ai.tasks.base import TaskMeta
from app.content.db_models import ContentRecordDB

TASK_KEY = "headline_polish"
MAX_OUTPUT_TOKENS = 300

DEFAULT_PROMPT = """You suggest sharper headlines for one piece of newsletter content.

Suggest 3 headlines for the content below, in the language the content is
written in. At most 60 characters each.

Return exactly 3 options in this format, nothing else:

1. HEADLINE: <headline>
2. HEADLINE: <headline>
3. HEADLINE: <headline>

The content:
{content}
"""

META = TaskMeta(
    key=TASK_KEY,
    label="Headline polish",
    description=(
        "Suggests three sharper headlines for a content record, from that "
        "record's own text. The manager picks one; nothing is applied "
        "automatically."
    ),
    default_prompt=DEFAULT_PROMPT,
    max_output_tokens=MAX_OUTPUT_TOKENS,
)


def gather_inputs(db: Session, content_record_id: int) -> str:
    """The task's declared input: the record's title and description."""
    record = db.query(ContentRecordDB).filter(ContentRecordDB.id == content_record_id).first()
    return f"{record.title}\n{record.description or ''}" if record else ""
```

### E. `backend/app/delivery/providers/example_mail.py` (35 lines)

```python
"""An example email adapter: the shape of a provider, not a vendor.

Throwaway, for the trailer's pre-production check. It sends nothing: it logs
what it was handed, as the mock does, and declares that it carries email only.
A real adapter calls its vendor's API in `send` (see resend.py).
"""

import logging
import uuid

from app.delivery.providers.base import DeliveryProvider, SendResult
from app.rendering.renderers.base import RenderedArtifact

logger = logging.getLogger(__name__)


class ExampleMailProvider(DeliveryProvider):

    channels = frozenset({"email"})
    click_content_attribution = False
    reaches_real_inboxes = False

    def __init__(self, from_address: str | None = None):
        self.from_address = from_address

    def send(self, address: str, artifact: RenderedArtifact) -> SendResult:
        logger.info(
            "example_mail send: to=%s subject=%s bytes=%d",
            address, (artifact.envelope or {}).get("subject"), len(artifact.body or ""),
        )
        return SendResult(
            success=True,
            provider_message_id=f"example-{uuid.uuid4()}",
            message="accepted",
        )
```

### F. `backend/app/delivery/providers/factory.py`, the four edits

```diff
@@ -7,6 +7,7 @@ message about a malformed request, which is a poor way to find out somebody
 configured a push send with an email provider.
 """
 
+from app.delivery.providers.example_mail import ExampleMailProvider
 from app.delivery.providers.mock import MockProvider
 from app.delivery.providers.resend import ResendProvider
 
@@ -25,6 +26,8 @@ def get_provider(provider_name: str, from_address: str | None = None,
         # A per-send verified sender overrides the RESEND_FROM env default;
         # None keeps the adapter's env fallback (mock ignores it entirely).
         provider = ResendProvider(from_address=from_address)
+    elif provider_name == "example_mail":
+        provider = ExampleMailProvider(from_address=from_address)
     else:
         raise ValueError(f"Unsupported provider: {provider_name}")
 
@@ -42,6 +45,7 @@ def get_provider(provider_name: str, from_address: str | None = None,
 PROVIDER_LABELS = {
     "mock": "mock (nothing is sent)",
     "resend": "resend (real)",
+    "example_mail": "example_mail (nothing is sent)",
 }
 #: Which adapters need a sender address. A push has no from-address, so
 #: offering the field is noise; a letter would need a return address, which is
@@ -66,6 +70,7 @@ def providers_for_channel(channel: str) -> list[dict]:
             # ADR-182 point 4: without it, clicks credit no category.
             "click_content_attribution": cls.click_content_attribution,
         }
-        for name, cls in (("mock", MockProvider), ("resend", ResendProvider))
+        for name, cls in (("mock", MockProvider), ("resend", ResendProvider),
+                          ("example_mail", ExampleMailProvider))
         if cls().supports(channel)
     ]
```

### G. The hand-written block, `pull.json` and `pull.html`

```json
{
  "label": "Pull quote",
  "channel": "email",
  "description": "Hand-written template, no MJML source.",
  "cms": false,
  "variables": [ { "name": "text", "required": true } ]
}
```

```html
<div style="max-width:600px;margin:0 auto;padding:16px 20px;font-size:20px;line-height:1.4;border-left:4px solid #1a1a1a">{{ text }}</div>
```
