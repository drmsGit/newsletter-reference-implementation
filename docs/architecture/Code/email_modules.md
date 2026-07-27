---
type: code-module
module: email_modules
topic:
  - architecture
  - composition
  - rendering
created: 2026-07-27
modified: 2026-07-27
---

# email_modules

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Composition Architecture]], [[MOC - Rendering Architecture]].

## Purpose

The email_modules module owns **the registry of email module templates** — the
drop-a-file plugin system that lets a designer add a new kind of block (a hero, a
two-column image, a CTA) **without any Python change**. Each module is a pair of
files in `storage/email_modules/`: a `name.json` manifest (label, whether it's
CMS-driven, and the list of variables) and a `name.html` template. This module
discovers, validates, and serves those manifests; it does **not** render (that's
[[rendering]]) and it has **no database** — the files on disk are the source of
truth.

## Key files
- `backend/app/email_modules/registry.py` — filesystem discovery, manifest parsing, mtime-based cache, `get_template_html`
- `backend/app/email_modules/router.py` — the `/email-modules` JSON endpoints
- `storage/email_modules/*.json` + `*.html` — **the actual modules** (the plugin folder), plus `brand.css`

## Public surface
**Functions** (`email_modules/registry.py`):
- `list_manifests()` / `get_manifest(name)` — the discovered module manifests (auto-refreshed when files change)
- `get_template_html(name)` — the raw Jinja HTML for a module
- `ModuleManifest` / `ModuleVariable` — the manifest dataclasses (also used by [[overrides]] to validate field edits)

**Routes** (`/email-modules`, tag `email-modules`): 2 routes — list manifests, get one by name.

## Data model
**None.** State is the `storage/email_modules/` directory. A file-change is detected by directory mtime and the registry rebuilds — no DB, no migration, no restart for a new module.

## Depends on →
*Nothing* (no `app.*` imports — it's a leaf that reads the filesystem).

## Depended on by →
- [[rendering]] — fetches the manifest + HTML to render a module
- [[overrides]] — validates a field-override against the module's declared `variables`
- [[frontend]] — the module picker / add-module form lists available types

## Invariants & decisions
- **Convention over configuration.** A module = `name.json` + `name.html` in the folder. Filename stem = module type. Zero Python changes to add one (a core pillar of the project's positioning).
- **`variable name = CMS field name exactly`** — no mapping layer between a module's declared variables and content fields ([[rendering]] relies on this).
- **`cms: true` vs `cms: false`** — `true` = variables come from the resolved content record / decision slot; `false` = from the module's `module_data` (static hero/cta).
- **One broken manifest can't take down the registry** — a malformed or unpaired file is logged and skipped, not fatal.
- **Source format is MJML for the final project, raw HTML in the POC** — [[ADR-131 — Email Module Templates Use MJML as Source Format]] (implementation intentionally lags the ADR for now).

## ⚠️ Change-impact — if you touch this, also check…
- **A manifest's `variables` list** → [[rendering]] `render_cms_module` iterates exactly these names, and [[overrides]] validates field edits against them. Adding/removing a variable changes both.
- **The `cms` flag** → flips whether [[rendering]] pulls variables from content vs. `module_data`; a wrong value silently blanks a module.
- **The directory path** (`storage/email_modules/`) → hard-coded relative to the package in `registry.py`; moving `storage/` breaks discovery.
- **Renaming a module file** → any `module_instances.module_type` pointing at the old name renders as "unknown module".
