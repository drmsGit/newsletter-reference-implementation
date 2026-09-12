---
name: needs-adr-downstream
description: The 15 Needs-ADR items and what each interview would unblock. Built 2026-09-12; omni-channel is now closed.
metadata:
  type: project
---

Rule: the unblocking event is "the interview happens", not "the code ships".
These 15 were deliberately left open across several review passes — do not propose
resolving them; record what sits behind each.

| # | Needs-ADR item | Downstream |
|---|---|---|
| 1 | **Omni-channel** | **RESOLVED 2026-09-12** — ADR-160..165 accepted, ADR-001 superseded by ADR-165. Nothing built. Backlog still lists it 📋. Downstream is now implementation, not design: consent migration, artifact rename, module namespacing, signal channel column, delivery transfer rows |
| 2 | System email transport/templating/triggering | System-mail-channel Feature; Gate 4b's admin-lockout path; transactional sends (#13) |
| 3 | Concurrent actors contention model | AI spend-cap race; bulk-send batching (#6); double-send guard in the pre-send bundle; send-instance concurrency |
| 4 | Mode-A subject/preheader vs decision-slot content | Recall-past-suggestions Feature; shared approval inbox; per-task model selection. **Reshaped by ADR-162 §1** — subject/preheader become module fields, so the "one task shape" answer is partly pre-decided |
| 5 | Dynamic decision content × audience ordering | Audience override mechanism; engagement-driven audience suggestions (PARKED); Phase 3D; cost/token preview |
| 6 | Bulk send batching + send-timing | Partial-failure reconciliation; pre-send safety net; provider choice on campaign send; P1 send-status (partial); performance-notes. **Widest fan of the open 14** |
| 7 | Provider contact sync | CRM opt-out relay; consent drift. Its own premise correction says it may not be needed — see cost-of-delay Decays |
| 8 | Snapshot storage strategy | Snapshot atomicity bug; ADR-062 gap; ADR-005 merge-context; per-recipient artifacts. **Half-answered by ADR-162 §3** (two artifacts + hash decided; medium still open) |
| 9 | Shadow-variant validation | A/B test component; override-outcome comparison; negative affinity |
| 10 | Guaranteed placement / sponsored slots | Anti-bubble exploration; tiebreak variant |
| 11 | Isolated test DB | Tests/CI Feature and its six named missing tests; verification of every fix in the queue; beta DoD #4 |
| 12 | Hero/CTA catalogue membership | Image upload/media picker; brand/theming; interacts with ADR-162 §5 module manifests |
| 13 | Transactional sends | System-mail channel; suppression (#14). **Partly pre-decided** by ADR-163 §3 and the ADR-122 addendum's `(channel, purpose)` grid |
| 14 | Suppression + opt-out reason model | Stage 3 of ADR-163 §7's gate stack; CRM opt-out relay; pre-send safety net; reactivation audiences. Downstream OF the P0 fix, not upstream of it |
| 15 | Data lifecycle / retention | DWH export + prune; auth session and login-code cleanup (code-slimmer S4); ADR-154 erasure; snapshot retention |
