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

---

# Run 2 — 2026-09-27

## Resolved since run 1
- #11 **Isolated test DB** — ✅ Done 2026-09-19, and the entry records it is NOT
  an ADR (`backend/tests/conftest.py`).
- The **flow/journey** question — ✅ ADR-169 accepted 2026-09-19.
  **Consequence nobody propagated:** L150 (subscribe/DOI/unsubscribe) still says
  "do not build it as a one-off script — it is the first consumer of the
  flow/journey question in Needs ADR". ADR-169's own entry (L427) says the
  opposite: "the unsubscribe surface, double opt-in, ADR-163's opt-out scope —
  become buildable as ordinary routes on acceptance." **L150 is actionable today.**
- #4 **Mode-A subject/preheader** — partly absorbed; ADR-162 §1 moved the fields.

## New Needs-ADR items
| Item | Downstream |
|---|---|
| **Nothing in the catalogue is ever hard-deleted** (L398, user 2026-09-27) | Asset deletion (L364 point 4), content records, categories. Already implemented for content and named nowhere: `CONTENT_STATUSES = ("active","inactive")` at `content/service.py:85`. **Sequence with #15 data lifecycle** — its own text says they are the same question from opposite ends |
| **Catalogue field set as the union of manifest variables** (L400) | This is the M1 batch. Four sub-decisions before it is an ADR: `required` becomes a property of *(module, field)*; `label` likewise; the union needs grouping discipline; exact-name union is exact-name collision with no namespacing. **One tension to settle:** the 2026-09-22 ruling "we shouldn't rely on reading the module json" was about deriving *which channel* a field belongs to; this derives *which fields exist* |
| **What n8n and the CRM must actually do** | Sequenced after ADR-166. Upstream of L144 (machine-plane reads fall through to platform `view`) |
| **Sales/transaction data from CRM or DWH** | Probably a playbook chapter |

## The four ADRs the Variant Editor interview owes
| Record | Blocks or trails | Reasoning |
|---|---|---|
| **Content-catalogue field model** (1.8, 2.4, 2.8, 2.9, 2.10) | **BLOCKS** | Defines the vocabulary ~10 gaps write against; the only one destructive if guessed (unvalidated JSON column + a migration that invents titles and brands) |
| **Edit versus override** (3.1-3.9) | **SPLIT** | The 2.6 half — a slot may **not** be overridden, "enforceable, not conventional" — must precede `max_results`. The rest (field state, reach count, reason codes) trails |
| **Machine-vs-human lock policy** (1.7) | **TRAILS, narrowly** | The optimistic-concurrency layer needs no ADR (`updated_at` exists). The **asymmetry** — advisory for a person, binding for a machine — is a new rule about machine principals and builds on ADR-166. Build layer 1; write the ADR before the binding half |
| **Addendum to ADR-176** (1.6, *human beats system*) | **TRAILS, but lands with `max_results`** | No consumer today because a slot yields one pick. It becomes load-bearing the moment `max_results` works — that is when VE-6 ("nothing checks manual bindings against slot resolutions") can actually collide |

## Manager Workflow ADR debt — fully discharged
ADR-174, 175, 176 accepted; dated addenda written on ADR-142 (2026-09-24, ×2),
ADR-150 (2026-09-20, 2026-09-24), ADR-161 (2026-09-24), ADR-168 (2026-09-20,
2026-09-24). Verified in the files. **One record still owed**: the Cluster 4 Q2
pin-vs-exclude reversal, which "is not in an ADR — it lives in a docstring and
four documentation pages."

---

# Run 3 — 2026-10-08
Closed since run 2: field model (ADR-177), edit-vs-override (ADR-178 -> ADR-186),
lock policy (ADR-180), human-beats-system stays as task-220 (needs task-109).
Today's addenda answer no Needs-ADR item outright. task-136 gained a direct
dependant (ADR-153 retention/indexes). task-119 lost its technical blocker (task-53).
New Needs-ADR since run 2: task-246 consent note, task-294 related data,
task-299 follow-up sends, task-230 preview link, task-231 exclude kinds.
Widest live fan: task-136+117 (lifecycle) and task-135 (suppression).
