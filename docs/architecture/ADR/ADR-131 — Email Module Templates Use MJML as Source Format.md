---
type: adr
status: accepted
topic:
  - architecture
  - rendering
  - templates
  - frontend
created: 2026-07-03
modified: 2026-10-15
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

## Addendum 2026-10-15 — blocks are compiled when they are written, not at send or preview

Prompted by the first MJML blocks (queue task-371, [[ADR-198 — The Email Block Set Is Seven Blocks, Square Images and Text Links]]), and decided with the user on 2026-10-15. The Decision above says MJML compiles "in the Node/React frontend layer, triggered when a send is prepared or a preview is requested". This addendum changes when compilation happens. It does not change where: compilation stays in Node, the backend never runs MJML, and the escape hatch stands. The Decision section is not edited.

**1. A block is compiled when it is written.**

- **A block is authored as `storage/modules/email/<type>.mjml`,** with its Jinja placeholders in place.
- **`npm run build:modules` in `frontend/` compiles it** to the `.html` template that the backend already renders.
- **The compiler is the official `mjml` npm package,** pinned as a dev dependency. It is hash-locked in `frontend/package-lock.json`, as every frontend package is (`docs/implementation/npm.md`). [[ADR-189 — Python Dependencies Are Locked With Hashes]] is the same rule for Python.

**2. The compiled files are committed, and CI checks them.**
CI fails if a committed `.html` differs from what the pinned MJML produces from its `.mjml` ([[ADR-190 — Continuous Integration Blocks on Defects and Reports Style]]).

**3. MJML never starts rendering differently on its own.** The user asked how the system would notice if MJML rendered differently after an update. The answer, recorded here:

- **MJML is pinned.** It does not change by itself.
- **An upgrade is a deliberate, reviewed change.** The version is bumped and every block is recompiled. The diff of every compiled template is visible in review.
- **CI rejects a bump made without recompiling** (point 2).
- **An email already sent is not touched.** It sits in the inbox as it went out. Its frame freezes the composition and the content, not the templates. [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] point 4 does not version templates. A reconstruction after a recompile uses today's templates. The frame's templates fingerprint reports the change, and the hash check shows whether the output differs.

**4. Hand-written HTML stays the escape hatch.** Editorial, the visible header, the footer and the envelope stay HTML for now.

**5. The backend never runs MJML.** This is unchanged. It now holds without any Node step at send or preview time.

**Consequences.**

- **The Negative point "the Python backend cannot independently re-render a snapshot without a pre-compiled HTML artifact or a call to a Node compilation step" is resolved.** The compiled artifact is in the repository. The Notes' reliance on "snapshot generation is always initiated from the frontend" no longer carries the design.
- **Preview and send render the same committed files.** There is no compile at either moment ([[ADR-063 — Rendering Parity Over Rendering Implementation]]).
- **The order of [[ADR-187 — A Manager Hides Fields Per Module, and Required Means Required When Shown]] point 5 is reversed.** That point says a hidden field is blanked "before the MJML compile", and its example sends filled MJML to the compiler. Now the compile comes first and the values are filled later. A hidden field is still blanked when values are filled, and its `{% if %}` guard still removes it, but only if the guard survives the compile. ADR-187's load-time check reads the template the backend loads, so a guard the compiler dropped or moved is refused there. ADR-187's Decision is not edited.
- **MJML does not know Jinja.** How Jinja's tags pass through the compiler intact is settled in the build.
- **Changing a block needs Node and a build step.** Each block is two files in the repository, the `.mjml` source and its compiled `.html`.

## Related ADRs

### Depends On
- [[ADR-060 — Rendering as Independent Layer]]
- [[ADR-061 — Snapshot Based Final Rendering]]
- [[ADR-130 — POC Uses Modular Monolith, Target Architecture Supports Service Separation]]

### Enables
- [[ADR-060 — Rendering as Independent Layer]]
