---
id: TASK-94
title: >-
  Brand/theming structure across stages (note options now, implement in final
  MVP package).
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-11 08:42'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 204700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — Brand/theming structure across stages (note options now, implement in final MVP package).** Surfaced 2026-07-26. Goal: let each adopting company drop in their own styles so the whole architecture looks consistently *theirs*, across the (at least) two rendering stages — **web** (the Jinja management UI) and **email** (rendered newsletters). **Current state:** email is already the "drop a file" pattern — `storage/email_modules/brand.css` (~79 lines) is auto-inlined by the renderer and uses class names matching the module templates (`.module-headline`/`.module-button`/`.module-hero`…), with a header comment "replace per project". **Web has no brandable file** — it's raw Bootstrap 5 via CDN in `base.html`. There is **no shared source of truth** between the two, and **no preprocessor/build**. **Design answer to the questions raised:** (1) *One file for both stages is possible but a bad idea* — web and email have fundamentally different CSS capabilities (email = inlined, table-based, limited client support; web = full modern CSS), so a single stylesheet can't serve both cleanly. (2) *"Is there a CSS 'MJML'?"* — yes, the analogues are **CSS preprocessors** (Sass/SCSS, Less: variables, nesting, mixins, partials — write maintainable source, compile to targets) and **design tokens** (brand primitives — colors/fonts/spacing/radius — as the single source of truth, e.g. CSS custom properties, or a Style-Dictionary-style build that emits per-target files). Neither is "20,000 lines" — the point is a *small* token file + component partials. (3) **Recommended structure:** split **tokens** (what the brand *is* — a tiny file the company edits) from **stylesheets** (how tokens are applied per stage). One token source → two outputs: web consumes tokens via CSS custom properties (native support); email keeps a `brand.css` but its values come from the *same* tokens, **baked in as concrete values at build** (email clients don't support CSS variables reliably, so they must be inlined — which the renderer already does via `css_inline`). (4) *Separate files + a frontend to manage?* — a full in-app CSS editor is a footgun; better is a light **brand-tokens panel** (pick primary color / font / logo — manager-friendly, writes tokens, akin to the existing settings layer) while raw stylesheets stay files for developers. (5) **Consistency / no redundant classes** — the email side already enforces a shared `.module-*` class convention; extend the same discipline: one token source, a documented component-class vocabulary shared by both stages, component-scoped (not page-scoped) classes. **DECIDED direction (2026-07-26) — simpler than the tokens→two-outputs idea above; handle the two stages *differently*, no shared token pipeline:**
- **Email** keeps `brand.css` as a **separate, full-flexibility plain-CSS file** (developer/designer-owned, drives preview + MJML). Email is the stage managers actually care about visually — "I want rounded buttons, a shadow behind the box", etc. — so it gets **full raw-CSS control**, not a constrained token set. No abstraction forced on it.
- **Web** (management UI) gets a **small, simple brand-palette frontend** — **colors, fonts, sizes, logos only** (settings-layer style, applied to the UI via CSS custom properties). Deliberately *not* full CSS; keep it simple.
- Net: email = file + full flexibility; web = simple palette UI. No build step, no preprocessor. Consistency still comes from the shared `.module-*` class vocabulary on the email side and a small fixed token set on the web side.

**Scope (per working style):** lands in the final MVP package; the web palette is small and self-contained enough to build standalone earlier if wanted. Source: user, 2026-07-26.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 264, section "Features", position 47 in that section (top = do next). The description is the original entry, verbatim.

2026-10-10 (task-301, ADR-193, decided by the user): brand.css stays the one shared full-CSS stylesheet for email structure, but each brand profile now also carries colour and font values, applied on top of brand.css at render. That widens this task's email side from one file per installation to one file plus per-brand values. How they are applied is still open: email clients handle CSS custom properties poorly, so the values must be resolved at render or inlining.

2026-10-11 (ADR-194, decided by the user): the manager app's look no longer gets a separate palette in Settings. It reads accent colour, logo and font from the working brand's default brand profile, with a contrast guard (task-356). Email styling is now brand.css filled from the brand profile's fields (task-354). What remains here is the overall theming structure across stages, if anything.

2026-10-11, revised: only the working brand's LOGO comes from its default profile (task-356). The app's palette and fonts stay one per installation, per the design draft in docs/design/DESIGN.md.
<!-- SECTION:NOTES:END -->
