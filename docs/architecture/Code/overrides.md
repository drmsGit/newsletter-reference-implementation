---
type: code-module
module: overrides
topic:
  - architecture
  - overrides
created: 2026-07-27
modified: 2026-07-27
---

# overrides

> Part of [[MOC - System Overview]]. Architecture rationale: [[ADR-040 — Introduce Override Layer]], [[ADR-041 — Override Precedence]].

## Purpose

The overrides module owns **the manager's ability to edit what the system
produced for a module, on the record** — the trust-building override layer. An
override is **field-level edits only** (`{manifest field: value}`) on a module
instance: a consistent headline across personalized picks, a shorter copy for one
send. It's a *functional* layer, not just an audit — [[rendering]] reads the
active override and its values win over resolved content until reset. Every
override keeps the system's original context so you can later ask "did the human
edit actually outperform the machine?" — the philosophy of "log overrides, show
that most didn't beat the system."

## Key files
- `backend/app/overrides/db_models.py` — `ContentOverrideDB` (one first-class table)
- `backend/app/overrides/service.py` — create (validated), the single-active lifecycle, reset, outcome-delta
- `backend/app/overrides/router.py` — the `/overrides/*` JSON endpoints

## Public surface
**Service functions** (`overrides/service.py`):
- `create_content_override(db, data)` — validate field edits against the module's manifest, enforce one-active-per-module
- `get_active_content_override(db, module_instance_id)` — the row [[rendering]] honors (O(1) via a partial unique index)
- `reset_content_override(db, override_id)` — deactivate (keeps the row as history)
- `list_content_overrides(...)` / `get_content_override(...)` — read history
- `record_outcome_delta(db, override_id, data)` — retroactively record whether the edit outperformed (row-locked, merge-not-replace)

**Routes** (`/overrides`, tag `overrides`): 5 routes — create, list, get, reset, PATCH outcome.

## Data model
*One table.*
- **`content_overrides`** (`ContentOverrideDB`) — `module_instance_id` (the render target), `field_overrides` (JSON, the edits), `system_content_record_id` (audit context), `active` + `reverted_at`, `outcome_delta`. Two constraints do real work: a CHECK that `field_overrides` is set (an override must change *something*), and a **partial unique index** allowing only **one active override per module**.

## Depends on →
- [[campaigns]] — an override attaches to a `ModuleInstanceDB`
- [[content]] — `system_content_record_id` references a content record (audit context)
- [[email_modules]] — validates field edits against the module manifest's declared variables

## Depended on by →
- [[rendering]] — `render_cms_module` applies the active override's fields (precedence)
- [[campaigns]] — composition views surface a module's override
- [[content]] — content delete is hard-blocked if override history references the record
- [[frontend]] — the override create/reset UI (a raw dev affordance today, not the final WYSIWYG)

## Invariants & decisions
- **Field edits only.** Swapping the whole content record is *not* an override: a for-all swap means "use static content, not a decision slot"; a segment-targeted swap belongs to the (open) guaranteed-placement concept, which suppresses the slot rather than overriding it. History: record-level "pins" were built, then deliberately removed.
- **One active override per module** — a module has a single override state; resets accumulate as history (enforced by the partial unique index).
- **Reset keeps history** — `active=false` + `reverted_at`, never a delete, so the trust-loop comparison and `outcome_delta` survive ([[ADR-041 — Override Precedence]]'s "used until deleted or reset").
- **Precedence: override field > resolved/static content** ([[ADR-040 — Introduce Override Layer]], [[ADR-041 — Override Precedence]]).
- **Backend-first, UI later.** The model/API is the deliverable; the current JSON-input UI is a placeholder for a future WYSIWYG editor with live preview.
- **Reusable spine.** Shaped so a future `AudienceOverrideDB` mirrors the same create → active → reset + audit/outcome lifecycle — *not* a polymorphic single table.

## ⚠️ Change-impact — if you touch this, also check…
- **`field_overrides` validation** → depends on [[email_modules]] manifest variable names; an override's keys must be declared module variables.
- **The one-active-per-module index** → [[rendering]] and `create_content_override` both assume at most one active row; loosening it breaks precedence and O(1) lookup.
- **`get_active_content_override`'s contract** → [[rendering]] `render_cms_module` calls it on every CMS module render; a slower/looser implementation hits the hot render path.
- **The "field edits only" rule** → don't reintroduce record swaps here; that decision was made twice. Segment-targeted content is the guaranteed-placement Needs-ADR item.
