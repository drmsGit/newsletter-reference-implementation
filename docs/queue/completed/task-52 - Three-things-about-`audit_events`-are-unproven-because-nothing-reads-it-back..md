---
id: TASK-52
title: Three things about `audit_events` are unproven because nothing reads it back.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:56'
updated_date: '2026-10-08 21:32'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — the operator screen's prerequisites, better settled before it is designed than discovered by it.** **Three things about `audit_events` are unproven because nothing reads it back.** ADR-153 point 1's "what did this operator do" screen is enabled, not built, and both read helpers are exercised only by tests. **(1)** `action` is a plain VARCHAR with nothing validating it against the constants, so a typo is invisible until somebody filters on it and gets an empty result they believe. **(2)** `detail` is unvalidated JSON carrying a stated policy — internal identifiers, never contact details (ADR-153 point 5, ADR-154 point 3) — that no test enforces. **(3)** Brand filtering **cannot** be a plain `WHERE brand_id = ?`: sign-in and deactivation rows carry `NULL` forever, so a naive filter silently drops exactly the events ADR-153 point 2 says have no other home. Write-first was the right order and is not what is being questioned — nothing was backfilled, because invented entries would fabricate the evidence the table exists to hold. Retention belongs with the general data-lifecycle Needs-ADR item; count the five indexes on a write-mostly table when it is answered. Source: [[Interview Prep - Channels, Audit]] → B-Q5.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 152, section "Features", position 5 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08 — verified, decided, built (commits 99a9fc2, 456861b; CI green on 456861b).

Verified first: all action names stored on dev were known constants, but they lived in three places (`audit/service.py`, the approval lifecycle constants in `approvals/service.py`, and two plain strings in held actions). Two entries already broke ADR-153 point 5: `variant.unfenced` copied the fence holder's label (an email address for a person) and `content.ready_unmarked` copied `marked_by`.

Decided with the user one question at a time, recorded in the ADR-153 addendum of 2026-10-08 and the playbook decision log:
1. One vocabulary. Every name is a constant in `backend/app/audit/service.py`; `ACTIONS` collects them; `record()` raises ValueError for a name outside it (a caller bug, consistent with record raising for programming errors and swallowing only database failures). The approval names are now `audit.APPROVAL_*` with the short local aliases kept in `approvals/service.py`; `send.fired` and `ai.suggestion_applied` became `audit.SEND_FIRED` and `audit.AI_SUGGESTION_APPLIED`.
2. No email address in a detail. `record()` raises ValueError when any key or value, at any depth, is email-shaped. `campaigns/router.py` unfence now records the fence holder by type and id; `content/service.py` `unmark_ready` no longer returns `marked_by`. Phones are not checked; stored rows are not rewritten.
   Found while building and decided with the user: authored copy is exempt. `COPY_KEYS = {name, title, envelope}`, top-level keys only, so a preheader like "Reply to hello@brand.test" does not fail the save it records.
3. `events_by_actor(..., brand_id=X)` returns that brand's entries plus the actor's brand-less ones (sign-ins, platform settings).

Tests: `backend/tests/test_audit_rules.py` (new), plus assertions in `test_fence.py` (unfence detail is type and id) and `test_channel_readiness.py` (no `marked_by`). Tests that planted names (`marker.written`, the task-23 markers) now add them to `ACTIONS` with monkeypatch. The task-22 database-refusal tests now use an over-long `subject_type` with a valid action, so they still exercise a genuine database refusal. Mutation check: 9 of 9 mutants caught. Full suite: 1525 passed, Ruff blocking rules clean.

Live check (mock provider, scratch data): signed in on the dev app and created the campaign "SCRATCH task-52 audit copy" (campaign 9, variant 15). Saved the variant with the preheader "Reply to hello@brand.test": 200, and the variant.updated entry kept the copy. There is no campaign delete route, so the scratch campaign remains.

Not done here: retention and the index count stay with the data-lifecycle item (task-136); the operator screen itself is not built.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The audit log now enforces what it promised. Action names come from one vocabulary and an unknown name is refused at write. A detail holding an email address is refused (authored copy in name, title and envelope exempt), and the two entries that leaked a person's address now record ids. events_by_actor filters by brand without hiding brand-less entries. Recorded in the ADR-153 addendum of 2026-10-08. Verified by test_audit_rules.py and the updated fence and readiness tests (9/9 mutants caught), the full suite (1525 passed), CI green, and a live save of a scratch variant whose preheader mentions an address.
<!-- SECTION:FINAL_SUMMARY:END -->
