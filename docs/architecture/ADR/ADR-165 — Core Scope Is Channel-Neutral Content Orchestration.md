---
type: adr
status: accepted
topic:
  - architecture
  - boundaries
created: 2026-09-12
modified: 2026-09-12
source:
  - "Omni-Channel design interview (interview-prep, closed 2026-09-01)"
depends_on:
  - "[[ADR-001 — Newsletter Architecture Boundaries]]"
  - "[[ADR-012 — Content Records Represent Communication Units]]"
  - "[[ADR-160 — Channel Model and Composition]]"
enables:
  - "[[ADR-002 — API First Architecture]]"
  - "[[ADR-010 — Newsletter Content Source of Truth]]"
  - "[[ADR-050 — Delivery Layer is Part of the Reference Architecture]]"
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
  - "[[ADR-125 — Define a Minimal Reference Architecture]]"
---

## Status
Accepted

## Context

[[ADR-001 — Newsletter Architecture Boundaries]] scoped the core to
"newsletter-specific responsibilities" — content source of truth, newsletter
composition, module system, rendering, snapshots, provider abstraction,
optional automation and decision layers — with external enterprise systems
(CRM, CDP, ERP, CMS, DWH, consent management, identity resolution) named as
integration points, not core components.

[[ADR-160 — Channel Model and Composition]] flagged, without resolving, that
this framing no longer describes the architecture: roughly 80% of the system
generalises to any API-reachable channel (email, push, letter, paid social)
as a consequence of earlier decisions — [[ADR-012 — Content Records Represent Communication Units]] defines a record as a communication unit, not an email;
the decision, audience and signal layers are already channel-neutral; and
ADR-160 through [[ADR-164 — Channel Feedback and Signals]] built the channel
layer itself on that foundation rather than against it. "Newsletter-specific"
was never quite accurate even when ADR-001 was written — it described the
first worked example, not the boundary — and omni-channel makes the gap
between the label and the thing impossible to keep ignoring.

**This is the first supersession in this repository.** Nothing has been
superseded before now; ADR-001's Decision is not edited, in line with the
never-edit-an-Accepted-Decision rule — this record replaces it and ADR-001's
status changes to point here.

What ADR-001 got right and what this record keeps unchanged: the boundary
around *enterprise systems* stays exactly where it was. This is not a scope
*expansion* into CRM/CDP/ERP/DWH territory — those remain integration points,
never core components. What changes is only the axis ADR-001 used to draw the
"core" side of the line: *newsletter* was the wrong noun for what the core
actually does.

## Decision

**1. The core is content management and orchestration for any API-reachable
channel — not a newsletter system with channels bolted on.**
The unit of work is a communication unit ([[ADR-012 — Content Records Represent Communication Units]]) composed, decided, personalised and rendered
for delivery through a channel. Email remains the first and most complete
worked example, not the definition of the boundary. "Newsletter" describes
the origin story and the primary reference implementation, not the
architecture's scope.

**2. The enterprise-system boundary from ADR-001 is retained without change.**
CRM, CDP, ERP, CMS, data warehouse, consent management platforms and identity
resolution systems remain outside the core, exactly as ADR-001 decided.
Omni-channel does not touch this line — it only replaces the axis the *other*
side of the line was described by.

**3. The core responsibilities list is restated in channel-neutral terms:**
- content source of truth (a communication unit, per channel)
- composition (per-channel variants under a shared campaign, per
  [[ADR-160 — Channel Model and Composition]])
- module system (per-channel manifests, namespaced by channel)
- rendering (a per-channel renderer returning role-tagged artifacts, per
  [[ADR-162 — Channel Rendering and Artifacts]])
- snapshots
- provider abstraction (per execution shape, per
  [[ADR-161 — Channel Execution Shapes]])
- optional automation and decision layers

This is the same list ADR-001 gave, with "newsletter composition" widened to
"composition" and nothing else added or removed. No new responsibility is
introduced by this record.

**4. A channel is admitted to the core by satisfying the existing seams, not
by special pleading.**
[[ADR-160 — Channel Model and Composition]] through
[[ADR-164 — Channel Feedback and Signals]] already state what a channel must
provide (a module manifest, a provider adapter matching one of the declared
execution shapes, a renderer). Nothing here adds a second admission test —
this record only says that satisfying those seams is what "in scope" means,
rather than "is it email".

## Consequences

### Positive
- The architecture's stated scope now matches what ADR-160–164 already built, closing a gap that would otherwise sit in the foundational boundary record indefinitely.
- The enterprise-system boundary — the part of ADR-001 doing the real work of keeping this from becoming a CRM/CDP/ERP — is carried forward unchanged, so nothing about vendor neutrality or scope discipline is loosened.
- Future channels are admitted by an existing, checkable test (do the ADR-160–164 seams hold) rather than a boundary that has to be re-litigated per channel.
- The playbook's core narrative — vendor-neutral orchestration architecture — now matches the boundary record instead of being ahead of it.

### Negative
- Every place that read "newsletter" as the scope boundary (naming, positioning language, parts of the playbook outline) needs to be checked against this record; this ADR does not audit that prose, it only changes the architectural decision.
- The repository's first supersession sets precedent — reviewers should expect ADR-001 references elsewhere to increasingly mean "see ADR-165" and should not assume ADR-001's Decision text still describes current scope.
- "Newsletter" remains in the product's working name and in `ADR-001`'s own title; this record does not rename the project, only the architecture boundary.

## Notes

- This record makes no change to [[ADR-160 — Channel Model and Composition]] through [[ADR-164 — Channel Feedback and Signals]] — it resolves the loose end those records flagged (ADR-001's fate) without altering their own Decisions.
- Business-side implications (positioning copy, product naming, playbook chapter framing) are explicitly out of scope here and belong in `docs/business/decisions/` if and when they are taken up.

## Related ADRs

### Depends On
- [[ADR-001 — Newsletter Architecture Boundaries]]
- [[ADR-012 — Content Records Represent Communication Units]]
- [[ADR-160 — Channel Model and Composition]]

### Enables
- [[ADR-002 — API First Architecture]]
- [[ADR-010 — Newsletter Content Source of Truth]]
- [[ADR-050 — Delivery Layer is Part of the Reference Architecture]]
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-125 — Define a Minimal Reference Architecture]]

### Referenced By
- [[ADR-160 — Channel Model and Composition]]
