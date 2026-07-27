---
type: code-module
module: rendering
topic:
  - architecture
  - rendering
created: 2026-07-27
modified: 2026-07-27
---

# rendering

> Part of [[MOC - System Overview]]. Architecture rationale: [[MOC - Rendering Architecture]].

## Purpose

The rendering module owns **turning a variant's module stack into final HTML** —
resolving each module's content (or per-recipient decision pick), applying any
active override, filling the module template's variables, rendering rich text,
and inlining the brand CSS so it survives Outlook. It's an independent layer
([[ADR-060 — Rendering as Independent Layer]]): it *reads* existing decision
resolutions but does **not** execute decisions, and it has **no database**.

## Key files
- `backend/app/rendering/service.py` — the whole pipeline (`render_variant_html` and the per-module renderers)
- `backend/app/rendering/router.py` — the single `/rendering/*` endpoint
- `storage/email_modules/brand.css` — the stylesheet inlined into output

## Public surface
**Service functions** (`rendering/service.py`):
- `render_variant_html(db, variant_id, recipient_id=None, mode="preview", collect_resolutions=False)` — **the entry point [[delivery]] and [[snapshots]] call.** `mode="send"` requires published content; `"preview"` shows live drafts.
- `render_cms_module` / `render_static_module` / `render_unknown_module` — per-module-type renderers
- `resolve_content_for_module` / `resolve_renderable_content` — pick the content (pinned version, latest published, or live draft) for a module
- `render_rich_text` — safe rich-text → HTML

**Routes** (`/rendering`, tag `rendering`): 1 route — `GET /rendering/variants/{id}` (rendered preview).

## Data model
**None.** Reads across [[campaigns]], [[content]], [[overrides]], and [[email_modules]]; produces HTML.

## Depends on →
- [[campaigns]] — the variant's module instances + decision resolutions
- [[content]] — resolves record fields / pinned versions into template variables
- [[email_modules]] — fetches the manifest + Jinja HTML per module type
- [[overrides]] — applies the active field override (precedence)

## Depended on by →
- [[delivery]] — renders each recipient's HTML at send (`mode="send"`)
- [[snapshots]] — renders + freezes the HTML into a snapshot
- [[frontend]] — the variant preview page

## Invariants & decisions
- **Parity over implementation** — the goal is that preview and send render the *same*, not a specific rendering tech ([[ADR-063 — Rendering Parity Over Rendering Implementation]]).
- **`mode="send"` never silently sends draft content** — it resolves the latest published `ContentVersion` and raises `UnpublishedContentError` if none exists; `"preview"` falls back to the live draft.
- **`variable name = CMS field name exactly`** — no mapping layer; a module's manifest variables are looked up directly in the resolved content dict.
- **Override precedence** — a field override value wins over resolved content, per variable ([[ADR-041 — Override Precedence]]).
- **No content resolved → hide the slot**, don't show a placeholder ([[ADR-086 — Decision Slots Fail Gracefully]]).
- **Rendering reads resolutions, never executes them** — [[decision]] does the resolving; rendering only looks up the existing `DecisionResolutionDB` (which is why [[delivery]] resolves per recipient *before* calling render).
- **CSS is inlined** before output for email-client compatibility.

## ⚠️ Change-impact — if you touch this, also check…
- **`render_variant_html`'s signature** → [[delivery]] `send_send_instance` and [[snapshots]] `create_snapshot_for_variant` both call it; `mode` and `recipient_id` are load-bearing.
- **`resolve_content_for_module`'s content-XOR-slot handling** → relies on the [[campaigns]] CHECK constraint; it silently prefers `content_record_id` if both are set.
- **The "reads resolutions, doesn't execute" boundary** → if you make rendering resolve decisions, you'd double-resolve at send (delivery already does). Keep the split.
- **Variable lookup by manifest name** → coupled to [[email_modules]] manifests and [[content]] field names; a rename on either side blanks a variable.
