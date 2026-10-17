---
type: reference
status: draft
created: 2026-10-17
---

# Capture list

The real-app screens the film needs, by scene. Every capture: the app at one recorded commit, on the `trailer_capture` database, **light theme**, brand **Grathaus Outdoor**, English interface, viewport **1440×810**, device scale **2**, saved as `captures/<id>.png`. A **tall** capture uses a viewport up to 1440×2400 so the whole column shows and a scene can scroll it. Capture before you change data, in the order of section "Order". See [[BUILD-PLAN]], [[STORYBOARD]] and [[PREPRODUCTION-CHECKS]] / [[PREPRODUCTION-CHECKS-2]] for the exact labels and states.

| id | Scene | What | Notes |
|---|---|---|---|
| c01-deliveries-list | S01, S18 | Deliveries, list only, nothing selected; the Familienherbst row `sent · 123 / 0 / 0` visible | |
| c02-slot-list | S01 | Decision slots, the Familienherbst row selected ("Für Sie ausgewählt", `recipient_top_score`, 369 picks) | |
| c03-slot-detail | S01, S07 | the same slot's page: "What it chooses from", "What it has picked" (369, 123, 15) | tall |
| c04-as-sent | S01, S10 | Deliveries, Familienherbst, one reader (Lea Huber #32), "As sent": subject, preheader, message | tall; capture BEFORE any file drop; the unsubscribe row is cropped in the scene |
| c05-slot-reasons | S10 | the slot page scrolled to "Reasons given" for one reader | |
| c06-content-search | S05 | Content, Records, search "Chiemgau", the record "Tagestouren im Chiemgau: Die Rückfahrt zuerst planen" selected | |
| c07-record-categories | S05 | the record page, the Categories card with the scores 1 to 10 | tall |
| c08-editor-chips | S06 | variant editor, a variant with Record, Slot and Typed in chips (Reparaturwoche) | |
| c09-override-before / c10-override-after | S06 | "Herbst in den Bergen / Autumn in the mountains", Deutsch: the first module's headline; then typed: "Headline — overridden here" with "Back to the catalogue value" | tall |
| c11-slot-settings | S07 | the editor's slot settings: "Für Sie ausgewählt", `recipient_top_score`, shows up to 3 | |
| c12-preview-reader-a / b / c | S07 | the Preview sheet for `lea.huber.32`, `michael.zimmermann.127`, `peter.mueller.330`: the email with the shared top and three different tails | tall; each reader found through the "Preview for a recipient" search and its result button |
| c13-new-record-dialog | S08 | Content, "New record": the dialog "New content record" | |
| c14-record-draft-source | S08 | the new record's page, "Draft with AI": a Source text pasted, Email and Push ticked | |
| c15-draft-proposal | S08 | the proposal: "Drafted fields" and "Proposed categories", "Use ticked fields" | **drawn result**: intercept the AI endpoint with a readable reply (the stand-in replies are in [[PREPRODUCTION-CHECKS-2]], appendix C and section 1.5); believable German; mark as a drawing in `CAPTURE-LOG.md` |
| c16-record-saved | S08 | after "Use ticked fields": "5 fields saved." and "Not published yet, so it cannot be sent until it is." | |
| c17-new-blank-variant | S08 | campaign "Neue Ausgabe", "New blank variant" | |
| c18-prepare-from-topic | S08 | the empty editor with "Prepare from a topic", a winter topic typed | |
| c19-topic-review | S08 | "Propose a variant" result: Hero, Editorial (a text box), Image left/right, Slot, Subject | **drawn result**, as c15 |
| c20-built-stack | S08 | after "Build the variant": the stack with Record, Slot, Typed in chips | **drawn result** |
| c21-approvals-request | S08 | Approvals: "Send a prepared campaign" from "Acme Agency (demo)", pending, with "Approve and run" | needs the approvals seed after a draft send is planned |
| c22-approvals-approved | S08 | the list after "Approve and run" | |
| c23-send-step1 / c24-send-plan / c25-send-ready | S09 | the Send screen: step 1; step 3 (the audience group line "123 of 123 in this group can be reached on email now"); step 4 "Goes to 123 recipients as of now, through mock (nothing is sent)." and "Send to 123" | |
| c26-results | S11 | the campaign page, Results card (delivery table and engagement table) | the Unsubscribes column and the footnote are cropped in the scene |
| c27-add-module-quote | S13 | the editor after the page reload: "Add a module" open with "Quote" | after the throwaway drop (below) |
| c28-quote-fields | S13 | the Quote module: Text typed (German), Heading empty | |
| c29-strategy-list | S14 | the slot settings, the Strategy list with "Recency boost", "Recipient Top Score", "Top Score" | after the drop and a page reload |
| c30-strategy-chosen | S14 | "Recency boost" chosen, its extra field "recency weight" | |
| c31-ai-prompts-list | S15 | Settings, AI prompts: the new task in the list | after the drop |
| c32-ai-prompt-detail | S15 | the new task's page: the pre-filled prompt, "Publish as version 1" | the Model select is cropped in the scene |
| c33-send-picker-email / c34-send-picker-push | S16 | the provider picker: mock, resend, example_mail / mock, example_push | after the provider drop and the reload |
| c35-campaign-two-variants | S17 | a campaign with "Deutsch (email)" and "Push (push)" | make it on the capture database: Reparaturwoche, New blank variant, channel push, Notification module, a record |
| c36-push-editor | S17 | the push variant's editor with its one module | |
| c37-push-preview | S17 | the sheet "Preview of Push" with the "Fields of Push" table | crop the `localhost` image address in the scene |
| c38-approvals-history | S18 | Approvals, Decision history | after the approval of c21 |
| c39-monitoring | S18 | Monitoring | |
| c40-audiences-rules | S18 | Audiences, the rules card only ("Who's in") | no "Leave out", no funnel, no opt-out line |
| c41-recipients-list | S18 | Recipients, list | |
| c42-brand-profile | S18 | Settings, Brand profiles | |
| c43-personalisation | S18 | Settings, Personalisation | |
| c44-roles | S18 | Settings, Roles | |
| c45-integration-matrix | S03b, S18 | Settings, Integrations, "Acme Agency (demo)", "What it may do" | the description line naming a script is cropped |
| c46-ai-prompts | S18 | Settings, AI prompts (the list) | |

## Order

1. Read-only captures first: c01 to c07, c11, c12, c26 (before any send), c36 needs data, so later.
2. Data preparation: publish the two AI prompts ("Content draft", "Variant from a topic") as version 1 and the third ("Subject & preheader") only if needed; plan a draft send and run `backend/scripts/seed_pending_actions.py` against `trailer_capture`; make the email-plus-push campaign (c35).
3. The manager flows: c08 to c10, c13 to c25 (c15, c19, c20 with intercepted AI replies), then c35 to c46.
4. **Last**, in a throwaway worktree with its own `storage/modules/email`: the file drops of S13 to S16 (the `quote` block, `recency_boost.py`, `headline_polish.py`, `example_mail.py` and `example_push.py` with the `factory.py` edits; the exact files are in [[PREPRODUCTION-CHECKS]] and [[PREPRODUCTION-CHECKS-2]], appendix), restarting the api once after the `factory.py` edit; then c27 to c34. Any change in `storage/modules/email/` makes "As sent" show template notices, so c04 and c05 are taken first.
