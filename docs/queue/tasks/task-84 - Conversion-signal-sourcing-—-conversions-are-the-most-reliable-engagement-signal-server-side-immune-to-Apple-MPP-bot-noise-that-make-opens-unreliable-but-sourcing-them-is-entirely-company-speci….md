---
id: TASK-84
title: >-
  Conversion signal sourcing — conversions are the *most reliable* engagement
  signal (server-side, immune to Apple MPP/bot noise that make opens
  unreliable), but sourcing them is entirely company-speci…
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 203700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** Conversion signal sourcing — conversions are the *most reliable* engagement signal (server-side, immune to Apple MPP/bot noise that make opens unreliable), but sourcing them is entirely company-specific: (a) tracking provider (e.g. Google) wired directly, (b) pushed from a DWH, (c) CRM conversion profiles. Deliberately left as a **pluggable contribution type** by [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]], not a built integration — the contribution model already accepts a `conversion` type with a weight; what's missing is the ingest path, which is per-deployment. Document the extension point + one worked example when a real adopter needs it. Source: user, 2026-07-15 (signal-layer design session).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 244, section "Features", position 37 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
