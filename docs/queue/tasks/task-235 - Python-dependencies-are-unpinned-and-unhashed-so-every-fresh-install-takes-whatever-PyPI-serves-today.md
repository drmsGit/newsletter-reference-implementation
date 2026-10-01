---
id: TASK-235
title: >-
  Python dependencies are unpinned and unhashed, so every fresh install takes
  whatever PyPI serves today
status: To Do
assignee: []
created_date: '2026-10-01 21:26'
labels:
  - backend
  - needs-adr
dependencies: []
type: decision
ordinal: 300200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Decision] — the Python side has no version pins, no lockfile and no hashes, while the frontend has all three.** `backend/requirements.txt` is nine bare names (fastapi, uvicorn, psycopg2-binary, sqlalchemy, jinja2, css-inline, pytest, httpx, python-multipart). A fresh install resolves the newest version of each plus roughly twenty transitive packages, and nothing records or verifies what came down. Compare `frontend/package-lock.json`: 176 packages, every one from registry.npmjs.org with an integrity hash, one install script (`fsevents`, macOS-only). **Why this is now urgent (2026-10-01 dependency sweep):** the AI-hallucinated-package-name attack (slopsquatting) works precisely because a name in a requirements file is installed on trust. It has already happened here once by accident: `requirements.txt` line 8 read `httpx2` (see [[task-198 - three-one-line-deployment-defects.]], fixed to `httpx`), and `backend/venv` still holds `httpx2 2.5.0`, `httpcore2 2.5.0` and `truststore` from 2026-07-03, installed directly (REQUESTED marker) and imported by nothing. It happened to resolve to a real package from the same author; it could as easily have resolved to a hostile one. **Open design questions the ADR must settle:** which lock tool (pip-compile, `uv pip compile --generate-hashes`, or another); whether install uses `--require-hashes`; how pytest and other dev-only packages split into a separate dev requirements file; that `pydantic` and `markupsafe` are imported directly by our code but only arrive transitively and should be declared; and who reviews a lock diff when a transitive package changes. Not decided here, and per CLAUDE.md it needs an ADR before any implementation. Full inventory of what is imported and installed, with per-package notes, was produced in the 2026-10-01 session. Related: [[TASK-105 - There-is-no-`.github-`-no-linter-no-type-checking-no-dependency-or-secret-scanning.]] (CI vulnerability scanning needs a lock to scan).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An ADR records the chosen lock tool, the hash-verification policy, and the runtime/dev requirements split
- [ ] #2 The ADR states how a lock diff is reviewed when a transitive package appears or changes
- [ ] #3 Directly imported packages (pydantic, markupsafe) are declared in the chosen manifest
- [ ] #4 A clean venv built from the lock with hash verification passes the test suite
<!-- AC:END -->
