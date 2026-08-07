---
type: adr
status: accepted
topic:
  - architecture
  - provider
created: 2026-06-01
modified: 2026-08-02
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
enables:
  - "[[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]"
---


## Status

Accepted

## Context

Providers support different feature sets.

Not all providers offer the same delivery and tracking capabilities.

## Decision

Provider capabilities must be explicitly defined.

Core capabilities:

- send
- delivery status
- bounce feedback
- complaint feedback

Optional capabilities:

- click tracking
- open tracking
- audience synchronization
- provider-specific features

## Consequences

### Positive

- transparent integrations
- easier provider comparisons
- avoids hidden dependencies

### Negative

- capability mapping required

## Addendum 2026-08-02 — capabilities describe the *configuration*, not the protocol

Prompted by the question of whether to offer **SMTP** alongside HTTP APIs as a
way to send, and if so where it may be used.

**The framing.** Every email travels over SMTP eventually; the only question is
how the *application* hands the message over. An HTTP API is a convenience
layer on top — the vendor does the SMTP part, and adds batching, a synchronous
message id, and webhooks. SMTP is universal and portable (swap host and
credentials, no code change); an API is vendor-specific, faster, batchable, and
the only one of the two that reports back.

**The distinction that matters, and the one easy to miss:** "SMTP" covers two
unrelated situations.

- **An ESP's SMTP relay** (Resend, Brevo, SendGrid) is the same infrastructure
  and reputation as their API, reached through a different door. **Webhooks
  still fire**, because they are configured on the account rather than on the
  submission path. You lose batching and some per-message metadata; the
  feedback loop survives.
- **Generic SMTP** (a hosting provider such as Strato, a self-hosted Postfix, a
  Microsoft 365 or Google Workspace relay) is a pipe. No webhooks, no tracking,
  no bounce events.

So a capability declaration must describe **the configured provider instance,
not the protocol it speaks.** "SMTP" is not a capability level.

**Why this architecture is stricter about it than most.** Personalisation here
is fed by engagement: clicks arrive as webhooks, become signals
([[ADR-103 — Provider Events Are Normalized Into Internal Events]],
[[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]])
and drive the decision layer. A marketing send with no feedback path produces
**zero signals**, so the decision engine quietly starves. That is not a
deliverability inconvenience — it is the product's central mechanism switching
off, silently, with nothing failing.

**The derivation this ADR should carry:** combined with
[[ADR-106 — Bounce and Complaint Feedback Is Mandatory]], declared capabilities
**gate where a provider may be selected**. A provider that cannot report
bounces and complaints may not be chosen for a marketing send. Stated that way
the rule is honest and sorts the cases by itself — no adapter needs to be
special-cased, and an ESP relay that *does* report is not penalised for
speaking SMTP.

**Known gap:** nothing enforces this today. Capabilities are documented per
adapter but not declared in a form the send path can read, and the provider
selector offers every registered name. The enforcement point — and the SMTP
adapter that motivates it — are tracked in `docs/backlog.md`; the first real
consumer is the operator-facing **system mail** channel, which deliberately
wants a provider with none of these capabilities.

## Related ADRs

### Depends On

- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]

### Enables

- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]
