---
id: TASK-66
title: Paid social is not declared as a channel yet.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 201900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — DEFERRED 2026-09-17, deliberately and with no ADR change.** **Paid social is not declared as a channel yet.** When the channel work is implemented, **email and push only**; no social channel manifest, no social provider adapter, no `max_modules` declaration for it. **Nothing in the ADRs is amended by this** — [[ADR-162 — Channel Rendering and Artifacts]] point 6 stands exactly as accepted, including its finding that *"carousel social ads are several ordered cards each with image, headline and link"* and that **only push is flat**. This is a scope decision about what gets built first, not a design decision about what social is.

  **Why it was asked at all, and worth re-reading when social returns:** the user first proposed social as a one-content-record channel like push — a manager uploads one or more images plus a caption, all inside a single content record's JSON, giving `max_modules: 1`. That conflicts with point 6's carousel finding, which would make social unbounded like email and letter, with a single-image post simply being the n=1 case. **The conflict is real and unresolved**, and deferring is what avoids resolving it on a guess before there is a paid-social requirement to test the answer against. When it returns, the question is precisely: *does a social variant hold one module or several ordered cards?* — because that single answer decides the `max_modules` declaration, and [[ADR-161 — Channel Execution Shapes]] point 1 already puts paid social on the separate **audience-delegated** provider interface, so it is the channel least like the others regardless. Source: user, 2026-09-17.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 206, section "Features", position 19 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
