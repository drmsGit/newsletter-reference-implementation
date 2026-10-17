---
id: TASK-369
title: AI translates a content record into another language
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 20:44'
updated_date: '2026-10-17 07:21'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** For the November 2026 presentations (docs/business/PRESENTATIONS-2026-11.md), raised by the user 2026-10-11: "translate content". A manager asks for a content record in another language; the AI drafts the translated fields and a person reviews them.

**Design questions for its final-design pass.** Where a translation lives: a new record linked to the original, or a language version of the same record — recipients have a language, brand profiles exist once per language (ADR-194 point 6), and nothing models a record's language today. Which fields are translated (text, rich text; never URLs). How a translation stays honest when the original changes. Budget and prompt (ADR-144).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Migration 0052: content_records.language (null = not set), translation_of_id (FK, ON DELETE SET NULL), translated_from (JSON: the original text the translation was made from); unique (translation_of_id, language). 2. Language on a record: chosen from the brand profile languages or not set (PATCH, field-level refusal), locked while linked; the detail carries the choices, the lock reason, the original, the translations and whether the original changed since. 3. candidate_query: only records in the slot variant message language or not set (message_language, ADR-199 point 4). 4. AI task content_translate (no held form): translates title, description, text and rich-text fields and alt text, JSON in and out; links and placeholders must come back unchanged or the field keeps the original text with a notice. 5. POST /content/{id}/translations {language}: checks (an original, language set, target a brand profile language, not its own, none yet), content.manage checked in the route besides ai.run; creates the record (copied links, images and categories with scores; unpublished, not ready, not machine ready), audits it naming the run. 6. POST and GET /content/{id}/retranslations on a translation: a proposal in the content-draft shape, taken with ticks; taking from a run made while the original was unchanged marks it up to date. 7. React: Language choice in Details; Translations section (list, Translate into ..., AIButton, opens the new record); on a translation, the AI banner, the changed notice and Translate again with the Proposal from ContentDraft. 8. Tests first, mutation-checked, all gates, live check on scratch data with a seeded run. ADR-200 and ADR-140 addendum 2026-10-17.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-16 (task-100): the button that starts this model call is frontend/src/components/AIButton.tsx, which already waits visibly and asks once; do not hand-roll a pending state. The server-side guard against two runs at once is task-387.

Built 2026-10-17: backend 8452c56, client 8603fb6; ADR-200 and the ADR-140 addendum 2026-10-17 in 8452c56. Codex handoff first: its passing partial-failure retry test for task-368 was brought in as b18eadd. Final design, decided with the user one question at a time: a translation is a new linked record (P2-F2, one variant per language, kept); slots pick only records in the variant message language or with none; a record language is chosen from the brand profile languages or not set, and locked while linked; translating needs the original language set first; the first translation is created and reviewed on its own page; a changed original is named per field with Translate again, taken with ticks; no approval step. Code: migration 0052 (content_records.language, translation_of_id, translated_from; ai_runs.input_snapshot); backend/app/ai/tasks/content_translate.py; backend/app/content/translation.py; POST /content/{id}/translations (ai.run in policy, content.manage checked in the route), POST and GET /content/{id}/retranslations; PATCH /content/{id} takes language; candidate_query filters by message_language. A field whose placeholders or link addresses came back changed keeps the original text and stays listed as changed. Per field rather than by timestamp, because updated_at also moves on readiness and machine-ready edits. Also declared migration 0051 default on expression_entries.languages in the model (schema check). Tests: backend/tests/test_content_translation.py (16) and frontend Translations.test.tsx (9); 22 backend and 14 client mutations, all killed after removing one redundant guard and one redundant fallback. Full pytest, Ruff, vitest, tsc, eslint, build, CI green. Live check on scratch data (a SCRATCH task-369 Deutsch profile in the Default brand; original 123, translation 124, made through the real service code with the model call stubbed in-process, no paid call and no prompt published): the original shows English locked with its reason and lists the German translation; editing its headline made the translation name Headline as changed; a fresh translation (run 466) started with only Headline ticked; taking it showed Up to date and the audit entry named the run. Found in the live check and fixed: a fresh translation started with nothing ticked. Before the demo: publish the Content translation prompt in Settings, and create a German brand profile in the demo brand. Left as found: the schema check reports an index on delivery_executions(provider_message_id) that only the database has (not from this task).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A record has a language (brand profile languages or not set, locked while linked); slots pick only their variant language or none; Translate with AI makes a linked record in another language (links, images, categories copied; unpublished, not ready); a changed original is named per field and Translate again is taken with ticks. ADR-200 and an ADR-140 addendum. Verified by 16 pytest and 9 vitest cases, all mutation-checked, CI green, and a live check on scratch records 123/124 with the model stubbed.
<!-- SECTION:FINAL_SUMMARY:END -->
