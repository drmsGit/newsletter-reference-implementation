---
name: cluster2-overrides-campaigns
description: Results of the 2026-08-21 overrides/ + campaigns/ sweep — what is confirmed intentional there, and the reversal residue that is real
metadata:
  type: project
---

Cluster 2 (`backend/app/overrides/` 372 loc, `backend/app/campaigns/` 854 loc)
swept 2026-08-21, read in full. **No dead functions and no dead routes.** What
this cluster carries is **orphaned schema** (columns whose only writers are
`scripts/*.sql`) and **JSON-router/Pydantic drift**.

**Why:** `overrides/` was cut back twice (record pins removed, "Case 2" dropped
— both recorded at `docs/backlog.md:212`, Done 2026-07-15). The code came out
clean; the columns did not.

**How to apply:** if a future sweep touches these dirs, start from schema and
router-payload drift, not from reachability.

Confirmed intentional, never flag:
- **All 5 `/overrides` routes, all 12 `/campaigns` routes.** No in-repo JSON
  caller is normal — documented public surface, ADR-142. `get_content_override`
  and `record_outcome_delta` have no non-router caller *by design*.
- **Lazy/function-local imports in `campaigns/service.py`** —
  `_normalize_for_strategy` (`app.decision.strategies.*`) and `delete_module`
  (`ContentOverrideDB`) both break a **real** cycle: `decision/service.py` and
  `overrides/service.py` each import `campaigns`. Not a style choice here,
  unlike the `frontend/router.py` case.
- **`ContentOverrideDB.reverted_at`** — written by reset, read by no code. It is
  an audit timestamp; that is the job.
- **The `postgresql_where` partial unique index** (`overrides/db_models.py:88`).
  The DB *is* Postgres (`app/database.py:4`), so the index exists and the
  `IntegrityError` branch in `create_content_override` is live. Checked because
  a SQLite backend would have made it a silent no-op.
- **`delete_module` hard-deleting override history** contradicts `overrides.md`
  ("reset keeps history, never a delete") and ADR-041, but it is a **deliberate
  carve-out** recorded at `docs/backlog.md:210`. Report the missing comment, not
  the behaviour.
- **`to_module_instance` / `to_decision_slot` / `to_decision_resolution`** are
  called from `decision/` and `rendering/`, not just locally.
- **Zero `relationship()` anywhere in `app/`** — project-wide convention.

Real and reported 2026-08-21 (not yet actioned, not in `docs/backlog.md`):
- `system_content_record_id` and `send_instance_id` on `ContentOverrideDB` have
  **no writer in `backend/app/`** — seed SQL only. Consequence: the content-delete
  guard at `content/service.py:491` is inert for app-created data.
- `DecisionSlotDB.max_results` is written and exposed but read by nothing;
  `resolve_decision` always takes one result.
- `POST /campaigns/{id}/variants` drops `subject`/`preheader`;
  `POST /campaigns/decision-slots/{id}/resolutions` drops `recipient_id`/
  `content_version_id`. Both are 2-loc fixes and both contradict documented
  `campaigns.md` invariants.
- `outcome_delta` is modelled and row-locked but has **no producer and no
  consumer** — a product gap, not lines to delete.

Method note that paid off: for a reversal-residue sweep, grep each **column and
Pydantic field** for writers separately from readers, and exclude `scripts/`
from the writer set — seed SQL masks exactly this class of orphan.

Related: [[seams-do-not-flag]], [[backlog-already-logged]],
[[cluster1-frontend-templates]], [[review-only-never-edit]]
