---
type: adr
status: accepted
topic:
  - architecture
  - delivery
  - governance
  - operations
created: 2026-10-09
modified: 2026-10-09
source:
  - "Decided by the user in chat, 2026-10-09, under task-325 (option 3 of three)"
depends_on:
  - "[[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]"
  - "[[ADR-142 — Autonomous Workflows and the Automation Boundary]]"
  - "[[ADR-153 — Audit and Accountability]]"
  - "[[ADR-150 — Tenancy and Access Model]]"
---

## Status
Accepted

## Context

**A send whose process dies mid-send is stuck for good.** `send_send_instance` in `backend/app/delivery/service.py` sets the send to `sending` and commits before it delivers anything. If an exception is raised, the send is marked `failed`, and `failed` can be retried. If the process dies, nothing runs that handler, and the send stays `sending`.

**The double-send guard then refuses every way back.** The guard is a row lock plus a status check, and it refuses a send that is already `sending` or `sent`. That is what stops one send going out twice. But it also refuses every retry of a stranded send: from a person, from the scheduler, and from the held-send approval (`backend/app/approvals/actions/send_fire.py`). The only way out was editing the database.

**Since task-318 (2026-10-09), a retry treats each recipient correctly.**

- An execution that is `sent` stays sent.
- An execution left `sending` means the provider was called and the outcome is unknown. It becomes `uncertain` and is never resent. That was the user's decision: never risk a duplicate, and resend by hand.
- An execution that is `created` was never attempted, so it is sent.

So a stranded send does not need new retry rules. It only needs to be let back in.

**Three options were offered under task-325.**

1. Automatic release after a timeout.
2. A release action with no detection.
3. Detection plus a release by a person.

The user chose option 3. Option 1 was rejected because no timeout can tell a slow live send from a dead one with certainty, and a wrong automatic release could deliver one send twice at the same time. Option 2 is safe, but it was rejected because someone has to notice the stuck send first, and nothing would tell them.

## Decision

**1. The platform flags a stranded send. A person releases it.**
The platform never releases a send on its own, for the reason option 1 was rejected: no timeout tells a slow live send from a dead one with certainty.

**2. What "stranded" means.**
A send is stranded when its status is `sending` and there has been no activity on it for 30 minutes.

- **Activity** is the latest `updated_at` of the send instance or of any of its delivery executions.
- **This is a reliable signal since task-318.** Every execution is written immediately before its provider call. So a living send shows activity for each recipient, and a dead one goes quiet.
- **The 30 minutes is a code constant for now.** Making it a setting can be added later, if a deployment needs it.

**3. The flag is part of the send's read model.**
The send carries `stranded` and the time of its last activity. Both appear on the deliveries list and on the send detail. So monitoring shows a stuck send without anyone having to look for it.

**4. Release is an explicit action: `POST /delivery/send-instances/{id}/release`.**

- **People only.** A machine cannot release a send. The route is guarded by `require_person`.
- **It needs `sends.plan` in the send's brand.** In this platform `sends.execute` means exactly "this route can put mail in front of a person", and `backend/tests/test_api_guard.py` checks that in both directions. Release mails nobody: it only moves the send to `failed`, and the retry that could mail someone still needs `sends.execute` on the send route. So release falls under the existing `("/delivery/", SENDS_PLAN)` entry in `backend/app/auth/policy.py`.
- **It is refused with 409 unless the send is stranded at that moment.**
- **It moves the send to `failed`.** A normal retry then follows task-318's rules.
- **It is audited** as `send.released`. The entry records how many executions were `sent`, `sending` and `created` at the moment of release.

## Consequences

### Positive

- **No more database edits** to recover a stuck send.
- **No automatic double delivery.** Nothing releases a send unless a person acts.
- **A stuck send is visible where people already look:** the deliveries list and the send detail.
- **The retry rules are reused, not duplicated.** Release only lets the send back in, and task-318's per-recipient rules do the rest.
- **Release adds nothing to the list of routes that can mail a person.** The `sends.execute` control stays exactly as narrow as it was.

### Negative

- **A person must act.** A stranded send waits until someone does.
- **The 30-minute threshold is a guess.** If a provider stalls on one recipient for more than 30 minutes, a send that is still alive is flagged. The release check only asks whether the threshold has passed, so it would allow a release. The person releasing a send has to judge whether it is really dead. A live send that is released and then retried could run alongside its original process.
- **A released send's in-flight recipient stays `uncertain`.** That person needs the manual resend path.
- **The threshold cannot be configured yet.**

## Notes

- **Not a supersession, and no ADR's status changes.** The first 2026-09-29 addendum of [[ADR-142 — Autonomous Workflows and the Automation Boundary]] (point 6) compares a crashed held request left `executing` to "a send left in `sending`", and says resolving it is "a person's investigation, not a button". That point is about the held request's row, and this record does not change it. For a send, release is still a person's decision, taken after the flag has said what the send holds.
- **Not decided here: the held request of a send that died during approval.** If the process dies while `send_fire` runs, the send is stranded and its held request stays `executing`. Releasing the send does not touch that request. ADR-142's one-open-request index covers `executing`, so a new held request for the same send would be refused until the old row is resolved. A person can still retry the send directly.
- **The same 30 minutes as the composer fence.** [[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]], addendum 2026-10-04, lets a fence lapse after 30 minutes without edits. The two thresholds were chosen separately and do not depend on each other. ADR-180 is also the precedent for an action that a person may take and a machine may not.
- **Related queue items.** task-124 part (c), a queue with a log, would give a send a better liveness signal than `updated_at`. task-81, provider-side reconciliation, could later turn an `uncertain` execution into sent or not-sent by asking the provider. That would shrink what a person has to resend by hand after a release.
- **No decision-log entry.** `docs/playbook-strategy.md` has no entry for this decision. The reasoning above comes from task-325 and the 2026-10-09 conversation.

## Addendum 2026-10-09 — release also fails the send's stuck held request

Prompted by task-326 and decided the same day by the user, recorded in the 2026-10-09 addendum to [[ADR-142 — Autonomous Workflows and the Automation Boundary]]. This settles the Notes' *"Not decided here"* item above. Releasing a stranded send now also moves every held request for `send.fire_send_instance` on that send that is still `executing` to `failed`, in the same transaction as the release, so the send and its request change together or not at all. Each such request's `execution_error` says it was released with its stranded send, each is audited `approval.failed` by the person who released, and the `send.released` entry lists their ids. A new held request for the send is therefore no longer refused after a release. Point 4 is unchanged: release is still a person's act, refused unless the send is stranded at that moment. Held requests for other actions, for other sends, or still `pending` are not touched.

## Related ADRs

### Depends On
- [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] — the delivery executions whose state a release counts and a retry reads.
- [[ADR-142 — Autonomous Workflows and the Automation Boundary]] — who may act, and the held-send approval path.
- [[ADR-153 — Audit and Accountability]] — `send.released` joins the audit vocabulary.
- [[ADR-150 — Tenancy and Access Model]] — the brand-scoped `sends.plan` and `sends.execute` permissions.

### Referenced By
- [[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]] — the precedent for an action a person may take and a machine may not.
