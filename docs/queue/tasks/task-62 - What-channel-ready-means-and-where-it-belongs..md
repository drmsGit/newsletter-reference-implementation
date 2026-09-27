---
id: TASK-62
title: 'What "channel-ready" means, and where it belongs.'
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 201500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — read this before building channel-readiness filtering, or the same mistake returns.** **What "channel-ready" means, and where it belongs.** [[ADR-160 — Channel Model and Composition]] point 3 says decision slots filter candidates to channel-ready records through the existing `candidate_filter_fields`, and [[ADR-161 — Channel Execution Shapes]] point 7's rider defines catalogue readiness as **"push fields not empty"** — not a length check and not a provider check, so the catalogue stays independent of provider configuration. **Neither is built.**

  **It was briefly built in the wrong place, on 2026-09-17, and the user's objection is the specification for doing it right.** A "ready" badge was put on the content record's channel tab. Three things were wrong with it: it was inconsistent (push had one, email did not); it **asserts a status the manager alone grants** — a record is usable once it is *active* and has a *frozen version*, so a badge saying "ready" beside an inactive draft is simply false; and, decisively, **per-record readiness is not well defined**, because `required` belongs to a **module's** manifest variable rather than to the record. A record with no `headline_medium` cannot fill `single_stack` and fills `cta` perfectly well — the user's own example being that half the email fields may be exactly right for a particular layout. "Ready" has no answer until a module is named.

  **So the filter belongs on the decision slot, where a module IS in scope**, and it should be expressed as "candidates that can fill *this* module on *this* channel" rather than as a property stamped on the record. The record page now states only what is written and what is not, with no verdict. When this is built, the interaction with `status == "active"` and with a frozen version has to be settled too — those are the real gates on use, and a candidate filter that ignores them would offer drafts to the engine. Source: user, 2026-09-17.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 180, section "Features", position 15 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
