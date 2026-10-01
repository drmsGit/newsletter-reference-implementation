---
id: TASK-29
title: this product has five names and none of them is canonical.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-01 20:54'
labels:
  - docs
dependencies: []
priority: p3
type: decision
ordinal: 102900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🟡 **[Needs decision — business] — this product has five names and none of them is canonical.** Measured 2026-09-20. **"Newsletter Reference Architecture"** is what the *runtime* says — FastAPI's `title=` (`backend/main.py:214`), the root route (`:656`), the Jinja nav (`backend/app/templates/base.html:18`) — and it is fossilised in the `nra_session` cookie, which is wire-visible. **"Newsletter Blueprint"** is what the prose and AI-facing docs say, including one string at `backend/main.py:179`, thirty-five lines from the other name. **"Newsletter Architecture"** is `CLAUDE.md:1`. **"Newsletter Reference Implementation"** is the repository and the one-line README. **"Newsletter Manager"** was invented by the React scaffold on 2026-09-20 and removed the same day. **This has never been asked, as opposed to deferred:** `docs/business/decisions/` is empty and `POSITIONING.md` blocks beta on the positioning *statement* while never mentioning the *noun*. **The SPA does not add a sixth** — `frontend/src/branding.ts` carries the Jinja nav's string from one constant, so when the name is decided exactly one line in the client changes. **The observation that makes this more than tidiness:** every candidate begins with the word "Newsletter", and [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] moved the core scope to channel-neutral orchestration — so the naming drift and the scope sharpening point the same way. Business decision, so it belongs in `docs/business/decisions/` rather than an ADR. Source: React client Phase 1, 2026-09-20.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 94, section "Bugs", position 29 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
