---
id: TASK-367
title: AI suggests a subject and preheader in the React client
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 20:44'
updated_date: '2026-10-16 18:05'
labels:
  - frontend
  - backend
dependencies: []
type: feature
ordinal: 200700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** For the November 2026 presentations (docs/business/PRESENTATIONS-2026-11.md). The AI subject and preheader suggestion exists only in the Jinja UI: `POST /ui/campaigns/{id}/variants/{vid}/suggest-subject` (`backend/app/frontend/router.py:1425`). There is a JSON route on the campaigns router (`/campaigns/variants/{variant_id}/suggest-subject`, used by `backend/tests/test_ai_budget_period.py`), but the React variant editor offers nothing. This task gives the variant editor the button, shows the suggestions, and lets a person take one into the subject and preheader.

**Related.** task-100 (progress and double-submit protection for AI calls, wanted with this). task-125 (today's suggestion only works for hand-composed campaigns, which collides with decision slots — its decision is needed before the demo shows both). The three new AI abilities wanted for the demo build on this: create and categorise content, translate content, prepare a variant from a topic.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-16 (f128f8a). Final design: Suggest with AI sits under the envelope fields, only when the channel has an envelope module; disabled and reading Asking the model… while the request runs, so it cannot be sent twice (this covers the double-submit part of task-100 for this button only). The newest run is read back from GET /campaigns/variants/{id}/suggestions, with notices, the raw reply when nothing parsed, and tokens. Use this saves subject and preheader together through the ordinary variant save (If-Match), with applied_suggestion_run_id; the variant.updated audit entry then carries applied_suggestion and ai_run_id, only when the run is this variant's (backend/app/campaigns/router.py _applied_suggestion). Found during the pass: the Jinja page never offers Use this on a held run (it redirects to the approval), and an editor showing the newest run on load would have. SuggestionRun gained pending_action_id (backend/app/ai/service.py suggestions_for_variant, matched on the ai_subject_apply action key and ai_run subject); such a run links to its approval and has no Use this. A 409 detail of the form {reason, message} now reaches the screen as its message (frontend/src/api/session.ts HttpError.from). Tests: backend/tests/test_applied_suggestion.py (4) and six cases in VariantEditor.test.tsx; every guard mutation-checked (7 client, 4 server, all killed). Full pytest, Ruff, vitest, tsc, eslint, build green; CI green on b97c7f3. Live check on scratch variant 23 with a seeded mock-provider run (no model call: the dev database has the claude provider switched on, so Suggest with AI was not pressed): the run, its notice and Use this rendered; both fields saved in one write; the audit entry named run 460. Separately fixed (b97c7f3): five inline forms were p elements holding TextField or Choice divs.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Suggest with AI in the React variant editor: one request at a time, the newest run shown with notices and tokens, Use this saves subject and preheader together and the audit entry names the run. Held runs link to Approvals and offer no Use this (new SuggestionRun.pending_action_id). Verified by 4 pytest and 6 vitest cases, all mutation-checked, full gates and CI green, and a live check on scratch variant 23 with a mock run.
<!-- SECTION:FINAL_SUMMARY:END -->
