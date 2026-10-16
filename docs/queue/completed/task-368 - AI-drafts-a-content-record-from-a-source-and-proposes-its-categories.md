---
id: TASK-368
title: AI drafts a content record from a source and proposes its categories
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 20:44'
updated_date: '2026-10-16 19:43'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** For the November 2026 presentations (docs/business/PRESENTATIONS-2026-11.md), raised by the user 2026-10-11 as an extension of the AI subject suggestion: "create content and categorize". A manager gives a source (a text, a link's text, a short brief) and the AI drafts a content record's fields for the channels it is meant for, and proposes category assignments with scores. A person reviews and saves; nothing is published or assigned without them (ADR-080: the taxonomy is human-governed; ADR-140 Assistive mode).

**Design questions for its final-design pass.** Which fields it fills (fields.json concepts); whether the proposal uses existing categories only (ADR-080 suggests yes); how the proposal shows its reasons; the prompt and its budget (ADR-144). task-95 (AI taxonomy recommendations) is related but about the taxonomy itself, not one record.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Backend task app/ai/tasks/content_draft.py (META key content_draft, max output ceiling, default prompt; no held form). Inputs: pasted source (max 12000 characters, never stored), the ticked channels, the text and rich-text catalogue fields of those channels (labels and notes, never url, image or alt fields), the existing category names. Output JSON parsed tolerantly; unknown fields and invented categories dropped (counted for a notice); scores clamped to nothing, out-of-range refused as unusable; markdown links reduced to their label. 2. TaskMeta.held_form flag (default True); settings refuse require_approval for a task without one; React and Jinja settings show a sentence instead of the switch. 3. POST /content/{id}/draft {source, channels} (ai.run in policy), refusals before the call as 409 {reason, message}; GET /content/{id}/drafts newest first with fields, categories (name, id, score, reason), notices, tokens. 4. ContentPatch and the category assignment and score routes take applied_suggestion_run_id; the audit entry names the run when it is this record's content_draft run. 5. React: Draft with AI panel on the record page (AIButton), channel ticks, source box with the personal-data line and the cap; proposal with ticked fields (filled ones unticked, both versions shown) and ticked categories with editable scores and reasons; Use ticked fields / Assign ticked. 6. Tests first, mutation-checked; gates; live check with a stand-in for the model call; addenda ADR-140 and ADR-141 2026-10-16.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-16 (task-100): the button that starts this model call is frontend/src/components/AIButton.tsx, which already waits visibly and asks once; do not hand-roll a pending state. The server-side guard against two runs at once is task-387.

Built 2026-10-16: backend 54f4d4a, client 185a2db; ADR-140 and ADR-141 addenda 2026-10-16 (in 54f4d4a). Final design, decided with the user one question at a time: on the record page (the run belongs to the record); pasted text only, the server never fetches a web address (task-388 filed for that decision); every text and rich-text field of the ticked channels from fields.json with labels and notes, never links, images or alt text; drafted fields ticked except where the record already has text, both shown, Use ticked fields in one edit; categories from the existing vocabulary only, score 1 to 10 editable before taking, the model's reason shown, already-assigned ones unticked with their current score; no approval step (TaskMeta.held_form False; Settings says so on both planes, the server answers 422 to require_approval); a personal-data line and the 12,000-character cap on the box, no detection. Code: backend/app/ai/tasks/content_draft.py (check_request, build_prompt, read_proposal, draft, drafts_for_record); POST and GET /content/{id}/drafts (POST is ai.run in policy.py); applied_suggestion_run_id on PATCH /content/{id}, POST /content/{id}/categories and PATCH /content/{id}/assignments/{id}, named in the audit entry through app/ai/service.py applied_run (shared with task-367). The source is never stored. Found and fixed on the way: the AI task registry reloaded base.py on every discovery, so any task file sorting before registry.py was silently dropped (content_draft was invisible); and the channel ticks started empty on the live page because the fields load after the panel (it now remembers what was unticked). Tests: backend/tests/test_content_draft.py (19) and frontend ContentDraft.test.tsx (8) plus a Settings case; 20 backend and 18 client mutations, all killed. Full pytest, Ruff, vitest, tsc, eslint, build, CI green. Live check on scratch record 121 with a seeded mock-provider run (no model call; the dev provider is the real Claude): proposal, notices and current values rendered; Use ticked fields saved three fields, the hand-written headline kept and the link reduced to its label; three categories assigned; every audit entry named run 462; an empty source refused under the box with no run recorded; Settings shows the no-approval sentence. Before the demo: publish the content draft prompt in Settings (a task with no published prompt is refused by run_task), and the real model's JSON has not been tried.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Draft with AI on a record page: paste a source, tick channels, and the model drafts the text fields and proposes existing categories with scores and reasons; a person ticks and takes them through the ordinary writes, each naming the run. No approval step (ADR-140 addendum), pasted text only (ADR-141 addendum; task-388 for URLs). Fixed a registry bug that hid new AI tasks. Verified by 19 pytest and 9 vitest cases, all mutation-checked, CI green, and a live check on scratch record 121 with a mock run.
<!-- SECTION:FINAL_SUMMARY:END -->
