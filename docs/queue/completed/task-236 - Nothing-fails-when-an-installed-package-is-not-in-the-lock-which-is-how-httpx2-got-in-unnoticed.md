---
id: TASK-236
title: >-
  Nothing fails when an installed package is not in the lock, which is how
  httpx2 got in unnoticed
status: Done
assignee:
  - '@claude'
created_date: '2026-10-01 21:26'
updated_date: '2026-10-08 19:44'
labels:
  - backend
dependencies:
  - TASK-235
type: chore
ordinal: 205810
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🟠 **[Chore] — a check that would have caught `httpx2`.** `backend/venv` holds `httpx2 2.5.0`, `httpcore2 2.5.0` and `truststore 0.10.4`, installed 2026-07-03 from the `requirements.txt` typo `httpx2` (fixed in task-198). Nothing noticed for three months because no step compares what is installed with what is meant to be installed. The same shape applies to npm: `frontend/package-lock.json` is solid today, but nothing fails if `node_modules` or the lock gains an unreviewed package. **What this is not:** task-105 covers vulnerability and secret scanning, which asks "is a known package known-bad"; this asks "is every installed package one we chose", a different question that a CVE scanner will never answer for a freshly registered malicious name. **Blocked on** TASK-235: there is no Python lock to compare against until the pinning ADR lands. Prefer a check that runs in CI and also locally; if TASK-105 builds the workflow first, add this as a step, and if this lands first, TASK-105 reuses the job. Heuristics worth considering once the lock exists: flag any new package whose name is within edit distance of an existing dependency (httpx2 vs httpx), and any package younger than a threshold on first appearance.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The check fails when an installed Python distribution is not in the lock
- [x] #2 The check fails when an npm package appears in node_modules or the lock without a matching package.json/lock change
- [x] #3 A deliberately added typo-squat-shaped name (for example httpx2) makes the check fail in a test run
- [x] #4 The check runs locally with one command and is wired into CI, or is added to the workflow TASK-105 creates
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-08, commits 2ead7cf, a3746d1, de40e88. No decision needed: it checks against ADR-189's locks.

Verified first: the description's stray httpx2, httpcore2 and truststore were already gone from backend/venv; the rest held (nothing compared installed with locked, for Python or npm).

backend/scripts/check_installed.py, one command (backend/venv/bin/python backend/scripts/check_installed.py), exit 1 on any difference:
- Python: the venv (its own pip list, pip and setuptools included) against requirements.txt + requirements-dev.txt, names normalised (PEP 503): installed but not locked, another version, locked and missing.
- npm: node_modules/.package-lock.json against package-lock.json, named by path so nested copies are told apart; optional builds for other platforms may be missing (24 rolldown and lightningcss bindings on this Mac).
- npm: package.json against the lock's root entry (dependencies and devDependencies): in one and not the other, or another range.
- A name not locked but within two edits of a locked one is called out as a likely typo or squat (httpx2 beside httpx).
Not built: a package-age heuristic (needs a registry lookup at check time).

Its first run found a real difference: the venv's pip was 26.1.1, the dev lock 26.2.1; the venv was re-installed from the locks (pip install --require-hashes ...).

Tests: tests/test_check_installed.py, 12, including the repository's own install checked as it is (skipped where nothing is installed). 13 mutants, all killed after one test was strengthened (a dev-dependency mismatch). Backend suite 1494.

Acceptance criterion 4: runs locally with one command; the CI step is handed to task-105, which now carries it as its own criterion.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
One command now fails when anything installed is not the locked one: the backend venv against ADR-189's locks, node_modules against package-lock.json (optional builds for other platforms aside), and package.json against the lock. A name close to a locked one is called out as a likely typo or squat. Its first run caught a real drift (pip) in the venv, fixed by re-installing from the locks. Verified by 12 tests (13 mutants killed) and the full suite; the CI step is handed to task-105.
<!-- SECTION:FINAL_SUMMARY:END -->
