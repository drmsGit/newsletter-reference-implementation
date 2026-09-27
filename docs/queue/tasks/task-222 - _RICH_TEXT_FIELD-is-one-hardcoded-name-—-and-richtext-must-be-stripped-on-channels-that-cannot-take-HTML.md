---
id: TASK-222
title: >-
  _RICH_TEXT_FIELD is one hardcoded name — and richtext must be stripped on
  channels that cannot take HTML
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies:
  - TASK-219
priority: parked
type: feature
ordinal: 208700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** `_RICH_TEXT_FIELD` is one hardcoded name, so `body_long` gets no formatting (`rendering/service.py:37`). From the resolution of question 2.5:

**The defect was the hardcoded name, and questions 2.10 and 2.4 had already fixed it.** `_RICH_TEXT_FIELD = "body_medium"` is a single constant, so `body_long` — which 2.10's size vocabulary requires — would silently get no formatting at all. It becomes `type: "richtext"` in `fields.json`, declared once.

**One consequence that stops being luck and becomes a rule.** Rich text emits `<strong>` and `<br>`, which are meaningless in a push notification. That is safe today only by accident of layout: the email and push paths diverge before this runs, and push happens to use `push_body` rather than `body_medium`. Once `richtext` is a declared type any channel can use, **the renderer must strip rather than emit** — which is consistent with [[ADR-162 — Channel Rendering and Artifacts]] point 2 (*the renderer formats, it never decides*) but has to be written down rather than inherited from a coincidence.

Source: [[Variant Editor - design interview]] → What Cluster 2 produced, gap 13 (Q2.5).

**The declaration half lands with the `fields.json` task this depends on** ([[ADR-177 — A Field Is Defined Once, Required Per Module]] point 3 makes `richtext` a `type`). **What this task carries on its own is the strip-per-channel rule**: a `richtext` field rendered for a channel that cannot take HTML is stripped, not emitted — written down and tested, not left to the current accident of layout.

**Verified against the code 2026-09-27:** `_RICH_TEXT_FIELD = "body_medium"` at `backend/app/rendering/service.py:37`, used at `:328-332`. `body_long` does not yet exist in any manifest or in `backend/app/`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
