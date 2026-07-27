---
type: code-module
module: content
topic:
  - architecture
  - content
created: 2026-07-27
modified: 2026-07-27
---

# content

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Content Architecture]].

## Purpose

The content module owns **the catalog of reusable things you can say, and how
they're categorized** — the source of truth for *content itself*, independent of
any campaign. A content record is a communication unit (an article, an offer)
that is *referenced*, never copied, into campaigns ([[ADR-013 — Content Reference Instead of Content Copy]]). It also owns the **category taxonomy** (the topics used
for personalization signals and audience targeting) and **content versioning**
(immutable published snapshots of a record's fields, for audit and safe sends).

## Key files

- `backend/app/content/db_models.py` — the five tables (records, categories, relations, assignments, versions)
- `backend/app/content/service.py` — CRUD + the taxonomy graph (cycle-checked relations) + version publish/restore + guarded deletes
- `backend/app/content/router.py` — the `/content/*` JSON endpoints

## Public surface

**Service functions** (`content/service.py`, selected):
- `create_content` / `update_content_record` / `get_content_record` / `list_content_records`
- `create_category` / `list_categories` / `delete_category`
- `assign_category_to_content` / `list_categories_for_content` / `delete_category_assignment`
- `create_category_relation` (cycle-guarded via `_would_create_cycle`) / `list_category_relations`
- `create_content_version` / `list_versions_for_content` / `get_latest_version_for_content`
- `delete_content_record` — **tiered delete**: hard-blocks if decision/override history references it, soft-reassigns the rest
- `create_demo_content_if_empty` — seeds a starter catalog on first boot (called from `main.py`)

**Routes** (`/content`, tag `content`): 16 routes — list/get/create/update/delete records; categories CRUD; category relations; category assignments; content versions. (Ordering matters — see change-impact.)

## Data model

*Five tables, all owned here.*
- **`content_records`** (`ContentRecordDB`) — `title`, `description`, `content` (JSON), `status`. The `content` JSON is the flexible field bag ([[ADR-011 — Store Reusable Content Only]]).
- **`categories`** (`CategoryDB`) — the topic taxonomy nodes.
- **`category_relations`** (`CategoryRelationDB`) — parent/child edges between categories (a DAG — cycles are rejected).
- **`content_category_assignments`** (`ContentCategoryAssignmentDB`) — which categories a record belongs to, with a 0–10 `score` (how strongly). **This score scales engagement signals** — see [[insight]].
- **`content_versions`** (`ContentVersionDB`) — immutable published snapshots of a record's `content` ([[ADR-128 — Version Content for Auditability and Restoration]]).

## Depends on →
- [[campaigns]] — `delete_content_record` checks `module_instances` for references before allowing a delete (function-local import)
- [[overrides]] — same delete-guard: a record referenced by override history is hard-blocked

## Depended on by →
- [[campaigns]] — module instances / decision resolutions reference content records
- [[decision]] — strategies rank content records and read their category assignments
- [[rendering]] — resolves a record's fields (or a pinned version) into template variables
- [[snapshots]] — freezes content into the render context
- [[insight]] — reads `content_category_assignments` to turn a click into per-category signals
- [[audience]] — ranks a campaign's categories from content assignments to suggest targeting
- [[frontend]] — the content/category admin UI

## Invariants & decisions
- **Content is referenced, not copied.** [[ADR-013 — Content Reference Instead of Content Copy]], [[ADR-010 — Newsletter Content Source of Truth]].
- **Store reusable units only** ([[ADR-011 — Store Reusable Content Only]]); a record represents a communication unit ([[ADR-012 — Content Records Represent Communication Units]]).
- **The category graph is acyclic.** `create_category_relation` rejects any edge that would create a cycle.
- **Versions are immutable and auditable.** [[ADR-128 — Version Content for Auditability and Restoration]]. Send mode resolves the latest frozen version, never live draft content (enforced in [[rendering]]).
- **Deletes protect history.** Decision/override references are a hard block (never force-deletable); category assignments/versions are soft/reassignable behind a `force=true` confirm.

## ⚠️ Change-impact — if you touch this, also check…
- **Route registration order** — `GET /content/categories` and `/content/category-relations` must be declared **before** `GET /content/{content_id}`, or the `{content_id}` catch-all swallows them (422). This was a real bug.
- **The `content` JSON field names** — they *are* the template variable names ([[rendering]] does no mapping layer). Renaming a field silently blanks that variable in every email module that uses it.
- **Assignment `score`** — [[insight]] multiplies engagement weight by `score/10`; changing the 0–10 scale changes signal magnitudes.
- **Dropping/renaming a column** — no migrations here; grep `backend/scripts/*.sql` for seed/reset drift (a stale `reset_all_data.sql` referencing a dropped `categories.parent_category_id` broke baseline restore once).
