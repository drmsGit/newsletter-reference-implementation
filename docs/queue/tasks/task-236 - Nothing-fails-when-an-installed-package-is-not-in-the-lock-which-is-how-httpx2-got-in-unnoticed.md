---
id: TASK-236
title: >-
  Nothing fails when an installed package is not in the lock, which is how
  httpx2 got in unnoticed
status: To Do
assignee: []
created_date: '2026-10-01 21:26'
labels:
  - backend
dependencies:
  - TASK-235
type: chore
ordinal: 205810
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🟠 **[Chore] — a check that would have caught `httpx2`.** `backend/venv` holds `httpx2 2.5.0`, `httpcore2 2.5.0` and `truststore 0.10.4`, installed 2026-07-03 from the `requirements.txt` typo `httpx2` (fixed in task-198). Nothing noticed for three months because no step compares what is installed with what is meant to be installed. The same shape applies to npm: `frontend/package-lock.json` is solid today, but nothing fails if `node_modules` or the lock gains an unreviewed package. **What this is not:** [[TASK-105 - There-is-no-`.github-`-no-linter-no-type-checking-no-dependency-or-secret-scanning.]] covers vulnerability and secret scanning, which asks "is a known package known-bad"; this asks "is every installed package one we chose", a different question that a CVE scanner will never answer for a freshly registered malicious name. **Blocked on** TASK-235: there is no Python lock to compare against until the pinning ADR lands. Prefer a check that runs in CI and also locally; if TASK-105 builds the workflow first, add this as a step, and if this lands first, TASK-105 reuses the job. Heuristics worth considering once the lock exists: flag any new package whose name is within edit distance of an existing dependency (httpx2 vs httpx), and any package younger than a threshold on first appearance.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The check fails when an installed Python distribution is not in the lock
- [ ] #2 The check fails when an npm package appears in node_modules or the lock without a matching package.json/lock change
- [ ] #3 A deliberately added typo-squat-shaped name (for example httpx2) makes the check fail in a test run
- [ ] #4 The check runs locally with one command and is wired into CI, or is added to the workflow TASK-105 creates
<!-- AC:END -->
