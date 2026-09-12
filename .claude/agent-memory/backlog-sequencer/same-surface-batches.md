---
name: same-surface-batches
description: File-level batches, verified against the tree 2026-09-12. Line counts measured, not quoted.
metadata:
  type: project
---

Measured line counts: `app/frontend/router.py` 2927, `app/auth/service.py` 623,
`app/audience/service.py` 503, `app/delivery/service.py` 433, `app/auth/router.py` 281,
`app/providers/service.py` 209, `app/snapshots/service.py` 169, `app/insight/service.py` 169,
`app/decision/service.py` 99.

**B1 — `app/delivery/service.py`, one function.** P0 consent gate, P1 parent-status
aggregation, typed exceptions replacing `except ValueError` (:383-387), per-delivery
artifact package, N+1 batching. All inside `send_send_instance()` :296-433.
Crosses ADR-163 / ADR-162 / ADR-161.

**B2 — `app/auth/` cluster.** Gate 4b disclosure (`service.py:310-311` -> `router.py:63-76`),
`+`-address quoting (`router.py:79,107-112`), enumeration oracle (`router.py:51-81`, 0 loc
after 4b), `auth_enforced` default (`dependencies.py`), CSRF, login-code rate limiting,
double session resolution (`main.py:227` + `dependencies.py:94`), session/login-code
cleanup (ADR-154), `current_user` 3-loc deletion. Gates 4 and 4b in one load.

**B3 — `app/frontend/router.py` (2927 loc, busiest file).** CSRF tokens across 43 write
routes, signal-weight write (:220) and display (:81), pagination, subject/preheader
handling, image picker, AI progress. The CSRF pass is the reason to batch: it touches
every write route once.

**B4 — recipient/consent surface (ADR-163 migration footprint, 10 files).**
`app/recipients/{models,service,db_models,router}.py`, `app/decision/service.py`,
`app/audience/service.py`, `app/templates/{recipients,recipient_detail}.html`,
`scripts/seed_demo_data.py`, `scripts/reset_all_data.sql`.

**B5 — snapshot/artifact surface.** `app/snapshots/{service,models,db_models}.py` +
seed script. Atomicity bug + `html_*` -> `artifact_*` + storage medium + `render_context`
gaps (overrides, merge-context). Crosses ADR-062 / ADR-005 / ADR-162.

**B6 — settings grid.** `app/settings/service.py`, `app/insight/{service,signals}.py`,
`app/frontend/router.py`, `app/templates/settings.html`. Weight no-op (+3 loc), half-life,
channel weights (ADR-164 §10), spend cap, model selection.

**B7 — providers surface.** `app/providers/{router,service}.py` + adapters.
Unauthenticated `POST /provider/events` (:17-32), webhook fail-open, click attribution
(`service.py:100-139`), aggregate-feedback table (ADR-164 §4). Crosses ADR-103's
addendum boundary (per-recipient events only).

**B8 — `app/database.py`, six lines, two backlog items from different scopes.**
The hard-coded password (in-beta, BETA-SCOPE's deployment-bundle exception) and the
engine-at-import defect (out-of-beta, the test-DB Needs-ADR) are lines 4 and 6 of the
same file. Batch regardless of scope; touching it twice is the only wrong answer.
`requirements.txt` `httpx2` and the `Secure` cookie flag ride along as the same
"publishable repo" pass.
