---
id: TASK-6
title: 'The SPA cannot sign in, and the builder screens cannot edit.'
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
  - frontend
dependencies: []
priority: p1
type: bug
ordinal: 100600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — MOSTLY DONE, verified 2026-09-27; one item remains and is tracked elsewhere. P1 against [[ADR-002 — API First Architecture]]. The SPA cannot sign in, and the builder screens cannot edit.** **Corrected 2026-09-19.** An earlier version of this entry claimed "73 UI write routes, 33 JSON write routes" across fifteen missing capability areas. That comparison was made on **path prefixes** and over-counted badly: `/ui/send-instances/{id}/send` and `/delivery/send-instances/{id}/send` are one capability under two prefixes, as are audience groups, categories and decision execution. Most of the campaign, content and audience core **does** exist in JSON. The corrected list is below and is much shorter — but it contains something the crude version missed entirely. **Blocks the React MVP, in order:** **(1) There is no JSON sign-in.** `/ui/login` and `/ui/login/verify` are HTML form posts that redirect, so a client that authenticates with the session cookie ([[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]) has no way to *obtain* one. ADR-168 is unusable in practice until this exists. **(2) No edit endpoints for the builder**: variant, module and decision slot can each be created and deleted over JSON and not edited — the campaign/variant builder is MVP screen one. **(3) Audience is half there**: groups and members exist; rule blocks, bulk-add, recalculate and suggest-from-campaign do not, which is most of what the audience screen does. **(4) Two cron seams are UI-only** — `/ui/deliveries/process-due` and `/ui/approvals/process-expired`. An orchestrator cannot drive either, which is odd given that [[ADR-142 — Autonomous Workflows and the Automation Boundary]] expects exactly that, and both are documented as "a real deployment points cron at this". Plus `send-test`. **Deliberately NOT in scope, and not a gap:** settings, users, roles and Mode-A polish stay Jinja-only per `docs/business/BETA-SCOPE.md` §5, which already decided the MVP cut is not parity. And approving a held action is refused over the API **by design** — a machine that can approve its own request has defeated the mechanism. Brands, integrations and duplication are real gaps but behind the four above. Source: user question, 2026-09-19. **Status 2026-09-27 — three of the four blockers are built and this entry had not been closed.** Verified against the routers, not assumed. **(1) JSON sign-in exists**: `POST /auth/session/request`, `POST /auth/session/verify`, `GET /auth/session` and `POST /auth/session/brand`, all mounted on `session_router` behind `enforce_api_csrf` — built with Phase 1 of the React client, which is also where the CSRF-after-reload gap was found and closed. [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] is usable in practice. **(2) The builder edit endpoints exist**: `PUT /campaigns/variants/{id}`, `PUT /campaigns/modules/{id}`, and both `PUT` and `PATCH` on `/campaigns/decision-slots/{id}`. **(4) Both cron seams and `send-test` have JSON routes** — `/delivery/process-due`, `/approvals/process-expired` (shipped with the approvals router on 2026-09-20) and `/delivery/send-test`, all four of which also gained response models in the schema-honesty pass. **(3) is the only survivor, and it is narrower than written**: audience rule blocks (`GET`/`POST`/`PATCH`/`DELETE /{group_id}/blocks`), bulk-add (`POST /{group_id}/members`) and `POST /{group_id}/recalculate` all exist. **What is missing is suggest-from-campaign**, which is now tracked as its own gap out of [[Manager Workflow - design interview]] Q1 — where suggestion became *the primary way an audience comes into being*, so it is a larger item than "one more route" and does not belong filed under this entry. **Why this matters beyond bookkeeping:** this was the backlog's headline answer to "what blocks the React client", and it overstated the remaining work by roughly four to one. A sequencing pass on 2026-09-27 ranked against it before the staleness was found. **The lesson is the one this entry already demonstrates once** — it was itself "Corrected 2026-09-19" after an earlier version over-counted by comparing path prefixes. An entry that answers a recurring question needs closing the day it stops being true, because it will be read as current.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 41, section "Bugs", position 6 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
