---
id: TASK-295
title: >-
  Audience writes: one version, audit, validated rules, safe delete, hand-add
  reasons, paste people
status: To Do
assignee: []
created_date: '2026-10-06 19:59'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200388
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-293 interview (2026-10-06, with the user); recorded in [[Audience Write Surface - final design pass]] (decisions 2, 3, 5, 6, 8, 10 and the pass's own choices) and [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]] points 2 and 3. First of four build tasks; the React editor (build 3) depends on it.

**Today** (`backend/app/audience/router.py`, `service.py`): no audience write takes a version token or records an audit entry; `PATCH /{id}` replaces the whole group (a missing description clears it); rule criteria are an untyped dict (unknown keys stored, a category without `min_score` matches everyone); deleting a group a send uses fails the foreign key at commit and answers an unhandled 500 (`delete_group`, `service.py` ~137; `SendInstanceDB.audience_group_id` has no ondelete); a hand-add records no reason or author (task-217); a rule's label cannot be cleared.

**Build:**
- **One version for the group:** `audience_groups.updated_at` is moved by any write to the group, its rules or its members; every write states it in If-Match and a stale one is refused 409 (ADR-180 point 2). No token, no check, as on the composer (the Jinja forms).
- **Audit on every write** (ADR-153 point 4): group created/updated/deleted, rule added/changed/removed, member added/removed (with the reason), paste applied (counts).
- **Rename is a partial update.** A rule's label can be cleared.
- **A typed criteria schema:** `language` and `status` as lists of values ("is one of", ADR-188 point 1), `category_id` with `min_score` required and > 0 (default 1.0 offered by the client); unknown fields refused by name (422).
- **A one-time fix of existing rules with a category and no score** (they match everyone today): set to 1.0, audited as a system change; report how many on the dev data.
- **Delete:** refused 409 when any send (planned or sent) uses the group, naming the sends; otherwise deletes with its rules and members, audited.
- **Hand-adds record a reason (optional) and who added them** (migration on `audience_group_members`); `POST /{id}/members/{recipient_id}` takes an optional body.
- **Paste people:** a preview route (identifiers or email addresses, any separator, up to 5,000) answering added / already in / not found (listed) / not agreed on a channel; then an apply route with one optional reason. Nobody is created.
- **Distinct values** for language and status among the brand's recipients, for the editor's choices.

Tests per convention, mutation-checked; `audiences.manage` / `audiences.pin` permissions unchanged.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every audience write states the group's version and is audited
- [ ] #2 Rules are validated (unknown fields refused; a category needs a score > 0; language and status take several values); existing scoreless category rules fixed once
- [ ] #3 Deleting a group a send uses is refused 409 naming the sends
- [ ] #4 Hand-adds record a reason and who added them; people can be pasted by identifier or email with a report first
<!-- AC:END -->
