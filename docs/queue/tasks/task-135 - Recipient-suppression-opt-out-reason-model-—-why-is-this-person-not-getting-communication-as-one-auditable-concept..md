---
id: TASK-135
title: >-
  Recipient suppression + opt-out reason model — "why is this person not getting
  communication?" as one auditable concept.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-09-27 14:29'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 301900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Recipient suppression + opt-out reason model — "why is this person not getting communication?" as one auditable concept.** Surfaced 2026-07-31 (AI-layer interview, Cluster 3 / Q16). Cluster 3 (Mode B automation) only needs the *interface* — flows and external systems can **read, write and explicitly override** a suppression gate — and that part is settled in the Mode B ADR. What is **not** decided, and belongs here as a **data-model ADR rather than an AI one**, is the concrete shape. **Agreed direction:** a single **`suppressed_until`-style recipient-level gate** (one place, not several tables/fields), checked at audience resolution **beside the consent floor**, always paired with a **log recording *why*** — the log is the point, not an optional extra. Deliberately covers more than fatigue: **fatigue** (system-set, short), **a manual or AI decision** ("recipient is in cycle XXX, shouldn't get any emails" — especially useful for **reactivation** cycles), and recipient-set **pause/snooze** (§M2). **Ruled out during the interview:** modeling it as a `consent_status` value (a platform-only value would register as CRM divergence in `detect_consent_drift` — the same reason `suppress_recipient` deliberately skips `ConsentSyncLogDB`), and modeling it as an audience exclude rule-block (rule-blocks are per-*audience*; suppression is a property of *the person* and must hold across every campaign). **Three-tier precedence agreed:** (1) **consent** = hard floor, never overridable; (2) **suppression** = *soft* — not easy to overwrite but overridable by an explicit, logged act (the existing pin mechanism in `resolve_audience`, `… ∪ pins`, now also callable by external systems — e.g. a website form firing "this recipient must get the masterclass mail"); (3) include/exclude rule-blocks = normal audience logic. **Still to decide in this ADR:** (a) the concrete table/field shape, and whether the "why" log is its own table or an extension of the Mode-B action/audit log; (b) an **opt-out code / reason taxonomy** covering "opt-out because bounce / active unsubscribe / block / …" — note the **GDPR-block case is just a general opt-out**, with the GDPR information itself owned by the **CRM** ([[ADR-120 — CRM as Customer Source of Truth]] / [[ADR-122 — Minimal Consent Model Required]]), so the platform stores the *code*, not the legal record; (c) how a **cycle-scoped** suppression ("while in cycle XXX") is modeled, given it has no known end date and doesn't map onto a plain `until` timestamp. Ties to: [[ADR-122 — Minimal Consent Model Required]], `suppress_recipient` (`recipients/service.py`), the audience consent floor in `resolve_audience`, and the pause/snooze concept in `docs/business-interview-baseline.md` §M2. Source: user, 2026-07-31 (AI-layer interview, Cluster 3 Q16).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 487, section "Needs ADR", position 19 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
