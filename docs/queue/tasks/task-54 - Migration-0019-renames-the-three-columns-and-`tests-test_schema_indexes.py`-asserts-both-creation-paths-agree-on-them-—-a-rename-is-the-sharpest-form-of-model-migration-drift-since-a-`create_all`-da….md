---
id: TASK-54
title: >-
  Migration 0019 renames the three columns and `tests/test_schema_indexes.py`
  asserts both creation paths agree on them — a rename is the sharpest form of
  model/migration drift, since a `create_all` da…
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature] — DONE 2026-09-20, before the typed client, which was the whole point.** Migration 0019 renames the three columns and `tests/test_schema_indexes.py` asserts both creation paths agree on them — a rename is the sharpest form of model/migration drift, since a `create_all` database gets the new names for free and a deployed one only gets them if the migration runs. The migration was exercised for real rather than assumed: rolled back by hand, applied, re-applied (idempotent), and applied again from a half-applied state, which is what the per-column guards are for. **The open question is answered: `html_size` did mean the same thing in both branches** — both write `artifact.size_bytes()` (`rendering/renderers/base.py:73`), the UTF-8 byte length of the HTML body or of the JSON-serialised fields. One meaning, two shapes, which is exactly why the channel-specific name was misleading rather than merely ugly. Note also that the entry below mentions `html_body`; no such column exists — an inline artifact lives in `render_context["artifact"]`, and the three columns were `html_storage_type`, `html_location` and `html_size`. Original entry: ([[ADR-162 — Channel Rendering and Artifacts]] point 3).** A push artifact is stored inline in columns named `html_body` / `html_size` / `html_storage_type` (`snapshots/service.py:97-166`). The storage decision is right and is not what changes: writing a `.json` beside the `.html` was rejected because it hardens an artifact-on-disk shape the project leans away from. What is wrong is the **names** — a push payload returned in a field called `html_body` is, in the interview's own words, "a lie the next reader has to decode". **The trigger the ADR never named is now identifiable: a second consumer of the OpenAPI schema.** The React client's typed API client is generated from it, so `html_body` becomes the name every call site uses for push content; renaming afterwards means regenerating the client and touching all of them. Also settle whether `html_size` means the same thing across both branches. Source: [[Interview Prep - Channels, Audit]] → A-Q3.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 156, section "Features", position 7 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
