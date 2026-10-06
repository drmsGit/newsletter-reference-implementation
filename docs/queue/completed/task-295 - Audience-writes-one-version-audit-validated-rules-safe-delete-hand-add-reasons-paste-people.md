---
id: TASK-295
title: >-
  Audience writes: one version, audit, validated rules, safe delete, hand-add
  reasons, paste people
status: Done
assignee:
  - '@claude'
created_date: '2026-10-06 19:59'
updated_date: '2026-10-06 20:32'
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
- [x] #1 Every audience write states the group's version and is audited
- [x] #2 Rules are validated (unknown fields refused; a category needs a score > 0; language and status take several values); existing scoreless category rules fixed once
- [x] #3 Deleting a group a send uses is refused 409 naming the sends
- [x] #4 Hand-adds record a reason and who added them; people can be pasted by identifier or email with a report first
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first (tests/test_audience_writes.py): version and audit on create/rename/rule/member/delete, stale refused on every kind of write, a rule or member write moving the group's version; rules refused by field (unknown, category without/zero/negative score, score without category), several values, an older single value; delete refused when a send uses the group, an unused one audited; hand-add reason and author, optional reason; paste preview and apply (identifiers, emails, separators, repeats, not found, not agreed, nobody created, the 5,000 cap); the values route; migration 0035; the Jinja forms audited and the in-use refusal.
2. Migration 0034 (member reason, added_by) applied before any .py edit; migration 0035 (Python, dry-run by default) for scoreless category rules.
3. audience/service.py: UNSET, touch, check_version (the composer's refuse_stale), GroupInUse, CriteriaInvalid + normalise_criteria, multi-value find_by_criteria, criteria_values, parse/preview/apply paste, versioned writes. router.py: If-Match, record_write audit, 409/422 shapes, partial PATCH, label clearing, new routes before /{group_id}. frontend/router.py (Jinja): the same audit, the in-use refusal.
4. Mutation-check, suite, contract, live check on a scratch audience.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Choices within the design: the version check reuses the composer's refuse_stale and IF_MATCH/_expected (as the content router does); the rule check lives in the service so the JSON routes, the Jinja forms and suggested rules share it; 'who' prefers the authenticated principal and falls back to the Jinja session summary; the paste re-reads the list on apply, so what is added is what is true then; bulk add (ids and criteria) is audited under audience_group.people_pasted with a 'by' field; a no-op hand-add (already in) records nothing. Two older tests posted "category_ids": [1] — a key no rule understands, stored silently until now — and were corrected: the check found its first typo.
The API server stopped while migration 0035 sat unapplied (ADR-181 refuses to start); restarted after applying.
Validation: 21 tests, failing first (19 of 20 before the code; the older-single-value test passes by design; the Jinja test added after); 19 mutants all caught (one survivor — only the first language matching — led to a second language in the fixture). Backend 1416, client 196, types regenerated (new routes and fields), contract matches. Dev: migration 0035 found 0 scoreless category rules; applied. Live on a scratch audience 'task-295 live check' (deleted after): create 201, rename-only kept the description, a scoreless category 422, a two-language rule 201, a stale write 409, criteria values listed, paste preview (2 to add, 1 not found), delete 204; four audit entries (created, updated, rule_added, deleted).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Every audience write now states the group's version (one for the whole group, moved by any rule or member write) and is audited on both planes; rules are checked — unknown fields refused by name, a category always with a score above 0, language and status taking several values; a group a send uses is refused with the sends named instead of a 500; a hand-add records an optional reason and who added it (migration 0034); a pasted list of identifiers or email addresses gets a report before anything is added; a route offers the languages and statuses to choose from; renaming changes only what is sent; migration 0035 fixes any scoreless category rule (none on dev). Verified by 21 tests, 19 caught mutants, both suites, the contract and a live check on a scratch audience.
<!-- SECTION:FINAL_SUMMARY:END -->
