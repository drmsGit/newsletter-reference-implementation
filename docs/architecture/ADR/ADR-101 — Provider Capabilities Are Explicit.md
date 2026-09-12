---
type: adr
status: accepted
topic:
  - architecture
  - provider
created: 2026-06-01
modified: 2026-09-12
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

## Addendum 2026-09-12 — extended from email providers to channel providers

Prompted by [[ADR-161 — Channel Execution Shapes]] point 6, which needed this
ADR to widen scope rather than build a second capability system, and by
[[ADR-164 — Channel Feedback and Signals]] point 1, which needed the same
scope for feedback granularity specifically.

**The extension.** This ADR was written against email providers. It now
applies to **channel providers generally** — the same ADR, a wider scope, no
second capability-declaration system introduced alongside it. A **channel-
level** capability file was considered and rejected in ADR-161: it would only
stay correct if kept current with everything a channel could possibly do,
and it has no owner — it goes stale the moment any one vendor ships
something new, whereas a provider file describes one thing its author
actually knows. Duplication across provider files is accepted as the cheaper
failure, the same trade this ADR's 2026-08-02 addendum already made for the
SMTP case: a capability declaration describes **the configured provider
instance**, not the channel or the protocol it happens to speak.

**Two things this addendum records as provider capabilities, not channel-level
facts, because both vary by vendor rather than by channel:**

- **Batch-versus-per-message handoff.** Some channel vendors — a letter shop
  is the motivating case — take a per-message API call; others want a CSV
  plus a PDF bundle over SFTP. That is a difference between vendors *of one
  channel*, exactly the discriminator this ADR already draws for SMTP versus
  an ESP's API. It is not a fact about "letter" as a channel; it is a fact
  about which letter shop is configured.
- **Feedback granularity is declared per provider, never per channel.**
  Whether feedback comes back per recipient or only in aggregate is a
  property of the configured provider instance. A social platform might
  someday offer per-recipient feedback where today it only reports
  aggregate; encoding "social = aggregate" anywhere in the architecture
  would bake a vendor's current limitation in with a shelf life, and the
  first vendor to improve would falsify the encoding. Declaring it per
  provider means a platform that starts reporting per-recipient events needs
  only a changed provider file, nothing else.

Both are the same argument this ADR's existing 2026-08-02 addendum already
made for SMTP — a capability declaration describes the configured provider
instance — extended from email specifically to channel providers in general.
Nothing above changes this ADR's Decision section; core and optional
capabilities are unchanged, and the gating relationship with [[ADR-106 —
Bounce and Complaint Feedback Is Mandatory]] is unchanged.

## Related ADRs

### Depends On

- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]

### Enables

- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]

### Referenced By

- [[ADR-161 — Channel Execution Shapes]]
- [[ADR-164 — Channel Feedback and Signals]]
