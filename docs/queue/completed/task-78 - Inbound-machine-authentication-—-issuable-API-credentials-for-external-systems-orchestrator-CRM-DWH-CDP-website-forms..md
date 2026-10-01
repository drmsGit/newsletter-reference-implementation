---
id: TASK-78
title: >-
  Inbound machine authentication — issuable API credentials for external systems
  (orchestrator, CRM, DWH, CDP, website forms).
status: Done
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-01 20:43'
labels:
  - backend
dependencies: []
priority: p0
type: feature
ordinal: 203100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — RAISED TO P0 by the 2026-08-07 code review; now blocks public exposure, not just Mode B.** **Inbound machine authentication — issuable API credentials for external systems (orchestrator, CRM, DWH, CDP, website forms).** **Update 2026-08-07:** what was framed as a Mode-B prerequisite is also the reason **the JSON API is currently an unauthenticated control plane**. `main.py` guards the UI router and deliberately leaves every JSON router open — content, campaigns, rendering, snapshots, delivery, insight, decisions, recipients, audience, overrides, settings and provider. Anyone who can reach the port can read data, mutate campaign and content state, create send objects and trigger operations. That was a defensible local-development posture and it is not one for a reachable host; the UI being locked while the API beneath it is open is the worst of both, because it *looks* protected. **Also in scope, and easy to miss:** `POST /provider/events` (`providers/router.py:17-32`) calls `ingest_provider_event()` with **no signature verification at all** — the signed adapter route is `/provider/webhooks/resend`, but this generic sibling bypasses it, allowing arbitrary event and quarantine injection. Either make it machine-authenticated or drop it from production routing; public providers should only ever enter through signed adapter routes. **Scope for the first cut:** API keys with scopes are enough for a reference build — OAuth2/client credentials can follow — with the signed webhook route staying on provider signature verification rather than a key. Original framing follows. Surfaced 2026-07-31 (user). **Not optional and not "later" — it is a prerequisite for Mode B.** [[ADR-142 — Autonomous Workflows and the Automation Boundary]] decided the platform exposes **triggerable-action APIs** that an orchestrator calls, and that external systems may write and explicitly override the suppression gate (the "website form fires *this recipient must get this*" case). Every one of those calls has to be authenticated, so Mode B is not actually usable until this exists. The Cluster-3 ownership finding sharpens it: **automation is usually a different department**, so credentials must be **issuable and revocable per integration**, never one shared secret. **Scope to design:** (a) credential issuance / rotation / revocation for machine callers; (b) **per-integration authorization** — which system may invoke which actions (n8n may trigger a send; a website form may only pin a recipient); (c) audit — machine-initiated actions land in the same action history ADR-142 already requires. **Distinct from the parked Security chapter**, which covers *human* auth (login/SSO/roles) — this is *machine* auth: related, separately scoped. **Hypothetical driving scenario — explicitly NOT a confirmed requirement (real client, presented to 2026-07):** the client has **not signed the CDP contract**, so nothing is implemented. Their current *assumption* is that the CDP will be the running AI system, offering only prompting — a user types *"collect everyone interested in X from the last two weeks and in N days send them something interesting"* — with the CDP perhaps assembling an audience while **another system translates intent into action**. **The user intends to challenge that assumption:** if the CDP's AI doesn't actually deliver results, there is little reason to use it, and this platform — or its connection to something like n8n — may be the better workflow. **So this particular integration may never be needed**; it is recorded as *one hypothesis about who calls the API*, not as a committed requirement. **What is not hypothetical is the underlying need:** inbound machine auth is required for Mode B regardless of which system turns out to be the caller. The scenario stays architecturally instructive — it shows ADR-142's boundary holding with an **LLM-speaking orchestrator** in n8n's role — and adds one design consideration: the action API should be **describable as tools** (name + description + input schema) so an LLM-driven caller can consume it without bespoke glue; MCP is the emerging standard for exactly this. **Direction only, not a build decision** (per the "don't over-commit to unvalidated detail" principle). Source: user, 2026-07-31.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 232, section "Features", position 31 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed as already done (verified 2026-10-01). Launch gate 3 records inbound machine authentication as built 2026-09-18 (ADR-166 accepted and built), and the JSON API is guarded by enforce_api_policy. The unauthenticated POST /provider/events sibling this entry named is now mapped in backend/app/auth/policy.py to insight.write, so it requires an authenticated principal holding that permission.
<!-- SECTION:FINAL_SUMMARY:END -->
