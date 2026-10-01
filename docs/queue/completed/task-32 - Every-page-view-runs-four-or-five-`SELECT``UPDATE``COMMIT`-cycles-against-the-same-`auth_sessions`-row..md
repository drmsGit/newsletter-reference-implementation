---
id: TASK-32
title: >-
  Every page view runs four or five `SELECT`+`UPDATE`+`COMMIT` cycles against
  the same `auth_sessions` row.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-01 21:10'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 103200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2, and now the LAST open dependency [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] names before its first screen** (accepted 2026-09-20; the other two it listed closed with ADR-172). The React client multiplies it by roughly an order of magnitude.** **Every page view runs four or five `SELECT`+`UPDATE`+`COMMIT` cycles against the same `auth_sessions` row.** `user_for_token` (`auth/service.py:767-792`) writes `last_seen_at` and commits on every call, and it is called from `attach_current_user`, from `current_brand_summary` → `resolve_session_brand`, again for the `switchable` count, again for `brand_options` when the switcher renders, and once more from `enforce_policy` — across two different sessions, so a user with several tabs open already serialises on that row's lock. **The property being paid for is real and must survive the fix:** the session's `brand_id` is a cache revalidated against the grant table on every resolution, which is what makes a revoked grant stop working immediately. **Fix:** resolve once into `request.state`, and write `last_seen_at` only when it has moved by more than a minute. **Why before the frontend:** a Jinja page is one request; a React screen is five to fifteen, and this is write amplification rather than read. Source: [[Interview Prep - Auth, Permissions, Machine Principals]] → Q7.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 100, section "Bugs", position 32 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The write half, which was the problem: last_seen_at is written at most once a minute, so a request went from 4 UPDATE + 4 COMMIT on the session row to 0 (measured). The idle timeout still slides at minute precision; brand revalidation is untouched. The read half (resolve once per request) was deliberately not done: 5 indexed point-SELECTs remain, and removing them means 24 call sites for no lock gain. Three tests incl. a whole-request statement count; the original and a never-extend mutant each fail; 778 pass.
<!-- SECTION:FINAL_SUMMARY:END -->
