---
type: adr
status: proposed
topic:
  - architecture
  - security
  - access
created: 2026-08-02
modified: 2026-08-02
source:
  - "Security Chapter design interview, Part 2 (playbook-strategy.md Decision Log, 2026-08-02)"
depends_on:
  - "[[ADR-150 — Tenancy and Access Model]]"
enables:
  - "[[ADR-153 — Audit and Accountability]]"
---

## Status
Proposed

## Context

[[ADR-150 — Tenancy and Access Model]] introduces users, roles and brand-scoped assignment. It does not say how a person proves who they are.

Two constraints shape the answer. The platform is **self-hosted by mid-market companies**, often without a dedicated identity infrastructure, so anything requiring an IdP as a precondition excludes much of the target audience. And ADR-150 put **external agency staff** inside the system as real Admins and Managers, which makes both credential handling and account lifecycle sharper than they would be for internal-only users.

There is also a piece of domain knowledge this project already owns that bears directly on the mechanism: the signal layer treats opens as unreliable because **Apple Mail Privacy Protection and corporate scanners pre-fetch email content**. The same behaviour applies to links.

## Decision

**1. Passwordless email authentication, using a typed code — not a magic link.**
The user enters their address, receives a short numeric code, and types it back. No password is ever set, stored, reset or breached.

The code-over-link choice is deliberate and follows from the pre-fetch problem above: a security scanner or mail client that fetches the link *consumes a single-use token before the human ever clicks it*, producing "this link has already been used" as a routine, unexplainable support case. A typed code has no such failure mode. This is the same pre-fetch behaviour the signal layer already accounts for, arriving in a different place.

**2. Code hygiene is part of the decision, not an implementation detail.**
Short time-to-live; single use; rate limited **per address and per IP**; and an **identical response whether or not the address exists**, so the login form is not an account-enumeration oracle. Codes are stored hashed, not in clear text.

**3. Sessions rotate, expire twice, and are revocable.**
The session identifier rotates on login. Both an **absolute** lifetime and an **idle** timeout apply. Sessions are server-side revocable — which is what makes deactivation in point 5 take effect immediately rather than at next expiry.

**4. SSO and SCIM are documented, not built.**
Passwordless solves *authentication*. SSO solves *lifecycle governance* — central policy and, above all, automatic deprovisioning. They are different problems, and conflating them is why "passwordless makes SSO unnecessary" is only half true. For the standard package we ship the seam and the documentation; a company needing automatic deprovisioning wires its own IdP. This matches the architecture-plus-one-worked-example posture used for send providers and AI models.

**5. Offboarding is admin deactivation plus a visible access list.**
An Admin can deactivate an account, which revokes its sessions immediately. A **user access list** shows every account with its role assignments, its last login, and whether it is external. This is the standard-package answer to "an agency employee left and nobody told us."

**6. Passkeys (WebAuthn) are an optional layer on top — never a replacement for the code.**
A passkey cannot be the only mechanism, because **a passkey has to be enrolled**: proving identity for the first time, and recovering when a device is lost or replaced, both require a second path. That path is the email code. So the code flow is not the alternative to passkeys; it is the foundation they stand on, and it is mandatory either way.

Given that, passkeys are worth adding as a **strengthening option a user may enrol**: they are phishing-resistant, involve no shared secret in transit, and directly address the email-as-single-point-of-failure weakness below. Browser and platform support is effectively universal on current versions; the genuine remaining gaps — older managed Windows fleets, locked-down devices with the platform authenticator disabled, shared machines — are real enough in the mid-market that they argue for *optional*, not *required*.

Sequence follows from this: ship the code flow, add passkeys as an additive layer. Adding them later is contained (a credential table, two ceremony endpoints, a WebAuthn library) and does not disturb the existing flow; removing the code flow later is impossible, because it is the recovery path.

## Consequences

### Positive
- No password storage, so no password breach, no reset flow, no rotation policy, and one whole category of Art. 32 obligations does not arise.
- Nothing to deploy or integrate before first login; a self-hosted company with a mailbox can use it.
- The same mechanism the company will use for its public-facing library site, so one pattern is learned once.
- Sessions being revocable makes deactivation real rather than eventual.
- The access list gives a controller something concrete to review during an audit.

### Negative
- **Email becomes the single point of failure**: whoever controls the mailbox controls the account. Accepted knowingly; the mitigations are session revocation, the audit trail and write-only credentials ([[ADR-152 — Secret and Credential Handling]]). A user who enrols a passkey escapes this, but the recovery path remains email, so the weakness is reduced rather than removed.
- **Passkeys add a second mechanism to support, document and test** — enrolment, multiple devices, device loss — and being optional means both paths exist permanently rather than one replacing the other.
- **Nothing signals that an external operator has left the agency.** Deactivation is a manual action that no one is prompted to take, and a stale external Admin account is the most valuable thing an attacker could find. The access list is the mitigation and it is a weaker control than automatic deprovisioning — this is the principal residual risk of the standard package.
- Login depends on mail deliverability and adds seconds of latency; a mail outage is a login outage.
- Companies with an existing IdP will ask why they cannot use it on day one, and the answer is a documentation page rather than a feature.

## Notes

- Passkeys are **not gating** for the standard package. The decision above settles the *shape* (additive, optional, code flow mandatory underneath); the build is tracked separately rather than blocking this ADR.
- **Still open: step-up authentication** for destructive or high-value actions — triggering a real send, changing credentials, deactivating a user. Given that a mailbox compromise yields full Admin, this deserves a deliberate answer rather than an omission. Passkeys make an attractive step-up factor for users who have enrolled one, which is a further argument for point 6 but does not by itself decide the question.
- Machine authentication for inbound API callers is a **separate concern** with its own scope, tracked in `docs/backlog.md` as a prerequisite for Mode B ([[ADR-142 — Autonomous Workflows and the Automation Boundary]]). This ADR covers human authentication only.

## Related ADRs

### Depends On
- [[ADR-150 — Tenancy and Access Model]]

### Enables
- [[ADR-153 — Audit and Accountability]]
