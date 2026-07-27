---
type: code-module
module: settings
topic:
  - architecture
  - configuration
created: 2026-07-27
modified: 2026-07-27
---

# settings

> Part of [[MOC - System Overview]].

## Purpose

The settings module owns **DB-backed runtime configuration — the tunable values
an admin/BI person can retune without touching code**. It's deliberately only for
*values and toggles* (the send cap, signal weights, decay half-lives), **not**
for structure or logic — the *shape* of things (the decay model, scoring
algorithm, plugins) stays in code. Code defines the defaults; a row here overrides
them. Generic key → JSON value, so a new setting needs no migration.

## Key files
- `backend/app/settings/db_models.py` — `AppConfigDB`
- `backend/app/settings/service.py` — get/set + the typed accessors
- (No router of its own — settings are edited via the [[frontend]] `/ui/settings` page.)

## Public surface
**Service functions** (`settings/service.py`):
- `get_config(db, key)` / `set_config(db, key, value)` — the generic key→JSON store
- `get_max_send_recipients(db)` — the send cap (key `max_send_recipients`, default 1000). Read by [[delivery]].
- `get_signal_weights(db)` — per-type contribution weights (overrides [[insight]]'s `CONTRIBUTION_WEIGHTS`)
- `get_half_lives(db)` — per-type decay half-lives (overrides [[insight]]'s `HALF_LIFE_DAYS`)

**Routes:** none in this module. The UI reads/writes via [[frontend]] `GET/POST /ui/settings`.

## Data model
*One table.*
- **`app_config`** (`AppConfigDB`) — `key` (PK, string) → `value` (JSON). Absence of a row = use the code default.

## Depends on →
- [[insight]] — imports its default weights/half-lives, so a config row overrides a known default rather than an arbitrary one

## Depended on by →
- [[delivery]] — send-cap enforcement at plan time and after a rerun reconcile
- [[insight]] — `signals.py` pulls configured weights/half-lives on every signal read
- [[frontend]] — the settings admin page

## Invariants & decisions
- **Config = values, not logic.** Only tunable parameters live here; algorithms, plugins, and structure stay in code. (Once AI capabilities land, the AI-governance guard *toggles* would live here too.)
- **Code owns the defaults; the DB overrides.** A missing key silently uses the code default — the app runs with an empty `app_config` table.
- **No migration for a new setting** — it's a generic key→JSON store by design.
- **`get_half_lives` is imported lazily** inside [[insight]] `signals.py` to avoid a module-load cycle (settings imports insight's defaults).

## ⚠️ Change-impact — if you touch this, also check…
- **`max_send_recipients` semantics** → [[delivery]] refuses a plan (and a rerun reconcile) over the cap; it's a real guardrail, not just UI.
- **`get_signal_weights` / `get_half_lives` keys** → must line up with [[insight]]'s contribution types; a mismatched key silently falls back to the code default.
- **Adding a typed accessor** → keep the "override a known code default" pattern (don't introduce a magic value with no code default).
