---
id: TASK-26
title: >-
  `frontend/package.json` pins `typescript` to `^5` and must not be upgraded to
  7 until `openapi-typescript` supports it.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - frontend
dependencies: []
priority: parked
type: bug
ordinal: 102600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🟡 **[Bug] — P3, a pin that exists to work around someone else's incompatibility and will be forgotten.** **`frontend/package.json` pins `typescript` to `^5` and must not be upgraded to 7 until `openapi-typescript` supports it.** npm resolved `typescript@^7` as latest during the 2026-09-20 scaffold and `npm run generate:client` died immediately on `TypeError: Cannot read properties of undefined (reading 'createKeywordTypeNode')` — `openapi-typescript@7.13.0` calls `ts.factory`, which TypeScript 7 (the Go rewrite) no longer exposes the same way. Our own `tsc -b` is fine on 7; it is the generator that is not. **Why this matters more than a version pin usually does:** the generator is what makes [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] point 4 true, so "the contract cannot silently fork" rests on it running at all. A well-meaning dependency bump to TypeScript 7 does not fail the build — it fails `check:contract`, and only when somebody runs it. **Fix:** watch `openapi-typescript` for TS 7 support, then unpin; until then the pin is load-bearing and the comment in the commit message is the only thing saying so. Source: React client scaffold, 2026-09-20.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 88, section "Bugs", position 26 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
