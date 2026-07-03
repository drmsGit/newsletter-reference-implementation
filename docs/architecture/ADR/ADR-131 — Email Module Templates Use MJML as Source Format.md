---
type: adr
status: accepted
topic:
  - architecture
  - rendering
  - templates
  - frontend
created: 2026-07-03
modified: 2026-07-03
depends_on:
  - "[[ADR-060 — Rendering as Independent Layer]]"
  - "[[ADR-061 — Snapshot Based Final Rendering]]"
  - "[[ADR-130 — POC Uses Modular Monolith, Target Architecture Supports Service Separation]]"
enables:
  - "[[ADR-060 — Rendering as Independent Layer]]"
---

## Status
Accepted

## Context
Email module templates (e.g. `2col_product`, `hero_banner`) must be authored by someone and compiled to email-compatible HTML. Email HTML is notoriously complex — nested tables, inline styles, inconsistent client support — making raw HTML an unreasonable authoring format for designers and an unstable foundation for long-term maintenance.

The target architecture includes a React/Node.js frontend (Phase 2). Snapshots are triggered at send time from the frontend layer, meaning the Python backend does not need to compile templates itself.

Two alternatives were considered:
- **Raw HTML/Jinja templates** — current state. Works, but places the full complexity of email HTML on template authors and couples every template to the rendering quirks of today's email clients.
- **Custom DSL** — a bespoke layout language compiled to HTML by the backend. Offers the translation-layer benefit but requires building and maintaining a custom compiler, and still requires designers to learn a new syntax without established tooling.

## Decision
Email module templates are authored in **MJML** (mjml.io, MIT license).

MJML compilation runs in the **Node/React frontend layer**, triggered when a send is prepared or a preview is requested. The Python rendering backend receives already-compiled HTML — it never invokes MJML directly.

Raw HTML templates remain permitted as an explicit escape hatch for layouts MJML cannot express, but are not the recommended path.

## Consequences

### Positive
- Template authors write declarative, readable markup instead of table-based email HTML.
- A single change to the compilation layer (custom MJML components or post-processing) propagates to all templates — no need to update individual files when email client standards or accessibility laws change.
- MIT license: no fees, no vendor lock-in, commercially usable, forkable.
- Compilation is entirely self-hosted — no data leaves the infrastructure. No GDPR or Datenhoheit exposure from the tool itself.
- MJML's `mj-raw` escape hatch and custom component API mean the system is never blocked by MJML's own release cycle for compliance changes (e.g. European accessibility law updates can be applied via a post-processing step or a custom component override).
- Node.js dependency is already implied by the React frontend; no additional runtime required.

### Negative
- Template authors must learn MJML syntax (low barrier, well-documented, but non-zero).
- MJML compilation lives in the frontend layer — the Python backend cannot independently re-render a snapshot without a pre-compiled HTML artifact or a call to a Node compilation step.
- Raw HTML escape hatch, if used widely, erodes the translation-layer benefit.

## Notes
The decision not to build a custom DSL was deliberate. MJML is a proven version of exactly the same idea — a declarative format that compiles to email-compatible HTML — with an existing compiler, tooling, and ecosystem. The cost of building and maintaining an equivalent from scratch outweighs any benefit of owning the full stack at this layer.

Snapshot generation is always initiated from the frontend (send preparation flow), so Python receiving compiled HTML is architecturally consistent with ADR-061.

## Related ADRs

### Depends On
- [[ADR-060 — Rendering as Independent Layer]]
- [[ADR-061 — Snapshot Based Final Rendering]]
- [[ADR-130 — POC Uses Modular Monolith, Target Architecture Supports Service Separation]]

### Enables
- [[ADR-060 — Rendering as Independent Layer]]
