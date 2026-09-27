---
id: TASK-52
title: Three things about `audit_events` are unproven because nothing reads it back.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
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
<!-- SECTION:NOTES:END -->
