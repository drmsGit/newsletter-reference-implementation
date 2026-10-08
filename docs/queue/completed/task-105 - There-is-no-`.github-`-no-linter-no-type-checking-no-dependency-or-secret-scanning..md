---
id: TASK-105
title: >-
  There is no `.github/`, no linter, no type checking, no dependency or secret
  scanning.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:57'
updated_date: '2026-10-08 20:36'
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
- [x] #1 One CI workflow runs the backend suite against a Postgres service container and the client's type check, tests, build and contract check
- [x] #2 Ruff runs on the backend and ESLint (typescript-eslint, react-hooks, jsx-a11y as warnings) on the client, informing review rather than forcing a cleanup
- [x] #3 Dependency vulnerability scanning and secret scanning run
- [x] #4 The workflow runs backend/scripts/check_installed.py after installing from the locks (task-236's check)
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

2026-10-08, from task-236: the installed-packages check exists and runs locally with one command - backend/venv/bin/python backend/scripts/check_installed.py (exit 1 on any difference between what is installed and the ADR-189 locks, Python and npm). The workflow this task builds runs it as a step after installing from the locks (pip install --require-hashes -r requirements.txt -r requirements-dev.txt; npm ci), with --python pointing at the CI interpreter if there is no backend/venv. task-236's acceptance criterion 4 ("wired into CI, or added to the workflow task-105 creates") is handed over here.

Built 2026-10-08. Asked of the user one at a time, each with the recommendation:
1. Linters block on a small set of real-defect rules and report the rest (not ~800 style fixes, not report-only).
2. Secrets: full history scanned once locally (gitleaks 8.30.1 via Homebrew: 708 commits, nothing found; backend/.env never scanned), then every push in CI.
3. Vulnerabilities: every push and weekly; block only on what ships, report dev tooling; fix by upgrading the one package, or an ignore with a reason and a date.
Recorded in ADR-190 (adr-author) and a playbook entry.

What landed (commits fbb2888 to a5f20e7):
- backend/ruff.toml: F821, F811, F822, F823, F841, F541 block; CI also runs E,F,W,B,I,UP,SIM with --exit-zero.
- frontend/eslint.config.js: ESLint 9 (10 is out; jsx-a11y 6.10.2 supports up to 9) recommended + typescript-eslint recommended + react-hooks rules-of-hooks as errors; exhaustive-deps and jsx-a11y as warnings; rest-sibling idiom allowed. npm run lint.
- Dev locks: ruff and pip-audit (24 new packages, provenance in the commit); ESLint and plugins (246 npm packages, all registry.npmjs.org with integrity, no install scripts).
- .github/workflows/ci.yml: backend (venv from hashed locks, Ruff, suite on Postgres 16, schema export, pip-audit), frontend (npm ci, lint, build, tests, npm audit), contract-and-installs (types from the exported schema equal schema.d.ts - byte-identical to generating from the running API; check_installed.py), secrets (gitleaks container, whole history). Push, pull request, Mondays 06:00 UTC, manual. Actions pinned to commit SHAs. INITIAL_ADMIN_EMAIL set to a test address for CI's test database; pytest -rs lists skips.
- backend/scripts/export_openapi.py for the contract check.

Found and fixed by the new checks:
- A real bug (Ruff F811): RecipientPreference declared twice, so GET /recipients/{id}/preferences and POST /recipients/preferences answered 500; the signal shape is RecipientSignal now, with tests/test_recipient_preferences.py.
- Ruff's automatic fix removed the wrong import in the test send (the call-time one a test relies on); the suite caught it, the top-level one went instead.
- pip-audit on the runtime lock: starlette 1.2.1 (PYSEC-2026-248, -249) -> 1.3.1, anyio 4.13.0 (PYSEC-2026-4024, -4025) -> 4.14.2.
- CI's first runs on GitHub: greenlet (SQLAlchemy needs it on Linux x86-64 only) was missing from a lock compiled on a Mac - declared; the approval-seed test assumed an admin existed - it brings its own now, and CI names a first admin so 9 admin-dependent tests stop skipping.

Reported, not blocking: 7 jsx-a11y autoFocus warnings (for the accessibility session); one high npm finding in dev tooling (source-map-js via Vite, already in the lock before) - a candidate for a one-package upgrade.

Verified: run on GitHub green in all four jobs (1495 passed, 1 skipped by design: the real-install test in a job without the client's install; the contract job runs that check directly). GitHub notes ubuntu-latest moves to Ubuntu 26 from 2026-10-19; nothing here depends on the OS version beyond Postgres 16 as a service.

Not done here, by the task's own rule: mypy (later, gradually), Vulture (by hand once).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The repository now has CI: one GitHub Actions workflow runs the backend suite on Postgres, the client's type check, build and tests, the API contract check, the installed-packages check, Ruff and ESLint on a small blocking set of real-defect rules (everything else reported), vulnerability scans that block only on what ships, and a secret scan of the whole history - on every push and weekly. Decided with the user and recorded in ADR-190. Its first runs found and fixed a real API bug, two vulnerable runtime libraries, and two things that only failed outside this Mac. Green on GitHub in all four jobs.
<!-- SECTION:FINAL_SUMMARY:END -->
