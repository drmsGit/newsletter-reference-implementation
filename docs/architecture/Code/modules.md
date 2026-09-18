---
type: code-module
module: modules
topic:
  - architecture
  - composition
  - rendering
created: 2026-07-27
modified: 2026-09-18
---

# modules

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Composition Architecture]], [[MOC - Rendering Architecture]].

## Purpose

The modules module owns **the registry of module templates, namespaced per
channel** — the drop-a-file plugin system that lets a designer add a new kind of
block (a hero, a two-column image, a CTA, a push notification) **without any
Python change**. Each module is a pair of files in
`storage/modules/<channel>/`: a `name.json` manifest (label, channel, whether
it's CMS-driven, and the list of variables) and a `name.html` template. This
module discovers, validates, and serves those manifests; it does **not** render
(that's [[rendering]]) and it has **no database** — the files on disk are the
source of truth.

**Renamed from `email_modules` on 2026-09-17** ([[ADR-162 — Channel Rendering and Artifacts]]
point 5). The rename was forced rather than cosmetic: the registry was flat and
global, so the moment a push manifest existed a manager composing an email was
offered it.

## Key files
- `backend/app/modules/registry.py` — per-channel filesystem discovery, manifest parsing, mtime-based cache, `get_template_html`, the misfiling assertion
- `backend/app/modules/router.py` — the `/email-modules` JSON endpoints (route prefix unchanged; they take a `channel` query parameter defaulting to email)
- `storage/modules/<channel>/*.json` + `*.html` — **the actual modules** (the plugin folder). `email/` holds `brand.css`; `push/` holds a template-less module

## Public surface
**Functions** (`modules/registry.py`):
- `list_manifests(channel)` / `get_manifest(channel, name)` — the manifests this channel accepts. **The channel is required and never defaulted**: defaulting it would silently resolve an email module for any caller that had not thought about channel, which is the collision namespacing exists to prevent.
- `get_template_html(channel, name)` — the raw Jinja HTML, or `None` for a module declaring `has_template: false`
- `envelope_module_type(channel)` — which of this channel's modules carries its **envelope** fields ([[ADR-162 — Channel Rendering and Artifacts]] point 1), found by reading the manifests rather than by looking for a module called `header`
- `assert_manifests_load()` — forces discovery at startup so a misfiled manifest stops the process rather than a request
- `ModuleManifest` / `ModuleVariable` — the manifest dataclasses (also used by [[overrides]] to validate field edits)

**Routes** (`/email-modules`, tag `email-modules`): 2 routes — list manifests, get one by name.

## Data model
**None.** State is the `storage/modules/` directory tree, one subdirectory per channel. A file-change is detected by directory mtime and the registry rebuilds — no DB, no migration, no restart for a new module.

## Depends on →
*Nothing* (no `app.*` imports — it's a leaf that reads the filesystem).

## Depended on by →
- [[rendering]] — fetches the manifest + HTML to render a module
- [[overrides]] — validates a field-override against the module's declared `variables`
- [[frontend]] — the module picker / add-module form lists available types

## Invariants & decisions
- **Convention over configuration.** A module = `name.json` + `name.html` in its channel's folder. Filename stem = module type. Zero Python changes to add one (a core pillar of the project's positioning).
- **Directory AND declaration, with an assertion between them** ([[ADR-162 — Channel Rendering and Artifacts]] point 5). A manifest declares its own `channel`; the loader raises `MisfiledManifestError` if that contradicts the directory. This is the one place the registry raises instead of logging-and-skipping: a malformed manifest costs that one module, a misfiled one offers it on a channel whose renderer cannot take it.
- **`has_template: false`** — a module with no HTML counterpart, declared rather than inferred. Push uses it: the receiving OS does the rendering, so a push renderer fills fields and has no layout job ([[ADR-160 — Channel Model and Composition]] point 2). Without the flag the registry would silently skip push for having no `.html`.
- **`envelope: true` on a variable** — the field belongs on the delivery envelope, not in the body. A subject line is the case that forces it.
- **`variable name = CMS field name exactly`** — no mapping layer between a module's declared variables and content fields ([[rendering]] relies on this).
- **`cms: true` vs `cms: false`** — `true` = variables come from the resolved content record / decision slot; `false` = from the module's `module_data` (static hero/cta).
- **One broken manifest can't take down the registry** — a malformed or unpaired file is logged and skipped, not fatal.
- **Source format is MJML for the final project, raw HTML in the POC** — [[ADR-131 — Email Module Templates Use MJML as Source Format]] (implementation intentionally lags the ADR for now).

## ⚠️ Change-impact — if you touch this, also check…
- **A manifest's `variables` list** → [[rendering]] `render_cms_module` iterates exactly these names, and [[overrides]] validates field edits against them. Adding/removing a variable changes both.
- **The `cms` flag** → flips whether [[rendering]] pulls variables from content vs. `module_data`; a wrong value silently blanks a module.
- **The directory path** (`storage/modules/`) → hard-coded relative to the package in `registry.py`; moving `storage/` breaks discovery.
- **Renaming a module file** → any `module_instances.module_type` pointing at the old name renders as "unknown module".
