---
id: TASK-235
title: >-
  Python dependencies are unpinned and unhashed, so every fresh install takes
  whatever PyPI serves today
status: Done
assignee:
  - '@claude'
created_date: '2026-10-01 21:26'
updated_date: '2026-10-08 19:33'
labels:
  - backend
  - needs-adr
dependencies: []
type: decision
ordinal: 300200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Decision] — the Python side has no version pins, no lockfile and no hashes, while the frontend has all three.** `backend/requirements.txt` is nine bare names (fastapi, uvicorn, psycopg2-binary, sqlalchemy, jinja2, css-inline, pytest, httpx, python-multipart). A fresh install resolves the newest version of each plus roughly twenty transitive packages, and nothing records or verifies what came down. Compare `frontend/package-lock.json`: 176 packages, every one from registry.npmjs.org with an integrity hash, one install script (`fsevents`, macOS-only). **Why this is now urgent (2026-10-01 dependency sweep):** the AI-hallucinated-package-name attack (slopsquatting) works precisely because a name in a requirements file is installed on trust. It has already happened here once by accident: `requirements.txt` line 8 read `httpx2` (see [[task-198 - three-one-line-deployment-defects.]], fixed to `httpx`), and `backend/venv` still holds `httpx2 2.5.0`, `httpcore2 2.5.0` and `truststore` from 2026-07-03, installed directly (REQUESTED marker) and imported by nothing. It happened to resolve to a real package from the same author; it could as easily have resolved to a hostile one. **Open design questions the ADR must settle:** which lock tool (pip-compile, `uv pip compile --generate-hashes`, or another); whether install uses `--require-hashes`; how pytest and other dev-only packages split into a separate dev requirements file; that `pydantic` and `markupsafe` are imported directly by our code but only arrive transitively and should be declared; and who reviews a lock diff when a transitive package changes. Not decided here, and per CLAUDE.md it needs an ADR before any implementation. Full inventory of what is imported and installed, with per-package notes, was produced in the 2026-10-01 session. Related: task-105 (CI vulnerability scanning needs a lock to scan).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An ADR records the chosen lock tool, the hash-verification policy, and the runtime/dev requirements split
- [x] #2 The ADR states how a lock diff is reviewed when a transitive package appears or changes
- [x] #3 Directly imported packages (pydantic, markupsafe) are declared in the chosen manifest
- [x] #4 A clean venv built from the lock with hash verification passes the test suite
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decided and built 2026-10-08, commit 7b29e4c. Asked of the user one at a time, each answered with the recommendation:
1. pip-tools writes the lock (not uv, not pip lock / pylock.toml): plain pip installs it.
2. Every install checks hashes, locally too; runtime and dev are separate locks, the dev lock compiled against the runtime one.
3. A lock change is its own commit with a provenance check for every new package (PyPI name, established, which direct dependency pulls it in); upgrades one package at a time; CI scans the lock once task-105 builds it.
Settled without asking: pytest and pip-tools in the dev lock; pydantic and markupsafe declared; the first lock pins the versions installed and tested that day (compiled once against a temporary freeze, then again without it so no local path is left in the file - pip-compile keeps existing pins).
Recorded in ADR-189 (adr-author), a playbook entry, and docs/implementation/npm.md (no longer says the backend is unpinned).

Files: backend/requirements.in (11 direct), requirements.txt (22 packages, hashed), requirements-dev.in, requirements-dev.txt (pytest 9.1.1 as tested; pip-tools 7.6.2 with build, pyproject-hooks, wheel, setuptools, pip - provenance in the commit message).

Verified: a new venv built only from both locks with pip install --require-hashes holds exactly the locked packages and passes the backend suite (1483 passed).

Out of date in this entry's description (kept verbatim): the stray httpx2, httpcore2 and truststore are no longer in backend/venv; task-236 should start from that.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The backend's Python dependencies are now locked: pip-tools compiles requirements.in into a requirements.txt with exact versions and hashes for all 22 packages (the versions tested that day), plus a separate dev lock, and every install checks hashes. pydantic and markupsafe are declared. Decided with the user and recorded in ADR-189; verified by building a fresh venv from the locks alone, which holds exactly the locked packages and passes all 1483 backend tests.
<!-- SECTION:FINAL_SUMMARY:END -->
