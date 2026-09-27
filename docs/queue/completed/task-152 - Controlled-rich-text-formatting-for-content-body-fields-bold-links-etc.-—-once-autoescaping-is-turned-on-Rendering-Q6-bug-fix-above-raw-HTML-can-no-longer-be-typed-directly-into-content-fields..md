---
id: TASK-152
title: >-
  Controlled rich-text formatting for content body fields (bold, links, etc.) —
  once autoescaping is turned on (Rendering Q6 bug fix above), raw HTML can no
  longer be typed directly into content fields.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels: []
dependencies: []
type: feature
ordinal: 501600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature]** Controlled rich-text formatting for content body fields (bold, links, etc.) — once autoescaping is turned on (Rendering Q6 bug fix above), raw HTML can no longer be typed directly into content fields. Needs a safe, controlled mechanism instead (e.g. a rich-text editor emitting sanitized markup, or a markdown-like syntax translated to safe HTML at render time) so editors keep the formatting they need without reopening the injection risk autoescaping just closed. Source: [[Interview Prep - Snapshots, Rendering, Email Modules]] → Rendering Q6 (addendum). **Done 2026-07-12** — minimal safe `**bold**`/`[label](url)` syntax (escape everything first, then allow only those two patterns through) applied to `body_medium`. Verified live: rendered to `<strong>`/`<a href>` correctly with no raw-HTML leakage.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 533, section "Done", position 16 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
