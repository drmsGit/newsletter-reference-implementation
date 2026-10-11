---
type: adr
status: accepted
topic:
  - architecture
  - consent
  - delivery
  - deliverability
  - compliance
  - brand
created: 2026-10-11
modified: 2026-10-11
source:
  - "task-355 final-design pass, decided by the user 2026-10-11, one question at a time, including two follow-up questions the draft of this record raised the same day"
depends_on:
  - "[[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]]"
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
  - "[[ADR-122 — Minimal Consent Model Required]]"
  - "[[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]"
  - "[[ADR-176 — A Negative Decision Outranks a Positive One]]"
  - "[[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]]"
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-153 — Audit and Accountability]]"
---

## Status
Accepted

## Context

**Until now the platform sends only marketing.** Verified 2026-10-11:

- **Every planned send records purpose `marketing`.** "Every planned send today is a marketing send (task-42)" (`backend/app/delivery/service.py:640`). The purpose vocabulary has one entry, `MARKETING`, and it is never a default (`backend/app/recipients/consent.py:34-40`).
- **The send-time exclusion stack asks for a marketing opt-in.** Its consent stage requires the latest event for `(recipient, brand, channel, purpose)` to be a grant (`backend/app/delivery/exclusion.py:189-217`). This is stage 2 of [[ADR-163 — Per-Channel Consent and Addressability]] point 7.
- **Audience resolution applies the same floor.** `resolve_audience` gates on `is_consenting_filter(brand_id, channel, purpose=MARKETING)` (`backend/app/audience/service.py:1280`). Rule blocks are gated the same way in `find_by_criteria` (`:693`), and audience assembly runs the stack with `MARKETING` (`:1068`).

**ADR-194 made a non-marketing email possible.** [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] point 9 lets a brand profile be marked transactional, so an email may go out without an opt-in check. Its design session settled the guard: a separate permission to create or mark one, audited; choosing one on a variant labelled and audited; a duplicate stays transactional only for a holder of the right. ADR-194 decided **where** the choice sits. It left **how a transactional send meets the exclusion stack** open, for this pass (ADR-194, "Open for the final-design passes", and its first addendum). Queue task-355 builds it.

**Two open needs-ADR items cover the wider ground.**

- **Queue task-134** asks (a) what the transactional consent basis is, (b) whether marketing, transactional and system mail need separate sending reputation, and (c) whether transactional mail reuses the email modules. It already leans one way on (a): "a dead address is dead either way", while "a *marketing* opt-out must not block a password reset". So "the suppression gate and the consent gate are not the same gate".
- **Queue task-135** asks for a suppression and opt-out reason model: one place that records why a person is not getting mail.

**There is no suppression store today.** Stage 3 of the stack is named and empty (`backend/app/delivery/exclusion.py:219-233`). A hard bounce or spam complaint is written as a consent opt-out event with `source="provider"`. It is keyed to the execution's brand, channel and purpose (`suppress_recipient`, `backend/app/recipients/service.py:39-83`, called from the webhook at `backend/app/providers/service.py:210-241`). [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]] is why that path exists. For marketing it works, because the opt-in check catches the event. That leaves three holes once a second purpose exists:

- **A send that skips the opt-in check would also skip the bounce.** Mailing a dead address, or someone who reported spam, is the reputation damage ADR-106 exists to prevent.
- **A bounce on a transactional mail lands on the transactional cell.** A marketing send reads only the marketing cell, so it would keep mailing that dead address.
- **A provider event is not always written.** `suppress_recipient` returns early when the cell is already opted out (`backend/app/recipients/service.py:67-71`). So a complaint that arrives after the person unsubscribed from marketing leaves no provider-sourced event behind.

The user decided the points below on 2026-10-11, in task-355's final-design pass, one question at a time. Point 2's reach to every send, and its rule for `suppress_recipient`, were decided the same day, after a first draft of this record raised the second and third holes.

## Decision

**1. Decide only what transactional profiles need now.**

- **A send whose snapshot's brand profile is transactional records purpose `transactional`** on every delivery execution.
- **It skips the marketing opt-in check,** both when its audience is resolved and at send time.

**2. Provider suppression applies to every send.**

- **Anyone the provider suppressed for that brand and channel is excluded from every send,** marketing and transactional. That is a hard bounce or a spam complaint, recorded as a provider-sourced opt-out event, on **any** purpose.
- **The reason is recorded under the stack's suppression stage** (stage 3).
- **The audience floor applies the same rule.**
- **Unaddressable recipients are excluded, as for every send** (stage 1).
- **No new suppression table.** The provider-sourced events already recorded are read as suppression.
- **This is the first rule in stage 3** of [[ADR-163 — Per-Channel Consent and Addressability]] point 7.
- **`suppress_recipient` always leaves the provider's event behind.** It records the provider's opt-out event even when the cell is already opted out, for example after a marketing unsubscribe. It skips the write only when the latest provider-sourced event for that same brand, channel and purpose is already an opt-out. Otherwise a complaint after an unsubscribe would leave nothing for this rule to read.

The reason for every send: a dead address is dead either way, and a complaint about any mail from a brand is a reason not to send that person its newsletters.

This follows [[ADR-176 — A Negative Decision Outranks a Positive One]] point 2. The transactional mark, or a marketing grant, admits a person. A provider suppression refuses them. The refusal wins.

**3. No unsubscribe line and no one-click header on a transactional email,** in this slice.

- **This holds even when the profile has unsubscribe wording.**
- **The legal details are still on every email** (ADR-194 point 8).
- **What an unsubscribe on transactional mail would mean stays open.** For example, a block list that also stops transactional mail.

**4. A transactional profile is never a brand's default.**

- **Making one the default is refused.**
- **Marking the default transactional is refused.**
- So a variant becomes transactional only when someone picks such a profile.

**5. The guard ADR-194's session settled is built with it.**

- **The permission `brand_profiles.transactional`** is needed to create a transactional profile or mark one transactional. It is brand-scoped. The Admin preset holds it. A Manager does not, unless the company grants it. Every use is audited ([[ADR-153 — Audit and Accountability]]).
- **A variant using a transactional profile is labelled "sent without opt-in check".** Choosing one is audited.
- **Duplicating a transactional profile keeps it transactional only for a holder of the permission.** For anyone else the copy is marketing.
- **An approver of such a send is told that it skips the opt-in check.**

### What stays open

- **task-134 (b):** separate sending reputation for marketing, transactional and system mail.
- **task-134 (c):** whether transactional payloads reuse the email modules.
- **task-135's full suppression model:** a store of its own, reasons, manual blocklists, and whether a later re-subscribe lifts a provider suppression.
- **What an unsubscribe on a transactional email writes** (point 3).

## Consequences

### Positive

- **Transactional mail is possible without bypassing bounces and complaints.** A dead address stays dead, whatever the purpose of the mail that found it and whatever the purpose of the next send.
- **The purpose is recorded on every execution.** So a bounce or complaint lands on the purpose the mail was really sent under, through the existing webhook path.
- **A complaint is never lost behind an unsubscribe.** The provider's event is written even when the cell was already opted out.
- **The guard is a permission plus labels plus audit.** Creating a transactional profile needs the right. Using one is visible on the variant and to the approver, and is audited.
- **Stage 3 gets its first rule without a second mechanism.** It reads facts already recorded, so nothing new can disagree with them.

### Negative

- **A provider suppression on any purpose blocks transactional mail for that brand and channel.** That includes a spam complaint about a marketing mail: a receipt to that person then does not arrive. There is no way yet to lift it in the platform.
- **Marketing sends exclude a little more than before, never less.** For example, a bounce on a receipt now also stops newsletters to that address.
- **Marketing and transactional still share one provider and one sender reputation** until task-134 (b) is decided. Complaints on marketing still affect the delivery of transactional mail.
- **Anyone who can edit a variant can pick an existing transactional profile.** The permission guards creating and marking profiles, not choosing them. Choosing is guarded by the label and the audit.

## Notes

- **The interim reading of provider events as suppression should be replaced, not extended, when task-135 is decided.** It is a stand-in for a suppression store, chosen so this slice invents no table that task-135 would then have to fit around. The stage-3 comment in `backend/app/delivery/exclusion.py:219-233` gave the same reason for leaving the stage empty.
- **This is not a supersession, and no record's Decision is edited.** ADR-194 point 9 and its open list left this question to this pass. Three readings narrow:
  - ADR-194 point 1 lets any profile be made the default. Point 4 above excludes transactional profiles.
  - ADR-194 point 10 lets a transactional profile carry unsubscribe wording ("Some companies do show one on transactional mail"). Point 3 above shows no line on transactional mail in this slice, even with wording.
  - [[ADR-163 — Per-Channel Consent and Addressability]] point 7 names stage 3 as "hard bounce, complaint, manual blocklist". Point 2 above gives it its first rule, for every send.
- **Not in conflict with ADR-191 point 4.** [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] point 4 says an unsubscribe never affects transactional messages. Point 2 above reads only provider-sourced events. An unsubscribe writes `source="unsubscribe"`, so it still never blocks transactional mail.
- **Not an exclude block.** [[ADR-176 — A Negative Decision Outranks a Positive One]]'s Notes say the record that settles the suppression model must not reach for `kind="exclude"`. Point 2 does not. It reads consent events, not audience rule blocks.
- **The consent basis.** [[ADR-122 — Minimal Consent Model Required]] requires the marketing-versus-transactional distinction. This record is the first send that uses the transactional side. A transactional send asks for no grant of its own: its floor is addressability plus provider suppression (task-355's D1).
- **On a marketing send, a provider event on the marketing cell is also a missing grant.** Stage 2 runs before stage 3 today, so the stack would record such a person under consent, not suppression. Point 2 asks for the suppression reason. How the build meets that, for example by the order of the stages, is a question for task-355's implementation. [[ADR-163 — Per-Channel Consent and Addressability]] point 9 says the order never changes who is excluded; it does change which reason is recorded.
- **No decision-log entry.** `docs/playbook-strategy.md` §5 has the 2026-10-11 entry for ADR-194, whose point 5 says a transactional profile "skips the opt-in check". It has no entry for this pass. The reasoning here comes from task-355's implementation plan, task-134's description and the user's answers of 2026-10-11.

## Related ADRs

### Depends On
- [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] — the transactional mark (point 9) and the guard this record builds.
- [[ADR-163 — Per-Channel Consent and Addressability]] — the exclusion stack, its consent and suppression stages, and the purpose on every execution (addendum 2026-09-12, point 1).
- [[ADR-122 — Minimal Consent Model Required]] — marketing versus transactional as the base consent distinction.
- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]] — why provider feedback must exclude people from every send.
- [[ADR-176 — A Negative Decision Outranks a Positive One]] — the suppression refuses, the transactional mark or a grant admits, and the refusal wins.
- [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] — the unsubscribe line and one-click header that a transactional email does not carry.
- [[ADR-150 — Tenancy and Access Model]] — permissions as rows, brand-scoped.
- [[ADR-153 — Audit and Accountability]] — the audit of every transactional mark and choice.
