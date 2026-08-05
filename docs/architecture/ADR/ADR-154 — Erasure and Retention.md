---
type: adr
status: proposed
topic:
  - architecture
  - privacy
  - security
  - governance
created: 2026-08-02
modified: 2026-08-02
source:
  - "Security Chapter design interview, Part 2 (playbook-strategy.md Decision Log, 2026-08-02)"
depends_on:
  - "[[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]"
  - "[[ADR-054 — Use Internal Recipient Identifiers]]"
  - "[[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]"
  - "[[ADR-153 — Audit and Accountability]]"
---

## Status
Proposed

## Context

[[ADR-004 — Privacy Operations as a First-Class Architectural Concern]] establishes that privacy operations are architecture, not an afterthought. It does not say what happens when a person exercises their right to erasure.

That question now has teeth, because [[ADR-153 — Audit and Accountability]] introduces an append-only accountability record. Article 17 says the person goes; an audit log says the record stays. Both are correct, and something has to reconcile them. The same tension applies to delivery history, engagement events and signal contributions, all of which describe a person and all of which the product needs.

## Decision

**1. Separate identity from activity.**
Audit entries, delivery executions, engagement events and signal contributions reference the **internal recipient identifier** — never the email address or any other contact detail. [[ADR-054 — Use Internal Recipient Identifiers]] already established this convention for other reasons; erasure is where it earns its keep.

**2. How deep an erasure goes is the company's determination, not ours — and the shipped default is full erasure.**
By default, an Article 17 request removes **everything connected to the person**: identity, signal contributions, engagement events, delivery executions, decision resolutions, and the person-referencing audit entries. This matches what companies operating a deletion interface actually do, and it is the position that needs no legal argument to defend.

The alternative — deleting only the *identity* row and keeping id-keyed activity — is **documented as a variation, not shipped as a toggle**. A company with a legal basis for retaining pseudonymised behaviour can implement it at a defined seam. We do not offer it as a setting, because shipping the option would amount to asserting that the arrangement is compliant, and that is a data-protection judgement this project declines to make on an adopter's behalf — the same refusal as [[ADR-144 — AI Data and Model Governance]] §3 and the two-installs stance in [[ADR-150 — Tenancy and Access Model]].

**2a. Why the variation is not obviously safe.** Removing the identity row leaves behavioural residue — engagement timing, category affinities, delivery history — which may be rich enough to single a person out. If it is, the data is *pseudonymised*, not anonymous, and remains personal data with the erasure incomplete. This is why full erasure is the default rather than merely one option among two.

**3. The enforcing rule: the audit log stores identifiers and never contact details.**
A single `"sent to anna@example.com"` in a payload field breaks the whole scheme, because erasure then means rewriting history rather than removing an identity. This is free to hold from the first line of the audit implementation and expensive to retrofit.

**4. Signals are personal data and are erased with the person.**
Signal contributions are a per-person behavioural profile. They live in a different table from the identity and are easy to overlook, so this is stated rather than assumed. They are also the richest source of potential re-identification, which is why 2a turns on them.

**4a. Erasure must propagate to the data warehouse.**
[[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] deliberately places long-term history and AI training data in the adopter's DWH rather than the operational database. An erasure that stops at the operational boundary therefore leaves the person's behavioural history intact in the exact place it is most likely to be used — **the export boundary would become an erasure loophole**. The export path has to carry the internal identifier so a downstream deletion is possible, and the playbook must state the obligation, since the DWH is outside our code and only the adopter can act on it.

**4b. Model training is the retention purpose that needs stating explicitly.**
Almost the only reason to want a person's behavioural data after they have asked to be erased is to keep using it for algorithms or model training — which is precisely the use a person exercising erasure is most likely to object to, and the least defensible to a regulator. This is called out rather than left implicit, because it is where an otherwise well-intentioned "we only kept the anonymous parts" quietly becomes indefensible.

**5. Rendered snapshots contain merged personal data and must be reachable by erasure.**
Stored rendered HTML holds the recipient's merged values and personalised content. Any erasure implementation has to reach it. This is the same question as the open snapshot-storage item, and it is a further argument for **reconstructing renders on demand** from a structured record rather than persisting per-recipient HTML.

**6. Proof of consent is retained in minimised form.**
Where a person has been erased, a minimal consent record is kept: internal identifier, timestamp, source, and what was granted — nothing else. Article 17(3)(e) permits retention for the establishment or defence of legal claims, and the defence against a UWG §7 complaint is showing the opt-in. This is a deliberate, scoped exception, not a general retention licence.

## Consequences

### Positive
- The default needs no legal argument to defend: the person asked to be forgotten, and they are.
- Erasure is a bounded, testable operation over a defined set of person-scoped tables rather than a sweep through every record in the system.
- Operator accountability survives, because operator-attributed audit entries reference the operator, not the recipient — so the two obligations stop being in conflict.
- The company can answer a DPO's question — "what happens to the audit trail when someone is erased?" — with a mechanism instead of a promise.
- Retaining consent proof in minimised form keeps the company defensible against a complaint from a person who has since been erased.
- The project takes no position on whether retaining pseudonymised behaviour is lawful, consistent with its stance everywhere else.

### Negative
- Full erasure loses data that has legitimate analytical value — historical delivery volumes and engagement baselines shift retroactively. Accepted: the alternative is asserting a compliance position we have declined to take.
- Whether the *documented variation* yields genuinely anonymous data is uncertain and company-specific (2a). Adopters choosing it need their own legal assessment, and the documentation must say so rather than implying our endorsement.
- The consent-proof exception means an erasure is not absolute, and that has to be explained rather than glossed.
- DWH propagation (4a) is an obligation we can specify but not enforce — it lives in the adopter's infrastructure, so the guarantee is documentation and process.
- Snapshot handling is a real implementation burden, currently blocked behind an undecided storage strategy.
- Retention *periods* are not settled here, so an adopter still has policy work before they are compliant — the architecture supplies the mechanism, not the number.

## Notes

- **Retention periods are deliberately out of scope.** How long delivery history, signals or audit entries are kept is the company's determination; the architecture's obligation is to provide a prune mechanism and to make the choice visible. This ties to the open data-lifecycle item in `docs/backlog.md`.
- **Breach response (Art. 33/34, 72 hours) is process, not architecture.** What the architecture owes is the ability to *detect* (the audit log) and to *scope* (knowing what data lives where). The response procedure belongs in the playbook's security chapter, as the adopter's documented process.
- The audit log may outlive the personal data it references. That is coherent rather than contradictory precisely because of point 1: what survives is an identifier and an action, not a person.

## Related ADRs

### Depends On
- [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]
- [[ADR-054 — Use Internal Recipient Identifiers]]
- [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]
- [[ADR-153 — Audit and Accountability]]
