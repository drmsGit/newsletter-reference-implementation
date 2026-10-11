---
type: adr
status: accepted
topic:
  - architecture
  - security
  - access
created: 2026-08-02
modified: 2026-10-11
source:
  - "Security Chapter design interview, Part 2 (playbook-strategy.md Decision Log, 2026-08-02)"
depends_on:
  - "[[ADR-150 — Tenancy and Access Model]]"
enables:
  - "[[ADR-153 — Audit and Accountability]]"
---

## Status
Accepted

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
- Machine authentication for inbound API callers is a **separate concern** with its own scope, now designed in [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]], which also carries its status as a prerequisite for Mode B ([[ADR-142 — Autonomous Workflows and the Automation Boundary]]). This ADR covers human authentication only.
- **Implementation status, 2026-09-14:** Points 1, 2, 3 and 5 are built — passwordless typed codes stored hashed, short-lived and attempt-limited; sessions carrying both an absolute and an idle expiry and revocable server-side; deactivation revoking sessions immediately; and the access list at `/ui/users` showing role assignments, last login and whether an account is external (`backend/app/auth/db_models.py`, `backend/app/auth/router.py`, `backend/app/auth/service.py`). Rate limiting of code *requests* per address and per IP — required by point 2 and previously missing — was built on 2026-09-13 (`LoginCodeRequestDB`). Points 4 and 6, SSO/SCIM and passkeys, are documented and not built **by decision**, not by omission. **Step-up authentication is unbuilt** and remains open, as the note above says.

## Addendum 2026-09-29 — an identical response also arrives in the same time

Prompted by task-5, and by Q5 of
[[Interview Prep - Auth, Permissions, Machine Principals]], decided by the user on
2026-09-29. Point 2 stands as written. This addendum records what *identical*
turned out to require.

**Point 2's response rule was built, and it moved the oracle rather than
closing it.** Gate 4b in [[LAUNCH-GATES]] implemented the single-response rule and
was closed for the response oracle on 2026-09-13. Both sign-in routes in
`backend/app/auth/router.py` — the form `POST /ui/login` and the JSON
`POST /auth/session/request` — returned the same 303 or the same 202 and body
for a known, unknown or deactivated address and for a failed send. But
`request_login_code` in `backend/app/auth/service.py` ran inline. For a known
address it superseded outstanding codes, inserted a row, committed, and then
called the mail provider synchronously over HTTPS through `deliver_code`. For an
unknown address it returned after one SELECT. Against a real provider, the
identical response arrived several hundred milliseconds later when the account
existed. The response oracle had become a timing oracle, found on 2026-09-19.

**1. Point 2's "identical response" includes arriving in the same time.** Timing
is part of the response. A status and body that say nothing are not enough if
the latency says something.

**2. A code is delivered after the response, never inside the request path of a
route that answers a sign-in request.** The service is split in two.
`issue_login_code` does the lookup, supersedes old codes, inserts the new one
and commits, then returns the address and code, or None. It sends nothing.
`deliver_code` sends. Both routes call `issue_login_code` and pass
`deliver_code` to FastAPI `BackgroundTasks`, which runs it after the response
has been sent. `deliver_code` takes no database session, never raises, and logs
a failed send itself. `request_login_code` survives as issue-then-deliver,
synchronous, for local development, scripts and tests only. No HTTP route calls
it. **Any future route that issues a code uses the same split:** issue in the
request, deliver in the background.

**3. The remaining gap is stated as a bound, not as constant time.** What
remains is `issue_login_code`'s own database work for a known address. On a
development machine with the mock provider it measured 0.6 ms median (known
0.92 ms against unknown 0.32 ms, 300 samples each). The existing throttle limits
how often anyone can sample it: 5 code requests per address per 15 minutes and
20 per client per 60 minutes. The throttle is applied **before** the user lookup
in both routes, so a throttled request costs the same work either way. So the
claim is *sub-millisecond, sampled at most five times per address per quarter
hour*, not *constant-time*.

A response-time floor, where every sign-in is padded to a fixed minimum, was
considered and not adopted. Every sign-in would pay the full floor. A worker
would be occupied while sleeping. And the gap would reopen whenever a send took
longer than the floor, so the floor would only move the threshold at which the
oracle reappears.

**4. Connection reuse was checked, not assumed.** Against a real uvicorn server
with delivery artificially slowed to 500 ms, the median was 15.8 ms for a known
address and 16.4 ms for an unknown one over fresh connections, a gap within
noise. On a kept-alive connection, the next request after a known-address
request took 11.9 ms. It does not wait for the background send, so the reused
connection is not a side channel. Every background send completed.

**What it costs.**

- **A failed send is visible only in the server log, after the response.** This
  was already the only signal, because the response never said anything, but it
  is now further from the request that caused it.
- **Background tasks die with the process.** A crash between the response and
  the send loses that code, and the user requests another. This is acceptable
  because codes are cheap and throttled, but nothing retries it.
- **The bound depends on the throttle staying in front of the lookup.** Moving
  the throttle behind the user lookup, or removing it, would turn the
  sub-millisecond gap back into something that can be sampled freely, and no
  response would change to show it.

Gate 4b in [[LAUNCH-GATES]] is updated separately to reflect this fix. This
addendum does not change it. Nothing else in point 2 changes: codes are still
short-lived, single-use, hashed and rate limited per address and per IP.

## Addendum 2026-10-09 — session lengths are the company's, attack resistance stays in code

Prompted by finding P2-B1 in [[business-interview-baseline]] ("Security numbers
are code; marketing numbers are settings rows — against the repo's own stated
rule"), decided by the user in the 2026-10-09 interview review and logged in the
[[playbook-strategy]] decision log under that date. Points 2 and 3 stand as
written. This addendum records who owns the numbers they leave open.

**Points 2 and 3 name properties, and the build fixed their values in code.**
Point 2 asks for a short time-to-live, an attempt limit and request limits per
address and per IP. Point 3 asks for an absolute lifetime and an idle timeout.
All of them are module constants in `backend/app/auth/service.py:39-53`:
`CODE_TTL_MINUTES = 10`, `CODE_MAX_ATTEMPTS = 5`, `CODE_REQUESTS_PER_ADDRESS = 5`
per `CODE_REQUEST_ADDRESS_WINDOW_MINUTES = 15`, `CODE_REQUESTS_PER_CLIENT = 20`
per `CODE_REQUEST_CLIENT_WINDOW_MINUTES = 60`, `SESSION_ABSOLUTE_HOURS = 12` and
`SESSION_IDLE_MINUTES = 60`. `backend/app/settings/service.py` has getters for
signal weights, half-lives, the AI provider, the AI spend cap, the send
recipient cap and per-task models, and none for any of these.

The repository's own rule points the other way.
[[ADR-161 — Channel Execution Shapes]] point 8 states it: "Numbers belong to the
company, the mechanism to us, the same split already used for retention periods
and the AI spend cap." [[ADR-164 — Channel Feedback and Signals]] point 10
repeats it for channel weights, [[ADR-154 — Erasure and Retention]] applies it
to retention periods in its Notes, and
[[ADR-144 — AI Data and Model Governance]] point 5 to the spend cap. Read
literally, the rule would make every number above a company setting. The
opposite answer, keeping all of them in code and recording the whole of
sign-in and sessions as the exception, would leave a company whose works
council or auditor sets its own session lengths with no seam short of a fork.
Neither was adopted. The numbers are split by whom they serve.

**1. The absolute session lifetime and the idle timeout are company policy and
become company settings, each clamped to a safe range.** How long a person stays
signed in, and how long an unattended screen stays usable, is a workplace rule.
Twelve hours and sixty minutes encode one working day and one coffee break. A
works council or an ISO 27001 auditor may require other lengths, and the company
must be able to set them without a fork. Point 3 is unchanged: both expiries
still apply, and a setting moves their lengths within the range without removing
either.

The safe ranges are not set here. They belong to the build's final-design pass.
Two facts in the code bear on them. The idle timeout slides on a write of
`last_seen_at` that happens at most once per `TOUCH_INTERVAL`
(`backend/app/auth/service.py:905`, 60 seconds), which that constant's comment
describes as "short against the idle timeout"; an idle lower bound close to it
would break that assumption. And the absolute lifetime also sets the session
cookie's `max_age` (`backend/app/auth/router.py:194` and `:663`), so the cookie
has to follow the setting.

**2. The attack-resistance numbers stay fixed in code, as a stated exception to
"numbers belong to the company".** These are the sign-in code lifetime, the
guess attempts per code, and the code-request limits per address and per client.
They protect the system rather than express a company preference, and a wrong
value opens a hole. The 2026-09-29 addendum above already depends on them: its
timing claim is "sampled at most five times per address per quarter hour". That
claim is stated in these exact numbers, and a setting that raised them would
weaken it without any response changing. A company that must change them does
so in its fork, knowingly.

Making them settings bounded like the session lengths was considered and not
adopted. A bound still lets a company choose the weakest value inside it, and
for these numbers the weakest permitted value is then the system's real
security level. Because they express no company preference, there is nothing
for such a setting to serve that would outweigh that.

**3. Decided now, built later.** Until the build lands, the session lengths
remain the constants above. The build is tracked as task-342. Its final-design
pass decides the safe ranges. It also decides whether a changed length applies
to sessions that already exist, and the two expiries differ here: the absolute
lifetime is stamped into each session row when it is created
(`backend/app/auth/service.py:892`), while the idle timeout is evaluated against
the constant on every request (`:930`). The pass also covers auditing the change
like other settings (`backend/app/settings/audited.py`).

**What it costs.**

- **Two more settings.** Each has a range to choose, defend and test, and each
  changes the length of every session in the company at once.
- **A company that needs different attack-resistance values must change code.**
  The exception is now written down rather than implicit, but it is still an
  exception, and such a company carries the change in its own fork.

**What it buys.** The numbers a company legitimately owns become its own. The
one place the repository departs from "numbers belong to the company" is
recorded, with its reason, instead of being discovered by reading module
constants.

## Addendum 2026-10-11 — the session lengths' final-design pass

Prompted by the final-design pass of task-342, decided by the user on 2026-10-11
one question at a time. It closes the list the 2026-10-09 addendum above left to
that pass in its points 1 and 3. Point 3 of the Decision and the 2026-10-09
addendum stand as written. This addendum records the ranges and when a changed
length takes effect.

**1. The safe ranges.** The absolute session lifetime is 1 to 72 hours, default
12. The idle timeout is 5 to 480 minutes, default 60, and never longer than the
absolute lifetime. Five minutes stays well above the 60-second activity refresh
(`TOUCH_INTERVAL` in `backend/app/auth/service.py`), so a short idle timeout
still works. Seventy-two hours covers a long working weekend without letting a
stolen session live for weeks. A value outside the range is refused when it is
set, not silently clamped. A stored value is still clamped to the range when it is
read, so one written by hand cannot step outside it.

**2. Shortening applies at once; a longer lifetime applies only to new
sessions.** Making either length shorter applies at once to everyone signed in:
a session past the new limit ends on its next request. Tightening is usually
why a company changes a length. Making the lifetime longer applies only to
sessions started afterwards, so nobody's existing session is silently extended.
A longer idle timeout applies at once. It can only keep people signed in longer
between clicks, never past their lifetime.

Technically, each session ends at the earlier of two times: the expiry stamped
when it started, and its start time plus the current lifetime. Idle is checked
against the current timeout on every request. The session cookie's lifetime
follows the setting at sign-in.

**3. Unchanged from the 2026-10-09 addendum.** The attack-resistance numbers
(the sign-in code lifetime, the guesses per code and the code-request rate
limits) stay code constants. A change to a session length is audited like other
settings. It is a person's change, under `settings.manage`.

**What it costs.**

- **Every request reads the two settings.** That is one small query per request.
- **Lengthening reaches only new sessions.** A longer lifetime shows fully only
  once the old lifetime has passed since the change.

**What it buys.** The lengths a works council or auditor requires can be set
without a code change, and tightening them takes effect at once.

## Related ADRs

### Depends On
- [[ADR-150 — Tenancy and Access Model]]

### Enables
- [[ADR-153 — Audit and Accountability]]
