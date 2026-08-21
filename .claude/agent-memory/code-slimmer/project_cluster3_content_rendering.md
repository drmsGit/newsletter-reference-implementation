---
name: cluster3-content-rendering
description: Results of the 2026-08-21 content/ + rendering/ sweep — no dead code, no orphaned schema; the real theme is missing DB constraints and an ADR-062 gap
metadata:
  type: project
---

Cluster 3 (`backend/app/content/` 966 loc, `backend/app/rendering/` 387 loc)
swept 2026-08-21, both read in full. **No dead code and no orphaned schema.**
Do not re-run reachability here.

**Why:** `content/` carried the content-schema redesign (`body` → `content`
JSON, `docs/backlog.md:230`), so it looked like a Cluster-2-style orphan target.
It is not — the redesign was completed cleanly. The residue is at the
**constraint** level instead.

**How to apply:** if a future sweep touches these dirs, start from DB
constraints and ADR-062 audit completeness, not from reachability or schema
orphans.

Confirmed live / intentional, never flag:
- **All 16 `/content` routes, the 1 `/rendering` route, all 26
  `content/service.py` functions, all 11 Pydantic models.** Router-only service
  functions are ADR-142 public surface. `get_latest_version_for_content` is
  called from `snapshots/` *and* both `pkgutil`-discovered decision strategies.
- **Zero unused imports in either module** — AST-verified.
- **The `content` JSON blob is clean on both sides.** The six keys written by
  `frontend`'s content create/edit are exactly the six CMS manifest variables in
  `storage/email_modules/*.json`. No writer-only or reader-only key. (Checked
  because seed SQL masks this class — it did not here.)
- **`render_static_module` raising `UnpublishedContentError`** for a
  content-linked static module — deliberate, `docs/backlog.md:224` Done.
- **`resolve_content_for_module` preferring `content_record_id` over
  `decision_slot_id`** — settled by the CHECK added in `docs/backlog.md:276`.
- **`_load_brand_css`'s `lru_cache`** — `docs/backlog.md:238` Done.
- **`render_rich_text` + its two regexes** — the controlled formatting mechanism
  promised when autoescaping was turned on (`docs/backlog.md:220` Done).
- **`_would_create_cycle`'s iterative DFS** — the only enforcement of the
  acyclic-taxonomy invariant. Over-built-looking, load-bearing.
- **`CategoryDB.type`** — branched on in `frontend/router.py`.
- **`data-module-id` / `data-content-id`** in rendered HTML — read by nothing in
  repo; almost certainly click-attribution seams. Left alone.
- **No tests exist for `content/` or `rendering/`** — that is the standing risk
  on every finding, not a separate finding.

Real and reported 2026-08-21 (not yet actioned, not in `docs/backlog.md`):
- **`content/db_models.py` is the only module in `backend/app/` with zero
  table-level constraints.** auth, audience, campaigns, insight, overrides and
  recipients all have `__table_args__`. Three integrity rules are service-only
  check-then-insert: `(content_id, category_id)` assignment uniqueness (the
  audience equivalent was fixed at `docs/backlog.md:294`), `version_number`
  sequencing, category-name uniqueness (audience equivalent at `:296`). No FK
  indexes either, though `overrides/db_models.py:48` sets the precedent for the
  same hot path.
- **`relation_type` is single-valued everywhere and gates the cycle guard** —
  `create_category_relation` only cycle-checks `if relation_type ==
  "parent_child"`, but every traversal ignores the type. A non-`parent_child`
  edge is unguarded and then walked as a hierarchy edge. 1-loc fix.
- **ADR-062 requires the snapshot to store *overrides* and *resolved content
  data*; `build_render_context` stores neither.** `render_variant_html`'s
  `collect_resolutions` carries resolutions only, so the caller has no
  non-racing way to record the override that changed the HTML. Same fix shape as
  `docs/backlog.md:240` (Done) — and that fix's static-content half is still
  open: `snapshots/service.py` re-derives the latest version independently of
  rendering.
- **Two override paths disagree on scope** (CMS applies manifest-declared keys
  only, static applies all keys) — but **neither contradicts ADR-041**; both put
  override ahead of catalog. Consistency finding, not an ADR violation.
- **Rich text is CMS-only, keyed off a hardcoded `_RICH_TEXT_FIELD =
  "body_medium"`** — a one-entry mapping layer in a module whose stated
  invariant is "no mapping layer". The seam is a `rich_text` flag on
  `ModuleVariable`.
- **`get_template_html` reads from disk per module per render**, uncached, while
  `_load_brand_css` two functions above was explicitly cached for that exact
  reason. Owning module is `email_modules/` (Cluster 7).
- **`content.md` advertises version "restore"; no restore exists anywhere.**
  ADR-128 specifies it concretely (restore = create a new version from an old
  one). Decide-don't-delete, not residue.

Method notes that paid off:
- Diff the JSON-blob keys written by the app against the **manifest variable
  names** in `storage/email_modules/*.json` — that is the schema a JSON column
  does not have.
- `grep "__table_args__\|UniqueConstraint\|CheckConstraint\|Index(" app/*/db_models.py`
  in one pass: the module that returns nothing is the finding.
- For any missing-constraint finding, search `docs/backlog.md` for the *same
  pattern in another module* — several were fixed there in 2026-07 and the Done
  entries name the systemic gap explicitly.

Related: [[seams-do-not-flag]], [[backlog-already-logged]],
[[cluster2-overrides-campaigns]], [[review-only-never-edit]]
