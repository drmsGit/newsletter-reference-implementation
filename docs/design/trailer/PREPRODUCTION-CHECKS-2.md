---
type: reference
status: draft
created: 2026-10-17
---

# Trailer pre-production checks, round 2: results

The second round of [[TRAILER-BRIEF]] section 15 ("A second round is needed for what the review added"), run on 2026-10-17 in the evening, read against the 22-scene [[STORYBOARD]] on `main` at "trailer storyboard reviewed, two moods, 22 scenes". Round 1 is [[PREPRODUCTION-CHECKS]]. Nothing was built for the film: no frame, no animation, no video. This file records what the running demo does, so that the later build draws what is true.

**Every result below is marked verified or not verified.** Verified means it was done and seen on the running scratch app or in its database, not only read from code. Where a result is a reading of code, or was done with a stand-in, it says so.

**What this file does not do.** It does not edit `TRAILER-BRIEF.md` or `STORYBOARD.md`. The changes those two need are proposed in section 7.

## The checks at a glance

| Check | Result |
|---|---|
| (a) S08, the three manager flows on scratch | **Verified.** With the demo's mock AI both flows return unreadable text, exactly "No draft could be read from the reply" and "No proposal could be read from the reply" (section 1). The success path was also seen, with a **stand-in** canned reply (1.5), not a model. A real model is not needed (1.6): Diede's decision |
| (b) S16, a push-only provider | **Verified.** Listed for the push variant, not for the email one; a new file restarts nothing, the `factory.py` edit restarts the server by itself (1.5 s) |
| (c) S16b, the docstring, the ADRs, history lines | **Verified.** The docstring cites ADR-161 and ADR-101; ADR-101 and ADR-143 exist; four vendor-free history lines are proposed |
| (d) S03b, Integrations | **Verified on scratch:** empty on a fresh reset, one row after the approvals seed. **Not verified** for the development database's own rows (not opened; argued from the reset code) |
| (e) S05, S06, S17, S18 | **Verified.** S05 and S06 match with small differences; **S17 and S18 differ from the storyboard in several places** (5.3, 5.4) |

## 0. How the checks were run

- **A scratch database, not the development one.** Diede said yes to a scratch database; `trailer_scratch2` was created on the existing development Postgres container (`CREATE DATABASE` only) and dropped again at the end. `DATABASE_URL` was set inline for the scratch processes only. The real `app` database was not touched.
- **Own servers, own ports.** A scratch api on :8100 and a scratch client on :5273, started from a throwaway git worktree. The scratch app was used at `http://[::1]:5273/manager/`, not `localhost`, so the sign-in cookie of the real app on :5173 was not shared (round 1's cookie trap).
- **No `.env`, no key, no real model.** No `.env` was read (the worktree has none). `INITIAL_ADMIN_EMAIL` was set inline to a scratch address. The AI provider in Settings stayed `mock`, with "API key configured: no". Mock delivery provider only, never Resend. The send cap was never changed.
- **Sign-in as the dev flow intends.** Code requested in the app, read from the api log, typed in.
- **The demo reset** ran once on the empty scratch database: about 60 s wall clock. The hook's numbers were not re-read (round 1 did that, twice).
- **Throwaway changes, all reverted, none committed.** `frontend/vite.config.ts` (proxy to :8100, port 5273), `.claude/launch.json` (two scratch server entries), `example_mail.py`, `example_push.py` and four edits in `factory.py` (section 2), and, briefly, a canned-reply hook in `backend/app/ai/adapters/mock.py` (section 1.5). Copies of the provider files and the factory diff are in the shared notes folder under `preproduction-drops-2/`, and in the appendix.
- **The app follows the system theme, and the film's manager world is light.** `frontend/src/index.css` switches to dark under `prefers-color-scheme: dark` and lets `data-theme` on `<html>` force either (`light` or `dark`). The first load in the browser pane was the app in dark (the empty Approvals list was the one screen seen that way). Colour-scheme emulation to light was set right after and held for every check below: all the observations in this file are of the light theme. No screen was compared light against dark, so **nothing here says how a screen looks in dark**; the brief's "screens 20 to 45 are not designed in dark" was not tested. For capturing, do not rely on the pane's emulation alone (the pane re-syncs to the app theme): force it in the page with `document.documentElement.setAttribute('data-theme', 'light')` after each load.

| What | How long |
|---|---|
| Demo reset on a fresh scratch database | about 60 s wall clock |
| The api restarting after an edit to `factory.py` | down at 0.7 s, back at 1.5 s after the save |
| "Approve and run" on a 123-recipient mock send | a few seconds; the screen keeps the old state until the sends are done |

## 1. Check (a), S08: the manager flows, performed for real

**Result: verified** for all three shots with the demo's mock AI, and, with a stand-in marked in section 1.5, for what a readable reply looks like. The expected result with the mock is confirmed: **neither AI flow produces anything readable**.

### 1.1 Preparation, and what a fresh reset holds

- Settings, AI prompts lists four tasks on a fresh reset: Content draft, Content translation, Subject & preheader, Variant from a topic. Every row reads "Prompt: the built-in default (never published)". Output: "no approval step" for Content draft, Content translation and Variant from a topic; "applied directly" for Subject & preheader. Both flows of S08 are therefore **no-approval** tasks: nothing of theirs ever waits in Approvals, as the brief says.
- Content draft and Variant from a topic were published with **Publish as version 1**. The list then reads "Prompt: version 1 of 1". (Prompts survive a reset: `ai_prompts` is among the kept tables in `backend/app/demo/reset.py`.)
- **A vendor model name shows even with the mock.** Every task's Model select reads "the default (claude-opus-5)", and Settings, General, AI reads "Default model claude-opus-5 / API key configured no / Tokens used 0 of 100.000". A frame of these screens must crop the model line (S15's note already says so; it applies to S08 too if the Settings are shown).

### 1.2 Shot 1: a content record, "Draft with AI"

The path, as it really is: Content in the navigation opens a short menu (Records, Categories, Graph); **Records** shows the list and the button **New record**. The brief and storyboard say "Content, 'New record'": add the Records step.

| Step | What the app shows |
|---|---|
| New record | Dialog **"New content record"**: fields Title, Description; the note "The fields are filled on the record's page, where they save as you go."; buttons Cancel, Create |
| Create | The dialog closes and the record's page opens at once (`/manager/content/<id>`); the record is first in the list |
| The record's page, top | "Active" with **Deactivate**; the switch **Machine ready** ("May a decision slot pick this without a person choosing it."); **Duplicate into** (a brand select) and Duplicate; the line **"Not published yet, so it cannot be sent until it is."** with the button **Publish**; "No unsent campaign uses this record. Sends use the published version. Where it is used" |
| Below it | Details (Title (required), Description, Language "Not set (any language)"), then the section **"Draft with AI"**, then Translations ("Set this record's language above to translate it."), then the Email and Push field groups |
| "Draft with AI" | **Source** (a text box; hint "Paste the content or write a brief — not anyone's personal details: the text goes to the model provider and is not kept here. 0 of 12,000 characters."); **"Draft the text fields for"** with the two ticks **Email** and **Push**, both ticked by default; the button **Draft with AI** |

**With the mock, the exact result** (a German brief was pasted, both channels left ticked, the button pressed):

> No draft could be read from the reply. The model said:
> 1. Mock option one 2. Mock option two 3. Mock option three [mock:dd4f9cc3]

Nothing else appears: no "Drafted fields", no "Use ticked fields", no provenance hint. The `[mock:xxxxxxxx]` suffix is a hash of the prompt (it differs per prompt). The record afterwards is untouched.

### 1.3 Shot 2: a variant, "Prepare from a topic"

- **The demo's empty variant is real, with a naming correction.** The campaign is **"Neue Ausgabe"** and its one variant is called **"Deutsch"** (email, draft, Modules 0). The brief and storyboard call the variant "Neue Ausgabe". Its campaign page lists "This variant has no modules yet.", **Edit Deutsch**, **Send Deutsch…**, **Duplicate this variant** and the card **New blank variant** (Name, Channel email or push, **Create blank variant**).
- **The editor of that variant offers "Prepare from a topic"**: in the right pane, below Brand profile and Envelope (Subject line, Preheader, **Suggest with AI**), the section **"Prepare from a topic"** with **Topic** (hint "What this edition is about, in a sentence. The AI builds the stack from content a machine may take. 0 of 500 characters.") and the button **Propose a variant**. The stack on the left reads "This variant has no modules yet." and a foot "Add a module".
- **"New blank variant" was also done for real** on the draft campaign Reparaturwoche (name "Scratch Leer", channel email): the app goes **straight into the new variant's editor**, which shows the same "Prepare from a topic" section. An empty **push** variant does not offer it (the section is for email variants only; the empty push editor shows only the Brand profile and "Add a module to start.", with no Envelope and so no "Suggest with AI" either).
- After the first edit of a variant the editor carries a banner: **"You are editing this variant (last edit 20:40). Automations wait until 30 minutes after your last edit. Unblock"**. It also appeared right after "Create blank variant". Draw it or crop it (S13 already says so).

**With the mock, the exact result** (run on both the demo's empty variant and the new blank one):

> No proposal could be read from the reply. The model said:
> 1. Mock option one 2. Mock option two 3. Mock option three [mock:83f0d6ac]

The stack stays empty and no record was created.

**"Enough records" is verified.** The run's offer (kept on the run) held **60 records**, all of which can fill a hero and an image block. The task offers "the newest 60 records a machine may take": published, ready for email, machine ready, in the variant's language or none. On the reset that is the **German batch**, the winter and climbing content (avalanche, cross-country, snowshoe, ski touring, via ferratas, first aid, used-gear days). The English siblings (language `en`) are not offered to a German variant. So **a topic must fit the newest German batch** to read as believable: "Winterausrüstung vor der Saison prüfen, leihen oder gebraucht abgeben" did; an autumn-hiking topic would be offered winter records.

### 1.4 Shot 3: Approvals, "Send a prepared campaign"

**Result: verified.** A draft send was planned first (Reparaturwoche, audience "Interesse: Familie & Kinder", mock: "Goes to 123 recipients as of now, through mock (nothing is sent)." and **Send to 123**, as in S09). `backend/scripts/seed_pending_actions.py` was then run against the scratch database: four requests, as in round 1 (one approvable, one "already sent" warning, one rejected, one expired).

- The list: "2 waiting for a decision"; filters **Action** (All, Send a prepared campaign) and **Requested by** (All, "Acme Agency (demo) (integration)"); each row reads "Send a prepared campaign / Send "Reparaturwoche" (#6) / Acme Agency (demo) (integration)" and a date that is the **deadline** (18.10.2026), not the request time.
- The detail of the approvable request: title "Send a prepared campaign", subtitle `Send "Reparaturwoche" (#6)`; the warning "Before you decide: The audience is re-resolved at send time, so the number above is what matches now — not necessarily what will be mailed."; facts Status "Pending", Requested by **"integration"**, Requested, Expires, Send, Status "draft", Provider "mock", From "— not set —", Audience "123 planned recipient(s)"; then **Decide** with a Reason box (optional; the requester sees it), **Approve and run** and **Reject**.
- **The integration's name is in the list row, not in the detail's facts.** The storyboard's "requested by the integration 'Acme Agency (demo)'" is true of the row only; the detail says "integration".
- **Approve and run** was pressed. The screen kept "Pending" for a few seconds while the 123 mock sends ran, then: the request left the waiting list ("1 waiting for a decision"), the detail read **Approved** with a "Decided" row, the Send's Status turned **"sent"**, and the Decide group was gone. Decision history then listed it: "Approved — Sent: 123 delivered, 0 failed, 0 excluded.", decided by "Initial admin".

### 1.5 What a readable reply looks like (stand-in, marked)

**Result: verified with a stand-in, not a model.** To see the success path the mock adapter was given, in a throwaway edit, a **canned reply** per task (a file read by the mock; no network, no key, no real model; the two replies are in the appendix). This shows what a good reply produces and which labels appear, so that the drawn frames are exact. It is not what the demo does, and the demo's own behaviour is section 1.2 and 1.3. The edit was reverted.

**Draft with AI, with a readable reply:**

- The proposal appears in the same section: a group **"Drafted fields"** of tick rows, one per field, each reading "<field label>: <text>": "Hero headline: …", "Headline: …", "Body text (short): …", "Notification title: …", "Notification text: …". An **empty** field starts ticked; a field that already has text starts unticked and shows "(now: …)". The button **Use ticked fields**.
- **A second group the storyboard does not mention: "Proposed categories"**: one tick row per category with its reason ("Familienwandern — <reason>"), a **Score for <name>** select (1 to 10) and the button **Assign ticked**. The task proposes categories as well as fields. Crop it or draw it.
- After **Use ticked fields**: the line **"5 fields saved."**, and the provenance hint **"487 tokens · mock-1 · prompt v1"** ("N tokens · <model> · prompt vN"). The fields are written into the Email and Push groups below.
- **The record stays unpublished and not ready**, verified: "Not published yet, so it cannot be sent until it is." with Publish still there; Machine ready off; Ready for Email off; Ready for Push off. Storyboard check (f) holds.

**Prepare from a topic, with a readable reply:**

- A line "Chosen among the 60 most recently created records a machine may take.", then a numbered review: **1. Hero** (a tick: "Hero: <record title> — <reason>"), **2. Editorial** (**a text box, not a tick**, with the note "Empty leaves the editorial out."), **Image left**, **Image right**, **Image left** (ticks, alternating, each "<record title> — <reason>"), **Slot** (a tick: ", up to 3 picks per reader from Wintersport, Skitouren — <reason>"), **Subject** (a tick: "<subject> — <preheader>"). Then **Build the variant** and the hint "3465 tokens · mock-1 · prompt v1".
- After **Build the variant**: the stack on the left fills with **Hero Banner [Record]**, **Editorial [Typed in]**, **Image Left [Record]**, **Image Right [Record]**, **Image Left [Record]**, **Image Right [Slot] "From the topic"**; Subject line and Preheader are filled; the hero's headline comes from its record; the "Prepare from a topic" section is gone (the variant is no longer empty); the editing banner of 1.3 appears. So the cue chips "Record", "Slot", "Typed in" appear, as the storyboard says. The slot is labelled **"From the topic"**, an English label in a German variant.
- A second run on the same record or variant was **accepted** (no "one run" refusal), both for the draft and the topic.

### 1.6 A real model: not needed, in my view

Diede decides whether to use one ([[TRAILER-BRIEF]], section 16, open decision 4). My recommendation is **no**, and I stopped nothing to ask: (1) every label and state of the success path is now known (1.5), so drawn frames can be exact, and the mock's `mock-1` provenance is honest and names no vendor; (2) a real model needs a key in the environment and the provider set to claude (a few cents), puts a vendor model name into the provenance hint and the Model select, and answers differently each time, which a film that reads picks "after the final reset" does not want; (3) the result frames are drawings either way, marked as such in the shot notes. If Diede wants real output, it is a separate step with its own approval.

## 2. Check (b), S16: a provider that declares only push

**Result: verified.** Files added in a throwaway worktree, against the scratch app: `backend/app/delivery/providers/example_push.py` (33 lines, `channels = frozenset({"push"})`, `reaches_real_inboxes = False`, logs what it was handed and sends nothing) and, for the two-provider picture of S16, round 1's `example_mail.py` (35 lines). Exact contents are in the appendix.

- **A new file alone restarts nothing.** Adding `example_push.py` and `example_mail.py` produced no `StatReload` line in the api log. The factory does not know them yet.
- **The `factory.py` edit restarts the server, by itself.** The same four places as round 1: the import, an `elif` branch, a line in `PROVIDER_LABELS`, the entry in the tuple of `providers_for_channel`. Console line: `WARNING:  StatReload detected changes in 'app/delivery/providers/factory.py'. Reloading...`, then the usual shutdown and start. Measured by touching the file: the api was down at 0.7 s and back at 1.5 s.
- **A restart is needed, and only for the factory.** In the dev server's reload mode it happens by itself. A deployment without reload would have to restart the process, because the factory imports the adapters when it loads (reasoned from the code, not run).
- **Lines.** One provider is **six inserted lines in four places** of `factory.py` (one line replaced): confirmed again for `example_push`. **Two providers are eleven inserted lines in the same four places.** The scene's "(six lines in four places)" is right for one provider and wrong if both are shown (see section 7, S16).
- **The pickers.** Before the factory edit the push variant's send step listed only "mock (nothing is sent)". After it (the page's data refetched when the window regained focus, no page reload; the focus was simulated by the same `visibilitychange` event the client listens to, because a tab switch in the embedded pane did not trigger it):
  - **push variant** ("Testtag im Laden (Push)"): "mock (nothing is sent)", "**example_push (nothing is sent)**". Not Resend, not example_mail.
  - **email variant**: "mock (nothing is sent)", "resend (real)", "**example_mail (nothing is sent)**". **Not** example_push. The email variant's "Send a test" picker shows the same list.
  - The Settings, General provider table lists them with the channel column: `example_mail (nothing is sent) | email | no — counted, not credited` and `example_push (nothing is sent) | push | no — counted, not credited`. A possible extra shot for S16.
- **The factory refuses a mismatch, in the app's own words.** `get_provider("example_push", channel="email")` raised: "provider 'example_push' cannot deliver on the 'email' channel — it carries push". `providers_for_channel("push")` gave `['mock', 'example_push']` and `("email")` gave `['mock', 'resend']` before example_mail was added.
- **It works end to end.** A push send planned through it for "Interesse: Familie & Kinder" read "Goes to 29 recipients as of now, through example_push (nothing is sent)." and **Send to 29**; after the press the screen said "Sent." and the log carried one line per device: `example_push send: to=grathaus-device-0856 fields={"push_title": "Gravelrunde im Altmühltal", …}`. Nothing left the machine.
- **No sender field.** The push send form showed no From address (`PROVIDERS_WITH_FROM_ADDRESS` was not touched for push), as the factory's own comment says.

Things on the push send screen that a frame must not inherit (also in section 6): its step 3 reads **"Planning freezes the email as it is now; later edits need a new send."** on a push; there is no step 2 (no test send); and the preview fields show **`push_image_url http://localhost:8000/media/…`**.

## 3. Check (c), S16b: the reasons stay with the code

**Result: verified** (files and history read; this scene is files, not screens).

- **The docstring.** The first line of `backend/app/delivery/providers/factory.py` is exactly: `"""Which adapter carries which channel — ADR-161 point 1 plus ADR-101.` It cites ADR-161 and ADR-101, as the scene says. It does not cite ADR-143 (the scene's second jump goes there on purpose). The edits of section 2 did not touch it.
- **The two ADR files exist.** `ADR-101 — Provider Capabilities Are Explicit.md` (frontmatter `status: accepted`, `## Status` "Accepted"; the Decision opens "Provider capabilities must be explicitly defined." then the core capabilities: send, delivery status, bounce feedback, complaint feedback) and `ADR-143 — AI-Assisted Development Boundary.md` (accepted). ADR-143's Decision point 1 reads "**Mode C is ADR-140's philosophy pointed at the repo: the AI's output is a proposal, never a deployment.**" (it wraps over two lines in the file; draw it on one). ADR-161 and ADR-100 exist too.
- **Cautions for the drawing.**
  - ADR-101's **line 73 names three vendors** ("Resend, Brevo, SendGrid"). The scene shows only the status and the first lines of the Decision: do not scroll past them.
  - ADR-143's later lines (146 and 151) name `docs/CLAUDE.md`. Draw only its first Decision point.
  - **The repository tree.** The tracked names include `CLAUDE.md` at the root and `docs/claude.md` (lower case in git), and the folder `.claude/`: an assistant's name in a file name, which S12 and the brief's claim ledger rule out on screen. Draw the pull-back without them.
  - **`storage/` is not in the README's table.** The README's "What is here" table lists `backend/`, `frontend/`, `docs/` and some paths under `docs/`, not `storage/`. The scene's tree with `storage/` is true of the repository but is not the README's table: draw the tree from `git ls-files`, not from the README, and not from the disk (`docs/design/logodevelopment/`, `docs/design/presentation/` and `docs/business/decisions/` are on disk and gitignored).
- **Change-history lines that cite a task and name no vendor or model**, verified on `main`. Proposed, four:

```
d0bcb51 docs: ADR-166 addendum — the key expiry's final-design pass (task-344)
40cc737 feat(integrations): a key may expire, set in days when issued (task-344)
cc9fb6d feat(signals): a link names its content, and a click credits it only if it was sent (task-240, ADR-182)
420921f fix(ui): a catalogue field's switch and Change in catalogue share one line (task-392 item 3)
```

  The first two read as one chain, "the decision, the task, the change": an ADR addendum, then the commit that built it, both citing task-344 (the addendum exists in the ADR file as "Addendum 2026-10-11 (second) — the key expiry's final-design pass"). The third is the one subject that touches `factory.py` itself and cites both a task and an ADR. The fourth is the `(task-NNN item N)` shape the scene text promises. Each commit's **body** ends with a `Co-Authored-By:` trailer that names a model: show subjects only, or crop the trailer. Two other candidates that also pass: `ef2ba79 feat(delivery): what the send screen needs — a test of the frozen send, and the count as of now (task-67)` and `b2f085c fix(client): the send screen says Sent only when it was (task-382)`.
  **Avoid** the older subjects that touch the factory: "Resend outbound provider adapter" names a vendor, and `feat(decision): a slot shows up to 1-5 picks, best first …` says "best first", which the hero scene's "never the best pick" rule forbids.

## 4. Check (d), S03b: Settings, Integrations

**Result: verified** on the scratch app. What the screen shows depends on whether anything has made an integration.

- **On a fresh reset the list is empty.** Settings, Integrations: title "Integrations", the button **New integration**, the line "Other systems that call this platform, each with its own keys and what it may do.", and **"No system calls this platform yet."**; the right pane "Select an integration to see its keys." There is no detail page to open.
- **After the approvals seed there is exactly one row**, the demo's own integration: **"Acme Agency (demo)"**, "Active · 0 live keys", "sends.execute". It exists only because `seed_pending_actions.py` made it (it is given no key).
- **Its detail page**: title "Acme Agency (demo)" and the description **"Raises the approval inbox's demo requests (seed_pending_actions.py)."**, which names a script file: **crop that line**. Then **Keys** ("No live key: it cannot call the platform.", "New key's label", "Expires after (days, empty for never)", **Issue a key**), then **What it may do**.
- **"What it may do"**: the note **"Tick what its keys may do, per brand. Each tick is saved at once. You can only allow what you may do yourself."**; a matrix with the columns **Permission**, **Grathaus Outdoor**, **Grathaus Touren** (one column per brand, as the storyboard says), and a long list of rows, each a permission in monospace with a one-line description (view, campaigns.manage, content.manage, audiences.manage, sends.execute, ai.run, settings.manage, … recipients.manage, recipients.consent, insight.write, … brand_profiles.transactional). Only one box is ticked: **sends.execute on Grathaus Outdoor**. Below it a card "Sending without a person" ("A send it fires to at most this many recipients goes out at once; a bigger one waits for a person in Approvals. 0: every send waits.", **Recipients per send, unattended**, Save) and "Deactivate Acme Agency (demo)". On a 1440-wide screen the first dozen rows fit and the rest needs a scroll; a two-second cut-in shows the note, the two brand columns and the one tick.
- **A key row** (not issued here, so read from the code): `<key id> **label** · issued <date> · last used … [Revoke]`; issuing shows a dialog "The new key" with "This is the only time it is shown." A shot that needs a key row needs a key issued on the capture database.
- **Rows from the development database: not seen, and why they cannot reach the film.** The reset **keeps** integrations, their keys and grants (`KEPT` in `backend/app/demo/reset.py`: `integrations`, `integration_credentials`, `integration_grants`), so a long-lived development database keeps whatever was created in it, which is where "n8n", "webshop" and scratch names come from. A reset database that never held them shows none. I did not open the development database to look (it is not to be touched), so those rows are **not verified here**; the argument is from the reset code and the scratch result. **The rule: capture S03b and S18's integration shot on a freshly reset database, not on the development one.** Then the list holds at most "Acme Agency (demo)", which the film already shows in Approvals.
- **One more app line that supports S03b** (read on a recipient's page): **"Read-only: the CRM owns this person. This page shows why they were chosen and what they were sent."** It is the app's own statement of [[ADR-120 — CRM as Customer Source of Truth]]. It could be a one-second cut-in under the CRM doorway.

## 5. Check (e): S05, S06, S17, S18 against the live screens

### 5.1 S05, Content

**Matches** (verified): the record exists, **"Tagestouren im Chiemgau: Die Rückfahrt zuerst planen"** (record #76 on this reset), German. It has an English sibling, **"Day hikes in the Chiemgau: plan the return journey first"** (language `en`), shown on its page under Translations ("English: Day hikes in the Chiemgau: plan the return journey first"). Its page has a **Categories** card with a score select per category (1 to 10) and the line "1 = barely in the category, 10 = squarely in it."; this record: Sicherheit & Wissen 5, Tagestouren 9, Wandern 6.

**Differences:**

1. **The storyboard's caption** "Tours in the Chiemgau: plan the return first" is the film's own translation. The app has its own English title for the sibling record; use that, or accept the film's.
2. **The list is not where "the list scrolls" lands on this record.** The Records list is newest first, 50 per page ("1–50 of N", Newer/Older), and starts with the English batch ("Two-person tent for €229: pitch it before you buy", …), then the German batch; on a fresh reset this record is on the second page. The Content list **has a search box** ("Find content by title or description", Search, Clear) and three filters (Status, Category, Ready for). Typing "Chiemgau" gives four rows, this one among them.
3. **The brief's section 8 is outdated here**: it says only Campaigns, Recipients and Audiences have a search box. Content has one now.
4. **The scores are far down the page**, after the Email and Push field groups and a **Performance card** ("Sent in 177 deliveries", "Clicks on it 6, from 6 deliveries", "Share of clicks 12 % of the 49 clicks in the emails that carried it", a one-row table). The push-in on the scores needs a scroll; the Performance card is a free clicks-only shot (clicks only, no opens).
5. The same page carries the "Draft with AI" section, so the S05 record and the S08 record share a layout.

### 5.2 S06, a campaign points to it

**Matches** (verified; a headline was edited and reset on a scratch campaign):

- The **stack** on the left, with the cue chips: **Record**, **Slot** and **Typed in** all appear in the Reparaturwoche variant (Hero Banner [Record], Editorial [Typed in], Image Left [Record], Image Right [Record], Image Left [Slot] "Für Sie ausgewählt"). The demo variant **"Herbst in den Bergen / Autumn in the mountains" (Deutsch)** has two Image Left modules that both read **[Record]**, and its first module is the S05 record itself, "Tagestouren im Chiemgau: Die Rückfahrt zuerst planen": a natural S05 to S06 link for the override beat.
- **The override.** Before: the field reads "Headline (required)" with a foot row of the switch "Hide Headline in this module" and the accent link **"Change Headline in catalogue"** at the right (the audit fix of task-392 item 3: one line). After the edit: the label turns **"Headline — overridden here (required)"** with an accent rule at the field's left, the line **"Catalogue: <the catalogue value>"** under it, and the foot row gains the button **"Back to the catalogue value"** beside the switch; "Change Headline in catalogue" stays at the right. Pressing "Back to the catalogue value" returned the label to "Headline (required)".

**Differences:** the storyboard's "the line 'Back to the catalogue value' appears beside it" is a **button** in the foot row; the new "Catalogue: …" line is not mentioned; the editing banner ("You are editing this variant … Unblock") appears after the first edit.

### 5.3 S17, email and push

**Matches** (verified): the push editor with its one module (stack: **Notification [Record]** "Gravel im Altmühltal: Eine Runde mit drei Abkürzungen"; the line "A push variant holds 1 module, and this one is full."), the preview, and a push through the mock reaching 29 recipients.

**Differences, three of which make the scene as written untrue:**

1. **"The campaign page shows two variants, Email and Push" is not true of the demo.** The demo's push campaign **"Testtag im Laden (Push)"** has **one** variant, "Push". No demo campaign carries both. A campaign with both is **possible in the app, in a minute** (verified on Reparaturwoche): **New blank variant**, channel **push**, add the **Notification** module, pick a record; the campaign page then lists "Deutsch (email)" and "Push (push) — Modules 1 of 1" with their own Edit, Send and Duplicate. Either do that on the capture database, change the demo seed, or show the two campaigns side by side.
2. **"A small label, in the app's own words, says nothing is sent" exists only in the Send step**: the provider label "mock (nothing is sent)" and "…through mock (nothing is sent)." The push editor and the preview carry no such label.
3. **The push preview is not a phone.** It is the sheet **"Preview of Push"**: "A preview shows what is saved now, unpublished edits included. A test send shows what will actually be sent.", **Preview for a recipient (optional)**, **Modules** ("Notification · from the catalogue"), and a table **"Fields of Push"** of raw field names: `push_title`, `push_body`, `push_image_url`, `push_link`. Draw that, and not a lock screen (the brief already says no phone).
4. **`push_image_url` reads `http://localhost:8000/media/…`** in the preview and in the send step (the api's development address, as with the unsubscribe link): crop or redraw it.
5. The push send step says "Planning freezes the email …" (section 6).
6. The captures `58-push-editor` and `60-push-preview` predate these screens: re-capture, as the storyboard already says.

### 5.4 S18, everything else, in one breath

Screen by screen (verified), with what each carries:

| Shot | What the live screen is | For the frame |
|---|---|---|
| Audiences | Three groups, each with the description **"Grathaus demo segment (task-71)"**; the detail has Name, Description, Channel, **Who's in** (rule "Familie & Kinder ≥ 1"), **Leave out**, **Added by hand**, **Who a send reaches**, and the list of who is reachable | **Crop to the rules card, and redraw or crop the description.** The description shows a task reference. The detail also shows exclusion and opt-out wording: "People who opted out are never sent to anyway: that's consent, not this list." and the funnel **"Match the rules 125 / Not agreed to email −2 / Added by hand +0 / Removed by exclusion segments −0 / In the audience 123"**. This **is an exclusion count**, and it contradicts the brief's decisions 7 and 8 (consent stays only if the film never shows exclusion or opt-out). It also qualifies round 1's "no one is excluded anywhere": nobody is excluded **at send** (the audience already omits the two who have not agreed to email: 125 match, 123 are in), which is why the send screen reads "123 of 123". |
| Recipients | A list of pseudonymous ids ("grathaus-1000 / Reachable on email, push / de · active"), no addresses; the detail says "Read-only: the CRM owns this person.", a **Consent** table (email, marketing, `opted_in`, source "demo"), **Audience groups** (In or out, and why), **Deliveries** with a column **"Excluded because"**, **Decisions** | Draw the list. If the detail is used, **crop the "Excluded because" column**. |
| A brand profile | Settings, Brand profiles: "Newsletter Deutsch / Default · de · marketing / Complete", "Newsletter English", "Service-Mails / de · transactional" | Fine. The detail pane was not opened. |
| Personalisation | "Salutation formal `{{salutation_formal}}` de, en", "Salutation informal `{{salutation_informal}}` de, en" | Fine; it shows the placeholder token in braces. |
| Roles | Admin, Manager, Viewer, each "Shipped · N permissions" and a count of people | Fine; counts of people, no names. Do not state the numbers. |
| An integration key | The one seeded integration has **no key** ("No live key: it cannot call the platform.") | A key row needs a key issued on the capture database (section 4). |
| Monitoring | "Where are my campaigns? Open a row to go to its campaign." A table Campaign, State ("In preparation", **"Sent"**), Variants, Next scheduled, Last sent; "No counts here: figures are on each campaign." | Fine. Unlike the Campaigns list (which still says "draft"), Monitoring says **Sent**. |
| Deliveries | Rows "Familienherbst / Familienherbst / Deutsch / sent · 123 / 0 / 0 / 8.10.2026, 08:30:00"; caption "Sent / failed / excluded" | Fine; the "excluded" in the caption reads 0 everywhere. |
| AI prompts | The list "Model: the default · Output: no approval step / Prompt: version 1 of 1" | The list has no vendor name; **the detail's Model select does** (crop). |
| The approvals history | The "Decision history" screen under Approvals: columns Request, Summary, Outcome, Requested by, Decided by, Ended, Reason; rows Approved ("Sent: 123 delivered, 0 failed, 0 excluded."), Expired ("nobody (expired)"), Rejected ("Not this week — the offer changed.") | Empty until the approvals seed has run and a request was decided. Its summary says **"123 delivered"** (the app's word); the hook's rule says never "delivered": do not caption it. |

**Differences from the storyboard text:**

1. **"Twelve one-second shots"** but ten screens are named. Either two more, or "ten".
2. **"The navigation's 'you are here' in Pale Pink steps down the list"** does not hold in the order given. The live navigation reads: Approvals, Campaigns, Monitoring, Content, Audiences, Recipients, Deliveries, Decision slots, Settings. Brand profile, Personalisation, Roles, the integration and AI prompts are **all under Settings**, one navigation entry. In the storyboard's order the marker goes Audiences, Recipients, Settings ×4, Monitoring (up), Deliveries, Settings (up), Approvals (up). To step down the list: Approvals history, Monitoring, Audiences, Recipients, Deliveries, then the Settings screens.
3. **The navigation foot now has a "Keyboard shortcuts" button** above Sign out (the handoff says so): it is in every frame.
4. **"Consent"** in the narration has no screen of its own among the ten: the closest is the Recipient detail's Consent card (with `opted_in`), and the Audiences funnel above.
5. The brief says the Integrations list holds "n8n"/"webshop" rows: on a fresh reset it holds none (section 4).

## 6. New flaws found, which a frame could inherit

None was changed here.

- **The push send step says "email".** "Planning freezes the email as it is now; later edits need a new send." on a push variant; its step numbers skip from 1 to 3 (no test send for a push).
- **`localhost:8000` in a push payload.** The push image address reads `http://localhost:8000/media/…` although the scratch api ran on :8100 (the unsubscribe link has the same development-address fallback; the image's cause was not traced).
- **Demo data carries internal wording.** The three audience groups are described "Grathaus demo segment (task-71)" and the seeded integration "(seed_pending_actions.py)".
- **The audience page shows opt-out and exclusion wording and a count** (section 5.4), which the film's decisions rule out.
- **A freshly sent mock campaign shows "Delivered 0"** on its Results card (Reparaturwoche after the approved send: Recipients 123, Sent 123, Delivered 0); only the seeded campaigns carry delivered, bounce and click figures. The approvals history says "123 delivered" for the same send.
- **Topic proposals are chosen among the newest 60 takeable records**, so a topic that does not fit the newest batch is offered the wrong content (section 1.3).
- **The built slot is labelled "From the topic"**, in English, in a German variant.
- **A blank variant opens with the "You are editing this variant … Unblock" banner** before anything is typed.
- **A freshly reset database has no integration at all**, so Settings, Integrations is empty until something creates one (the approvals seed does).
- **The app renders in dark whenever the system is dark** (`prefers-color-scheme`, overridable with `data-theme` on `<html>`): a capture on a dark machine silently carries a dark UI. The brief says dark mode for screens 20 to 45 is not designed; it was not examined here (see section 0).

## 7. Changes the brief and storyboard need (proposed, not made)

Ordered by scene. "Brief" means [[TRAILER-BRIEF]], "SB" means [[STORYBOARD]].

**S03b.**
- Replace "rename or crop before capture" (the "n8n", "webshop" rows) with: **capture on a freshly reset database**, where Settings, Integrations is empty until the approvals seed has run and then holds only "Acme Agency (demo)" (verified). The development database keeps its own integrations through a reset, and must not be captured.
- The cut-in's matrix is real, with the note as the SB quotes it (it continues: "Each tick is saved at once. You can only allow what you may do yourself."). Crop the detail's description line, which names `seed_pending_actions.py`. Only one box is ticked (sends.execute for Grathaus Outdoor); the shot reads as one integration with one grant, which suits "own key · own permissions".
- Optional: a one-second cut-in of the recipient page's line "Read-only: the CRM owns this person." under the CRM doorway.

**S05.**
- Correct the route: Content, then **Records**; open the record from the Content search ("Chiemgau") instead of scrolling.
- Use the app's English title for the caption, "Day hikes in the Chiemgau: plan the return journey first", or keep the film's own.
- Say that the scores are in the **Categories** card low on the page (select boxes, 1 to 10, "1 = barely in the category, 10 = squarely in it."), above which sits a clicks-only **Performance card**.
- Brief section 8: Content **has** a search box now.

**S06.**
- Use two campaigns for two beats: the cue chips **Record / Slot / Typed in** from the Reparaturwoche variant; the override from "Herbst in den Bergen / Autumn in the mountains" (Deutsch), whose first module is the S05 record.
- Say what the override looks like: the label turns "Headline — overridden here (required)", the line "Catalogue: <value>" appears, and the button **"Back to the catalogue value"** appears in the foot row beside the switch; "Change Headline in catalogue" stays at the right. Note the editing banner after the first edit.

**S08 (hero).** The scene's structure holds; its words need these corrections:
- **Shot 1:** add the route (Content, Records, New record). The dialog is "New content record"; Create opens the record's page. "Draft with AI" sits right below the Details; Email and Push are ticked by default. The proposal has **two** groups, **Drafted fields** and **Proposed categories** (with "Assign ticked"); say so or crop the second. After "Use ticked fields": **"5 fields saved."** and the hint "N tokens · mock-1 · prompt v1". Keep the record's "Not published yet, so it cannot be sent until it is." and Publish (verified).
- **Shot 2:** the demo's empty variant is the variant **"Deutsch" of the campaign "Neue Ausgabe"**; "New blank variant" is a card at the foot of any campaign page and opens the new variant's editor at once. The review's **Editorial is a text box** ("Empty leaves the editorial out."), not a tick; the subject tick reads **"Subject"**; add the line "Chosen among the 60 most recently created records a machine may take." The built stack ends with an **Image Right [Slot] "From the topic"**.
- **Shot 3:** the integration's name is in the list row; the detail's facts say "Requested by integration". The request stays "Pending" for a few seconds after "Approve and run" while the sends run.
- **With the mock, the result frames of shots 1 and 2 are drawings,** and now they can be exact: the labels and states are in section 1.5. Use a **winter topic** ("Winterausrüstung vor der Saison prüfen, leihen oder gebraucht abgeben" worked) because the newest batch is winter content; draw the hero, image blocks and slot from records that exist (section 1.5 and the appendix list the ones the stand-in used).
- Check (e): add that the prompts were published once ("Publish as version 1") and that a second run on the same record or variant is accepted.
- Brief section 16, still open 4: my recommendation is **drawings, no real model** (section 1.6). The decision stays Diede's.

**S16.**
- State the line count per provider: **six inserted lines in four places for one provider; eleven for two**. If both files are shown, say "the same four places, once for each", or show the factory edit once with both providers in it.
- The push provider's file: `channels = frozenset({"push"})`, and say `reaches_real_inboxes = False` (it defaults to True).
- The pickers are as the SB says (verified): email variant "mock (nothing is sent)", "resend (real)", "example_mail (nothing is sent)"; push variant "mock (nothing is sent)", "example_push (nothing is sent)". The **refocus** is what updates them (no reload). One more optional shot: Settings, General's provider table with its **Channels** column showing `push` for the new one.
- Add the factory's own refusal as a possible one-second line: "provider 'example_push' cannot deliver on the 'email' channel — it carries push".
- Optional: a push really sent through the new provider (the screen says "Sent."; the log shows one line per device). It sends nothing, and the picture must not suggest a phone receiving it.

**S16b.**
- The factory docstring, ADR-101 and ADR-143 are exactly as drawn (verified, section 3).
- Draw the repository tree from `git ls-files`, **without** `CLAUDE.md`, `docs/claude.md` and `.claude/`, and without the gitignored folders; `storage/` is in the repository but not in the README's table, so do not attribute the tree to the README.
- Show ADR-101 only to the top of its Decision (line 73 names three vendors) and ADR-143 only to its first point (later lines name `docs/CLAUDE.md`).
- Use the four history lines of section 3, subjects only (each commit's body ends with a trailer naming a model).

**S17.**
- Replace "The campaign page shows two variants, Email and Push" with what the demo has: **one** variant on the push campaign. Either add a push variant to an email campaign on the capture database (a minute, section 5.3), change the demo seed, or show the push campaign beside an email campaign.
- Replace "a small label, in the app's own words, says nothing is sent" with the **Send step's** "through example_push/mock (nothing is sent)", or drop it.
- Say the preview is the **"Preview of Push"** sheet with a **"Fields of Push"** table of raw field names, not a phone; crop the `localhost:8000` image address and the send step's "Planning freezes the email …".

**S18.**
- "Twelve one-second shots": list twelve, or say ten.
- Reorder so the Pale Pink marker steps down: Approvals history, Monitoring, Audiences, Recipients, Deliveries, then the five Settings screens (brand profile, Personalisation, Roles, an integration, AI prompts).
- **Audiences:** crop to the rules card ("Who's in") and redraw the description; do **not** show "Leave out", "Who a send reaches" or the line about opted-out people. **Recipients:** crop "Excluded because". **Approvals history:** crop or do not caption "123 delivered". **AI prompts:** crop the detail's Model select. **Integration key:** needs a key issued on the capture database.
- Add the Keyboard shortcuts button to the list of things every frame now carries.
- The word "Consent" in the narration has only the Recipient detail's Consent card (with `opted_in`) to point at; decision 7 stands only if that card is the only consent picture.

**Brief section 8 (known flaws).** Add the flaws of section 6 that a frame can inherit: the push step's "email", `localhost:8000` in a push payload, the internal wording in the demo data, the audience page's exclusion wording, "Delivered 0" on a fresh mock send, the topic's newest-60 rule. Update "Approvals is empty after a reset": the seed also creates the one integration; and "the demo AI is a mock": the success path was seen with a stand-in (section 1.5).

**Brief section 11 (claim ledger).** The AI row ("AI suggests and drafts, a person ticks or builds…") is **confirmed by running**: "Draft with AI" fills the fields a person ticks, on a record the person created, which stays unpublished and not ready; "Prepare from a topic" builds an empty variant's blocks and subject; Settings says "no approval step". Add, as a caution, that **"Proposed categories" are part of the draft** (a person ticks them too). The row "The delivery provider can be swapped with a file and a few lines" should say "six lines per provider, in four places".

**Brief section 15.** The second round is done by this file: (a) to (e) are verified, with the stand-in of 1.5 marked; what stays open is Diede's decision on a real model (section 1.6) and the follow-ups of section 8.

## 8. Follow-ups in the project, not in the film

None was changed here. Each could be a queue entry.

1. **The push send step says "email"** (`frontend/src/screens/SendVariant.tsx`, line 346) and skips step 2 without saying why.
2. **The push image address reads `http://localhost:8000/media/…`**, as the unsubscribe link does (that one falls back to `PUBLIC_BASE_URL_DEFAULT` in `backend/app/subscriptions/service.py`); the scratch api ran on :8100. That the image address has the same cause was not traced.
3. **Demo data names its own tooling.** The audience descriptions read "(task-71)" and the seeded integration "(seed_pending_actions.py)" (`backend/app/demo/`, `backend/scripts/seed_pending_actions.py`).
4. **The demo has no campaign with both an email and a push variant**, so "one campaign, two channels" cannot be shown without making one by hand.
5. **A fresh mock send reports "Delivered 0"**, while the approvals history of the same send says "123 delivered".
6. **The slot built from a topic is labelled in English** ("From the topic") in a German variant.
7. **The approvals seed's closing hint still says `/ui/approvals`** (round 1 follow-up 5, still open).

## Appendix: files of the second round

All of these are throwaway. They were created in a git worktree, uncommitted, and removed. Copies are in the shared notes folder under `preproduction-drops-2/`.

### A. `backend/app/delivery/providers/example_push.py` (33 lines)

```python
"""An example push adapter: the shape of a provider, not a vendor.

Throwaway, for the trailer's pre-production check. It sends nothing: it logs
what it was handed, as the mock does, and declares that it carries push only.
A real adapter calls its vendor's API in `send` (see resend.py).
"""

import json
import logging
import uuid

from app.delivery.providers.base import DeliveryProvider, SendResult
from app.rendering.renderers.base import RenderedArtifact

logger = logging.getLogger(__name__)


class ExamplePushProvider(DeliveryProvider):

    channels = frozenset({"push"})
    click_content_attribution = False
    reaches_real_inboxes = False

    def send(self, address: str, artifact: RenderedArtifact) -> SendResult:
        logger.info(
            "example_push send: to=%s fields=%s",
            address, json.dumps(artifact.fields or {}, ensure_ascii=False),
        )
        return SendResult(
            success=True,
            provider_message_id=f"example-push-{uuid.uuid4()}",
            message="accepted",
        )
```

`example_mail.py` is round 1's ([[PREPRODUCTION-CHECKS]], appendix E).

### B. `backend/app/delivery/providers/factory.py`, both providers (11 insertions, 1 deletion)

```diff
@@ -7,6 +7,8 @@ message about a malformed request, which is a poor way to find out somebody
 configured a push send with an email provider.
 """
 
+from app.delivery.providers.example_mail import ExampleMailProvider
+from app.delivery.providers.example_push import ExamplePushProvider
 from app.delivery.providers.mock import MockProvider
 from app.delivery.providers.resend import ResendProvider
 
@@ -25,6 +27,10 @@ def get_provider(provider_name: str, from_address: str | None = None,
         # A per-send verified sender overrides the RESEND_FROM env default;
         # None keeps the adapter's env fallback (mock ignores it entirely).
         provider = ResendProvider(from_address=from_address)
+    elif provider_name == "example_mail":
+        provider = ExampleMailProvider(from_address=from_address)
+    elif provider_name == "example_push":
+        provider = ExamplePushProvider()
     else:
         raise ValueError(f"Unsupported provider: {provider_name}")
 
@@ -42,6 +48,8 @@ def get_provider(provider_name: str, from_address: str | None = None,
 PROVIDER_LABELS = {
     "mock": "mock (nothing is sent)",
     "resend": "resend (real)",
+    "example_mail": "example_mail (nothing is sent)",
+    "example_push": "example_push (nothing is sent)",
 }
 #: Which adapters need a sender address. A push has no from-address, so
 #: offering the field is noise; a letter would need a return address, which is
@@ -66,6 +74,8 @@ def providers_for_channel(channel: str) -> list[dict]:
             # ADR-182 point 4: without it, clicks credit no category.
             "click_content_attribution": cls.click_content_attribution,
         }
-        for name, cls in (("mock", MockProvider), ("resend", ResendProvider))
+        for name, cls in (("mock", MockProvider), ("resend", ResendProvider),
+                          ("example_mail", ExampleMailProvider),
+                          ("example_push", ExamplePushProvider))
         if cls().supports(channel)
     ]
```

### C. The canned replies of the stand-in (section 1.5)

The mock adapter was edited, briefly, to return one of these when the prompt was the task's: a file per task, read at call time. The edit is reverted; the demo's mock has no such behaviour.

`content_draft` (field names are the real ones of `storage/fields.json`; category names exist in the demo):

```json
{"fields": {"headline_hero": "Herbstrunde mit Kindern", "headline_medium": "Zwei Stunden, drei Pausenplätze", "body_medium": "Eine leichte Herbstwanderung im Chiemgau für Familien mit Kindern ab sechs Jahren: kurze Etappen, drei Pausenplätze und ein Spiel für unterwegs.", "push_title": "Herbstrunde im Chiemgau", "push_body": "Zwei Stunden, drei Pausen, ein Spiel für unterwegs. Treffpunkt am Parkplatz."}, "categories": [{"name": "Familienwandern", "score": 9, "reason": "Kurze Etappen und Pausenplätze für Kinder ab sechs."}, {"name": "Tagestouren", "score": 6, "reason": "Etwa zwei Stunden, ein Tag reicht."}]}
```

`variant_from_topic` (record ids 150, 148, 146 and 144 were in the run's offer on this reset: "Rosenheim: Winterausrüstung gebraucht abgeben am 6. März", "Grathaus Basis Isolationsjacke: 139 Euro für die Winterpause", "Drei Winterwochenenden: Leihkosten vollständig vergleichen", "Lawinenschaufel für 59 Euro: Mit Handschuhen zusammensetzen"; the ids are stable only for this reset):

```json
{"hero": {"record_id": 150, "reason": "Der nächste Annahmetermin passt zum Thema."}, "editorial": "Bevor der erste Schnee fällt, lohnt der Blick in den Schrank: Was passt noch, was fehlt, was kann weiterwandern? Diese Ausgabe sortiert Winterausrüstung zum Prüfen, Leihen und Abgeben.", "blocks": [{"record_id": 148, "reason": "Eine Jacke für die Winterpause."}, {"record_id": 146, "reason": "Leihkosten vollständig vergleichen."}, {"record_id": 144, "reason": "Zubehör, das mit Handschuhen geprüft wird."}], "slot": {"categories": ["Wintersport", "Skitouren"], "reason": "Jede Leserin bekommt, was zu ihrem Winter passt."}, "subject": "Winterausrüstung: erst prüfen, dann kaufen", "preheader": "Prüfen, leihen, gebraucht abgeben: drei Wege vor der Saison."}
```

These are drawings of a model's reply, not output of one. A frame built from them is marked as a drawing in the shot notes.
