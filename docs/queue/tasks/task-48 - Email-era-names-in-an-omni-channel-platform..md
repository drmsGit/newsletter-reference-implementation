---
id: TASK-48
title: Email-era names in an omni-channel platform.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
  - frontend
dependencies: []
priority: p3
type: chore
ordinal: 200100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Chore] — P3 for the code, P2 for the four that reach the schema. Measured 2026-09-20.** **Email-era names in an omni-channel platform.** Twelve email-shaped names reach the OpenAPI schema; nine are FastAPI's auto-named `Body_*_ui_*` Jinja form bodies and vanish with that plane. **Four genuinely mislead a generated client** and are tabled in `docs/react-screen-inventory.md` so the frontend session is told rather than left to infer: `Variant.subject`/`.preheader` (the columns were dropped by migration 0012 — they are synthesised, and a push variant has no envelope), `GET /email-modules` (takes a `channel` parameter defaulting to email, serves all of them), `RenderedVariant.html` (snapshots already went `artifact_*`; this did not), and `Recipient.email`/`.email_consent_status` (flattened cells of a per-channel address set and consent grid). **Separately, 25 internal definitions across 13 files** carry email-shaped names — `render_variant_html` and friends. Those are honest about what they do, never reach the frontend, and are a readability pass rather than a risk. **Do the four with the client, not before it:** each is a schema change, and the reason the `artifact_*` rename went first was that nobody had written the table above. Now somebody has.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 144, section "Features", position 1 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
