---
id: TASK-311
title: >-
  Should unused imports (Ruff F401) block CI? — a widening of ADR-190's blocking
  set
status: To Do
assignee: []
created_date: '2026-10-08 22:46'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 305400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Decision: should "unused import" (Ruff F401) block CI?** Found by the code-slimmer sweep of 2026-10-08 (D6). The ADR-190 decision is to widen the blocking set; `backend/ruff.toml` says widening is a decision, not a cleanup.

**Why it matters.** The list-paging work (task-88, ADR-185) left six dead service functions and about a dozen unused router imports behind for weeks. F401 would have flagged them at the commit that orphaned them. They were removed on 2026-10-08 (commit 5a2d653), but nothing stops the next refactor leaving the same residue.

**What blocking would need first.** On 2026-10-08, after that cleanup:
- `backend/app/` outside the Jinja router is clean.
- `backend/main.py` has 31 hits. They are deliberate: model imports so `create_all` knows every table. Only a few carry `# noqa: F401`. They need marking, or rewriting as `import app.x.db_models  # noqa: F401`.
- The frozen Jinja router (`backend/app/frontend/router.py`) has 8. Its freeze test pins routes, not content, so removing them is allowed.
- `backend/tests/` has 36 and `backend/scripts/` has 2.

**A related report-only fix.** B008 is about 300 hits, all FastAPI `Depends`/`Query` defaults, all false positives. They drown the report-only output CI prints. A `[lint.flake8-bugbear] extend-immutable-calls` entry for `fastapi.Depends`, `fastapi.Query`, `fastapi.Header` and similar would make that report readable. It changes no blocking behaviour.

**The options:**
- (a) Make F401 blocking after clearing the hits above. Record it as an ADR-190 addendum, through the adr-author agent.
- (b) Keep it report-only, and rely on the next slimmer sweep.
- (c) Block F401 in `app/` only, excluding tests and scripts.
<!-- SECTION:DESCRIPTION:END -->
