---
id: TASK-370
title: AI prepares a variant from a topic
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 20:44'
updated_date: '2026-10-17 07:59'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 201000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** For the November 2026 presentations (docs/business/PRESENTATIONS-2026-11.md), raised by the user 2026-10-11: "prepare variant based on topic". A manager names a topic and the AI proposes a variant: which content records to bind or which categories a slot should draw from, plus a subject and preheader. A person reviews before anything is saved (ADR-140 Assistive mode).

**Design questions for its final-design pass.** Whether it proposes hand-bound records, slot configuration, or both; how it uses the catalogue (only ready, published records, as `candidate_query` does); what it writes and how the proposal is shown; budget (ADR-144). Builds on the subject suggestion in React and on realistic demo content (task-71).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Share the machine-takeable conditions of candidate_query (brand, active, machine ready, ready for the channel, a latest published version, language) in decision/strategies/base.py so the task reads exactly what a slot may take. 2. AI task variant_from_topic (no held form): refuses before the call for a non-email variant, a variant with content blocks (anything but the envelope and decorative modules), an empty or over-long topic, or nothing to choose from; offers the 60 most recently created eligible records with title, description, categories and the blocks each can fill (hero, image block), plus the categories; JSON answer: hero, editorial text, 2 to 4 records, an optional slot (categories), subject, preheader, reasons; drops and names what is outside the offer, doubled, unfillable or not a category. The offer is kept on the run (input_snapshot), the topic is not. 3. POST and GET /campaigns/variants/{id}/topic-proposals (POST is ai.run). 4. POST /campaigns/variants/{id}/build-from-proposal: the ticked parts of one proposal, rechecked (still empty, still takeable), built in order: hero, editorial, alternating image left and right, the slot block (up to 3 picks), then subject and preheader; every audit entry names the run. 5. React: Prepare from a topic panel in the variant editor (AIButton), preview with ticks, editable editorial text, Build the variant. 6. Tests first, mutation-checked, gates, live check with a seeded run. ADR-141 addendum 2026-10-17.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-16 (task-100): the button that starts this model call is frontend/src/components/AIButton.tsx, which already waits visibly and asks once; do not hand-roll a pending state. The server-side guard against two runs at once is task-387.

Built 2026-10-17: backend 463a2da, fix 57c31ed, client dbd5b64; ADR-141 addendum 2026-10-17 in 463a2da. Final design, decided with the user one question at a time: records plus a slot when the model judges it fits; only what a slot may take (published, ready for email, machine ready, in the variant language or none), the 60 most recently created; offered for an empty email variant only (the envelope and decorative modules do not count); the user fixed the shape: hero first, editorial second (its text written by the model), then two to four records in alternating image left and right blocks, the slot block continuing it (up to 3 picks, the model choosing its categories), subject and preheader; one preview with ticks and the editorial editable, then Build the variant; no approval step. Code: decision/strategies/base.py takeable() now shared by candidate_query and the task; backend/app/ai/tasks/variant_from_topic.py; backend/app/campaigns/from_topic.py (everything checked before anything is written); POST and GET /campaigns/variants/{id}/topic-proposals (POST is ai.run), POST .../build-from-proposal; composition preparable_from_topic. The offer is kept on the run, the topic is not. Found in the live check and fixed (57c31ed): runs_for_target filtered by target only, so a topic run showed in the subject panel and the Jinja history as an unreadable suggestion; it now takes the task key. Tests: backend/tests/test_variant_from_topic.py (19) and the applied-suggestion regression; frontend TopicProposal.test.tsx (6) plus two editor cases; 24 backend and 13 client mutations, all killed after sharpening three tests. Full pytest, Ruff, vitest, tsc, eslint, build, CI green. Live check on scratch campaign 18, variant 24, with a proposal made by the real code and the model call stubbed in-process (59 records offered from the dev catalogue): the preview listed hero, editorial, three alternating blocks, the slot (City, Food), subject and preheader; Build the variant made hero, editorial, image left, right, left and the slot block on the right, wrote subject and preheader, and every audit entry named run 469; the panel then disappeared. Before the demo: publish the Variant from a topic prompt in Settings; the real model has not been tried.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Prepare from a topic in an empty email variant: the model proposes a hero, an editorial text, two to four records in alternating image blocks and optionally a slot by categories, plus subject and preheader, only from content a machine may take; a person ticks, edits the editorial and builds it in one checked step, every entry naming the run. ADR-141 addendum 2026-10-17. Fixed the subject panel listing other tasks runs. Verified by 20 pytest and 8 vitest cases, all mutation-checked, CI green, and a live check on scratch variant 24.
<!-- SECTION:FINAL_SUMMARY:END -->
