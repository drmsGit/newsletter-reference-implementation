---
id: TASK-29
title: this product has five names and none of them is canonical.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:56'
updated_date: '2026-10-05 20:07'
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Decided with the user 2026-10-05, one question at a time: provisional name Tarrow (display) / tarrow (slug), NOT legally cleared; one source of truth so a later rename is quick.
1. product.json at the repo root: name, slug, retired_names. Everything that runs reads it: backend/app/product.py -> FastAPI title and API description, Jinja global (nav), the session cookie ({slug}_session, not a bare 'session' — localhost cookies are shared across ports); the React client via vite.config (define + index.html title).
2. Things that cannot read a value (prose, file names, YAML) carry the name literally; backend/scripts/rename_product.py rewrites them from product.json — content, file names, and wikilinks to renamed files everywhere — and records the old name as retired. ADR wikilinks are protected (ADR titles are permanent).
3. Living documents and code get Tarrow; dated records keep their wording (ADRs, docs/queue, business decisions, interview-prep, playbook, docs/backlog.md, HANDOFF.md, react-session-brief, business-interview-baseline, agent memory). Plain 'newsletter' as a domain word stays (task-48).
4. Name-free where the name adds nothing: preview servers 'api' and 'client'; npm package stays 'manager-client'.
5. Kept as listed exceptions: dev database/user/password/container names (later stage, user wants them changed then); the GitHub repo and local folder (until the name is cleared — a new Tarrow GitHub account then). The script prints the checklist for these.
6. Test (backend/tests/test_product_name.py): runtime reads product.json; no retired name in living files; no wikilink to a retired name anywhere; the script renames correctly on a scratch repo. Client test: PRODUCT_NAME equals product.json.
7. Record: dated entry in docs/business/decisions/naming-brand-tarrow.md (used provisionally, not adopted); CLAUDE.md points at product.json.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 94, section "Bugs", position 29 in that section (top = do next). The description is the original entry, verbatim.

2026-10-01: a candidate name exists and is waiting on legal clearance (trademark / IP) before it is adopted. Held until that check is done; the name itself is deliberately not recorded here until it is cleared.

2026-10-04: checked with the user; the candidate name is still not cleared. Still held; task-30 taken instead.

2026-10-05, built with the user's decisions (one question at a time): Q1 one source (product.json) + a rename script for what cannot read a value + name-free identifiers where the name adds nothing; Q2 'Tarrow' for display, 'tarrow' as slug; Q3 living documents and code renamed, dated records keep their wording, links follow renamed notes everywhere, plain 'newsletter' stays (task-48); Q4 dev database/user/password/container kept for now, renamed later (filed as task-288); Q5 GitHub repo and local folder kept until the name is cleared (a new Tarrow GitHub account then).
Built: product.json; backend/app/product.py (API title/description, Jinja nav via a template global, cookie tarrow_session from the slug — not bare 'session', localhost cookies are shared across ports); vite.config.ts reads product.json (define __PRODUCT_NAME__, %PRODUCT_NAME% in index.html), branding.ts no longer spells the name; backend/scripts/rename_product.py (living text, file names, wikilinks everywhere, ADR links protected, --dry-run, prints what it cannot do). The migration ran through the same script: README, CLAUDE.md, CODE-REVIEW-BRIEF, docs/claude.md, backlog.config.yml, the MOCs and code docs; 'MOC - Newsletter Architecture' -> 'MOC - Tarrow', 'Newsletter Architecture Design Principles' -> 'Tarrow Design Principles'. Three sentences fixed by hand ('the Tarrow' -> 'Tarrow'). Preview servers renamed 'api' and 'client'.
Left as is, noted: the integration key prefix 'nri_' (does not spell a name; changing it could affect issued keys); 'nra_' in test fixtures is an arbitrary invented token.
Validation: 10 tests in test_product_name.py + 1 client test, failing first; with product.json switched to another name every runtime test still passes (it follows the file); 16 mutants all caught (each hard-coded name, a bare cookie, and every rule of the script and the stale-name check). Backend 1326, client 181, tsc, contract. Live: Jinja nav, React title and sign-in heading, and /openapi.json all read 'Tarrow'; the cookie rename signed the pane out, as expected.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The product has one name, Tarrow (slug tarrow), held in product.json at the repo root and still provisional — not legally cleared. Everything that runs reads it; prose, file names and YAML carry it literally and backend/scripts/rename_product.py rewrites them in one command (dry run first), while dated records keep their wording. The dev database names (task-288), the GitHub repo and the local folder are deliberate, listed exceptions. Recorded as a dated entry in docs/business/decisions/naming-brand-tarrow.md; CLAUDE.md points at product.json. Verified by 11 new tests, a run with another name in product.json, 16 caught mutants, both suites, and a live check.
<!-- SECTION:FINAL_SUMMARY:END -->
