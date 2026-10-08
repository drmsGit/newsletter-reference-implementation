---
id: TASK-105
title: >-
  There is no `.github/`, no linter, no type checking, no dependency or secret
  scanning.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-08 18:59'
labels:
  - backend
dependencies: []
type: chore
ordinal: 205800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Chore] — a public reference implementation with no CI at all is a positioning problem before it is a quality one.** **There is no `.github/`, no linter, no type checking, no dependency or secret scanning.** The first thing a technical visitor does is look for the badge and the workflow file; their absence reads as "hobby" regardless of the 567 tests underneath, which is exactly the gap [[LAUNCH-GATES|Launch gate 1]] is about. **Do:** one workflow running the suite against a Postgres service container, plus Ruff, plus dependency vulnerability scanning and secret scanning. Type checking comes later and gradually — a strict `mypy` over this codebase today would produce a cleanup nobody asked for. **The rule for all of it: the checks inform review, they do not trigger an indiscriminate refactor.** A Vulture pass is worth running once by hand for the signal, not wiring into CI where it will cry wolf. Source: `CODE_QUALITY_RELEASE_POSITIONING_2026-09-19` §4 and §7.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 One CI workflow runs the backend suite against a Postgres service container and the client's type check, tests, build and contract check
- [ ] #2 Ruff runs on the backend and ESLint (typescript-eslint, react-hooks, jsx-a11y as warnings) on the client, informing review rather than forcing a cleanup
- [ ] #3 Dependency vulnerability scanning and secret scanning run
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 360, section "Features", position 58 in that section (top = do next). The description is the original entry, verbatim.

Scope extended by the user 2026-10-08: ESLint for the React client belongs here too. Checked that day:
- frontend/package.json has no ESLint, Prettier or end-to-end runner. The client's checks are tsc (inside npm run build), Vitest with Testing Library against a stubbed server, and npm run check:contract.
- One leftover: frontend/src/shortcuts/Shortcuts.tsx:153 carries an eslint-disable-next-line react-hooks/exhaustive-deps that nothing reads.

The set to wire up:
- typescript-eslint;
- eslint-plugin-react-hooks, which is what that disable comment was written for;
- eslint-plugin-jsx-a11y, whose findings feed the keyboard and accessibility session (deferred by the user 2026-10-05) rather than being fixed one by one.

Same rule as the rest of this task: it informs review and does not trigger a cleanup. jsx-a11y in particular starts as warnings, not errors. End-to-end tests are their own task, filed the same day.
<!-- SECTION:NOTES:END -->
