---
type: code-module
module: campaigns
topic:
  - architecture
  - composition
created: 2026-07-27
modified: 2026-07-27
---

# campaigns

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Composition Architecture]].

## Purpose

The campaigns module owns **the structure of an email — the composition, not the
content**. One campaign = one newsletter ([[ADR-020 — Campaign Equals Newsletter]]).
A campaign has variants (the human-created A/B versions), each variant is an
ordered stack of module instances, and a module instance either points at a fixed
content record *or* at a decision slot (the personalization hook). It stores
*where things go and what decides them*, referencing content rather than holding
it ([[ADR-031 — Newsletter Composition Stores Structure Not Content]]). It also
owns the **decision slot** definition and the **decision resolution** record (the
audit of what a slot resolved to) — though the *resolving* is done by [[decision]].

## Key files
- `backend/app/campaigns/db_models.py` — the five composition tables
- `backend/app/campaigns/service.py` — campaign/variant/module/slot CRUD, module ordering, slot-config normalization, resolution records
- `backend/app/campaigns/router.py` — the `/campaigns/*` JSON endpoints

## Public surface

**Service functions** (`campaigns/service.py`, selected):
- `create_campaign` (creates an initial variant) / `list_campaigns`
- `create_variant_for_campaign` / `update_variant` (subject/preheader live here)
- `create_module_for_variant` / `update_module` / `move_module` / `delete_module`
- `create_decision_slot_for_variant` / `update_decision_slot` (validates config via `_normalize_for_strategy` → [[decision]]'s `normalize_slot_config`)
- `create_decision_resolution` / `list_resolutions_for_decision_slot` — the resolution audit rows

**Routes** (`/campaigns`, tag `campaigns`): 12 routes — campaigns; variants; module instances (+ move/delete); decision slots; decision resolutions.

## Data model

*Five tables, all owned here.*
- **`campaigns`** (`CampaignDB`) — name, status.
- **`variants`** (`VariantDB`) — a composition version; `subject` + `preheader` are **per-variant recipient-facing copy** (A/B versions differ) ([[ADR-021 — Variants Are Human Created Versions]]).
- **`module_instances`** (`ModuleInstanceDB`) — one placed module: `module_type`, `position`, and *either* `content_record_id` *or* `decision_slot_id` (or neither, for `module_data`-only static modules). Unique `(variant_id, position)`; CHECK enforces the two are never both set.
- **`decision_slots`** (`DecisionSlotDB`) — a personalization intent: `decision_strategy` + JSON `candidate_filter` / `strategy_config` + `max_results`.
- **`decision_resolutions`** (`DecisionResolutionDB`) — what a slot resolved to for a recipient: `content_record_id`, optional `content_version_id`, `reason`, `score`. The explainability + attribution record.

## Depends on →
- [[content]] — modules and resolutions reference content records
- [[decision]] — `update_decision_slot` normalizes config against the chosen strategy's declared shape
- [[recipients]] — resolutions key off `recipients.id`
- [[overrides]] — composition views surface a module's active override

## Depended on by →
- [[decision]] — reads slots, writes resolutions here
- [[rendering]] / [[snapshots]] — render a variant's module stack
- [[delivery]] — reads `VariantDB.subject` and the variant's `DecisionSlotDB`s at send
- [[audience]] — reads a campaign's content categories to suggest targeting
- [[overrides]] / [[providers]] / [[frontend]] — override targets a module; inbound correlation walks slot→resolution; UI is the composition editor

## Invariants & decisions
- **One campaign = one email** ([[ADR-020 — Campaign Equals Newsletter]]); **structure ≠ content** ([[ADR-031 — Newsletter Composition Stores Structure Not Content]], [[ADR-030 — Separate Global and Repeatable Structures]]).
- **A module points at content XOR a decision slot, never both.** The CHECK constraint is load-bearing: rendering silently prefers `content_record_id` and ignores a co-set slot ([[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]).
- **Slot config is locked to its strategy's shape** at create/update — unknown keys rejected, defaults filled, types checked (via [[decision]]).
- **Resolution = the audit of a decision** ([[ADR-085 — Decision Resolution Should Be Optionally Explainable]]).

## ⚠️ Change-impact — if you touch this, also check…
- **`VariantDB.subject`** → [[delivery]] `send_send_instance` reads it as the email subject (falling back to the send name). Renaming/removing it changes what recipients see.
- **The module content-XOR-slot rule** → [[rendering]] `resolve_content_for_module` depends on it; loosening the CHECK reintroduces silent-precedence bugs.
- **`DecisionResolutionDB` shape** → [[decision]] writes it, [[providers]] inbound reads it to attribute engagement, [[rendering]] reuses the row for the render context ([[ADR-062 — Snapshot Stores Final Render State]]).
- **Slot config field names** → must match what the strategy declares in [[decision]]; a mismatch surfaces as a 400 at slot save (by design), not a crash at send.
