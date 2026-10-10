---
type: adr
status: accepted
topic:
  - architecture
  - consent
  - compliance
  - deliverability
  - delivery
created: 2026-10-09
modified: 2026-10-10
source:
  - "Decided by the user in chat, 2026-10-09, one question at a time (task-56)"
depends_on:
  - "[[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]]"
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
  - "[[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]"
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
  - "[[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]"
---

## Status
Accepted

## Context

**There is no unsubscribe anywhere.** There is no public route, no landing page and no `List-Unsubscribe` header. The Resend payload is `from`, `to`, `subject` and `html`, nothing else (`backend/app/delivery/providers/resend.py`). The only code that writes an opt-out is the provider webhook for bounces and complaints (`backend/app/providers/service.py`). A recipient who wants to stop has no way to say so except to mark the mail as spam.

**One-click unsubscribe is a hard requirement for bulk senders.** Gmail and Yahoo require RFC 8058: a `List-Unsubscribe` header with an HTTPS URL, and a `List-Unsubscribe-Post: List-Unsubscribe=One-Click` header so the mail client can unsubscribe with one POST. Without it, mail is filtered. This is the deliverability failure [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]] exists to prevent, arriving by another door. A recipient with no visible way out complains instead, and a complaint costs reputation.

**The brief for the external code review of 2026-10-09** (`CODE-REVIEW-BRIEF.md`) lists the missing unsubscribe among the known open gaps, so the reviewer was told not to re-find it. Its report (`docs/queue/docs/doc-1`) therefore does not raise it.

**Two parts of the answer were decided earlier and are cited here, not decided again.**

- [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]] point 1: unsubscribe and double opt-in are routes, not flows. Each is a link, a page and a consent write. No flow machinery is needed.
- [[ADR-163 — Per-Channel Consent and Addressability]], addendum 2026-09-15, point 2: an opt-out defaults to the brand that sent the mail. The page may also offer stopping everything from the company, and whether that option appears is a company setting.

What was left open was the link itself, what opening it does, what exactly is opted out, where the visible link goes before the designed footer exists, and the wording. The user decided these in chat on 2026-10-09, one question at a time, under task-56.

## Decision

**1. Unsubscribe is built first. Double opt-in is split off into its own queue task.**
Double opt-in starts with a question this record does not answer: where a signup comes from. It could be a website form, the API or the CRM. The platform has no signup entry point today. And [[ADR-120 — CRM as Customer Source of Truth]] makes the CRM the owner of who agreed. Unsubscribe has no such question, so it does not wait for one.

**2. Each delivered message carries a random token.**
Each sent message gets an unguessable random token. It is stored on that message's delivery execution row, in one new indexed column. The execution row already knows the person, the brand (through the send instance), the channel and the purpose. So the token needs to carry nothing, and the route looks everything up from the row.

- **There is no secret to configure.** No missing or rotated key can break links that were already sent. An unsubscribe must never fail, and a link in a mail sent last year must still work.
- **Tokens never expire.**

A stateless token signed with an environment secret was considered and rejected. It needs no migration. But a missing or rotated secret would break every link already sent, silently, in mail that can no longer be changed.

**3. Opening the link shows a page. Only a POST opts out.**

- **The visible link opens a short page:** "Unsubscribe from <brand> emails", with one confirm button. Opening the page writes nothing. Only the button's POST writes.
- **The RFC 8058 one-click POST opts out immediately.** A mail client that sends `List-Unsubscribe=One-Click` to the header URL gets no page. It applies the default scope of point 4, because there is no page on which to choose.

Unsubscribing on GET was rejected. Corporate link scanners and mail previews open every link in a message. They would silently unsubscribe people who never clicked. This is the same reason the decision log already gives for never putting one-click approve links in email (`docs/playbook-strategy.md`, 2026-07-31, AI Layer Design Part 2, point 2).

**4. What is opted out.**

- **The default:** marketing, on the channel the message came on, from the brand that sent it. This is ADR-163's 2026-09-15 addendum, point 2.
- **A second option, when the company setting allows it:** "everything from the company". It opts out of marketing from every brand, on every channel.
- **Transactional messages are never affected.** Sign-in codes and system mail still arrive.
- **The setting starts off.** A one-brand deployment never shows a second option that would confuse its readers.

Two other shapes were rejected. The setting on by default was rejected for the reason ADR-163's addendum already gives: in a one-brand deployment the choice implies sibling brands the reader has never heard of. "All brands, email only" was rejected as a third option.

**5. A minimal footer line now, until the designed footer replaces it.**

- **Every marketing email carries `List-Unsubscribe` and `List-Unsubscribe-Post` headers.**
- **The email renderer appends one plain footer line with the visible link,** for example: "You receive this from <brand>. Unsubscribe."
- **The designed visible footer of task-301 replaces that line, and it must keep the link.**

Headers only, until task-301, was rejected. Some mail clients hide the header's unsubscribe button. A reader using one of them would have no visible way out.

**6. Unsubscribe is a launch gate.**
"Every marketing mail can be unsubscribed from — one-click header, a visible link and a working page" is [[LAUNCH-GATES|launch gate 10]] in `docs/business/LAUNCH-GATES.md`. It closes when task-56 ships.

**7. English now, with all wording in one place.**
All recipient-facing wording lives in one small module, in English: the footer line, the page and the confirmation. Translation is then a later addition, not a search through the code. Recipients already carry a `language` field, but nothing translates recipient-facing text yet.

**The opt-out is a consent event, and nothing else is new.**
The route writes through the existing consent writer (`record_consent` in `backend/app/recipients/consent.py`), with source `unsubscribe`. The send-time exclusion stack of ADR-163 point 7 already honours an opt-out event. So no new exclusion mechanism is needed.

**Relaying the opt-out to the CRM is not part of this record.** It belongs to suppression and opt-out reasons (task-135). Until then, the consent-drift report already shows such an opt-out as platform-ahead (ADR-163, addendum 2026-09-12, point 4).

## Consequences

### Positive

- **The compliance gap closes.** Every marketing mail can be unsubscribed from, and Gmail's and Yahoo's one-click requirement is met.
- **Scanners cannot unsubscribe people.** Opening a link never writes.
- **Links never break.** Nothing is signed, nothing expires, and no key rotation can invalidate mail already sent.
- **No new secret.** There is nothing to add to the environment and nothing to rotate under [[ADR-152 — Secret and Credential Handling]].
- **No new exclusion path.** The opt-out is an ordinary consent event, so the gate that already exists honours it.

### Negative

- **A migration, and a public route with no authentication.** This is new attack surface. The token is the only credential, so it must be unguessable: 256 random bits, as Notes records.
- **Links need a public base URL.** It must be configured. In development it is the API's own address.
- **The interim footer line is plain.** It is a stopgap and will be replaced by task-301.
- **Recipients who do not read English get an English page.** Nothing translates recipient-facing text yet.
- **A test send has no real unsubscribe link.** It creates no delivery execution row, so there is no token to put in it.

## Notes

- **ADR-169 says "a signed link". This record uses a stored random token.** ADR-169 point 1 is about routes versus flows. "Signed" there described a link, it did not choose a token design. ADR-169's point holds unchanged: the unsubscribe is still a link, a page and a consent write. So this is not a supersession, and ADR-169's Decision is not edited.
- **This refines task-56's scope note.** That note recorded the user's 2026-09-18 scope as "global opt-out plus per-channel". Point 4 is the decided form: per-brand and per-channel by default, with a company-wide option that a company switches on.
- **Settled by the final-design pass and built on 2026-10-09, under task-56.**
  - **When the token is minted: at send time, in the send loop.** It is minted the first time a message is rendered for sending: `footer_for` in `backend/app/subscriptions/service.py`, called from `_deliver_claimed` in `backend/app/delivery/service.py`. A message that is never sent has no token. Tokens are `secrets.token_urlsafe(32)`. They are stored in `delivery_executions.unsubscribe_token`, which migration 0041 adds as unique and indexed.
  - **How the headers reach the provider: through the email artifact's envelope, as `list_unsubscribe`.** The envelope is the artifact's delivery metadata. [[ADR-161 — Channel Execution Shapes]] point 1 keeps one addressed interface, which is why the subject rides in the envelope too. The Resend adapter turns `list_unsubscribe` into `List-Unsubscribe: <url>` and `List-Unsubscribe-Post: List-Unsubscribe=One-Click`. The provider interface is unchanged.
  - **Rate limit: none.** The token carries 256 random bits, so guessing one is not a practical attack, and the route does nothing costly. The route reads no session and acts as no principal. `backend/app/auth/policy.py` classes it under a new sentinel, `RECIPIENT_TOKEN`, and a test asserts that exactly the unsubscribe POST carries it. The route is mounted outside both signed-in planes and is kept out of the API schema.
  - **The base URL setting is the environment variable `PUBLIC_BASE_URL`.** It falls back to `http://localhost:8000`, and is documented in `backend/.env.example`.
- **A reconstruction renders the same footer.** The footer's inputs, the link and the brand name, are recorded in the delivery record. So a reconstruction under [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] renders the same footer, even after the brand is renamed. A message without a footer renders byte for byte as before, so every earlier delivery record still matches its hash.
- **One-click never means "everything".** It applies point 4's default scope even when the company setting offers the second option.
- **The company setting is `PUT /settings/unsubscribe`** (`offer_everything`). It is audited like every settings write.
- **Not decided here: whether an unsubscribe also writes a negative signal.** [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] lists unsubscribe as a strong negative signal. This record only decides the consent write.
- **No decision-log entry.** `docs/playbook-strategy.md` has no entry for this decision. The reasoning above is from the 2026-10-09 conversation, and from ADR-163 and ADR-169.

## Addendum 2026-10-09 — "links never break" means the token; the address and the records are the adopter's

Prompted by business per-feature finding BF-SUB1 in `docs/business-interview.md` ("Does the promise of durable links include durable infrastructure?"), decided by the user in the 2026-10-09 interview review. The playbook decision log records the same position under "Unsubscribe links over time (BF-SUB1)" in `docs/playbook-strategy.md` §5. A related decision of the same day came from the technical interview, [[Interview Prep - Since 2026-09-18]], Audience Q6, and is queued as task-330. Decision point 2 above is left as written. This addendum governs how its promise that "a link in a mail sent last year must still work", and the Positive consequence "Links never break", are to be read.

**What was found.** Point 2 and the Positive consequence promise that links never break: nothing is signed, nothing expires, and no key rotation can invalidate mail already sent. That holds for the token. But a working link needs two more things, and the token carries neither.

- **The address.** The link is built at send time from `PUBLIC_BASE_URL` (`backend/app/subscriptions/service.py:25-26` and `:33-34`, returned by `footer_for` at `:49`). It is recorded in the delivery record (`backend/app/delivery/service.py:1306-1307`) and fixed into the mail, which can no longer be changed. If the address stops reaching this installation, every link in every mail already sent stops with it.
- **The records.** Resolving a token joins the delivery execution, its send instance and the sending brand (`backend/app/subscriptions/service.py:52-63`). If any of those rows is gone, both the page and the POST answer 404 (`backend/app/subscriptions/router.py:27-28` and `:47-48`). Neither [[ADR-154 — Erasure and Retention]] nor the retention design item, task-136, mentioned unsubscribe links.

The question was whether "never break" also promised those two.

**What this records.**

1. **"Links never break" covers the token's lifetime.** A token never expires and needs no key. That is what point 2 decided, and it is what the product guarantees. It is not a promise that the address stays reachable or that the rows behind the token survive.
2. **The address is the adopter's to keep reachable.** The public address the link points to should be a domain the company owns, not an agency's host. Keeping it reachable is the adopter's job, and it is part of the reference deployment (task-55). The product already carries its own share of this: a real marketing send refuses a `PUBLIC_BASE_URL` that is unset or not https (task-330), so the localhost fallback in Notes above cannot end up in a real recipient's mail.
3. **Retention must keep the lookup working for a minimum period.** Any retention clean-up of delivery records must keep the unsubscribe lookup working for a minimum period. That constraint belongs to the retention design (task-136). The period is not decided here.

**Nothing is built by this addendum.** Points 2 and 3 are recorded as notes on task-55 and task-136. The one code change in this area is task-330, which was decided separately.

**The option not taken: the product guarantees all three.** The product could have promised the address and the records as well, for example with a fixed domain and a lookup table that is never pruned. That would contradict two settled positions. An install runs on the company's own infrastructure and is not a hosted service (`docs/business/BRIEF.md`, "Not a hosted service"), so the product has no address of its own to guarantee. And how long delivery history is kept is the company's determination ([[ADR-154 — Erasure and Retention]], Notes), which a table that is never pruned would take away.

**Consequences.**

- *Positive:* the promise says exactly what the product guarantees, and who carries the rest.
- *Negative:* an adopter who moves hosts or prunes records carelessly can still break links in mail already sent, and only documentation stands between them and that. A broken link answers 404, so its reader is back to having no visible way out, which is the complaint risk this record exists to remove.

**Not decided.** What an erasure does to a link. [[ADR-154 — Erasure and Retention]] point 2 removes a person's delivery executions by default, so that person's old links stop resolving after an erasure. Point 3 above speaks only of retention clean-up. Whether erasure needs the same care is not decided here.

## Addendum 2026-10-10 — the footer line is permanent, not a stopgap

Prompted by the task-301 design session. The user decided on 2026-10-10, and [[ADR-193 — An Email's Legal Footer Is Fixed, Its Visible Header and Footer Are Placed Modules]] records it. Decision point 5 above and its Negative entry are left as written. This addendum governs how they are to be read.

**What changed.** Point 5 called the footer line "a minimal footer line now, until the designed footer replaces it". It said the designed visible footer of task-301 would replace the line. The Negative list called the line "a stopgap". ADR-193 point 1 goes another way:

- **The fixed line stays, permanently.** The frame keeps appending it to every marketing email.
- **It is extended with the brand's legal details,** taken from a brand profile (ADR-193 point 2).
- **The designed visible header and footer are placed modules on top of it.** A manager may place them or leave them out. They do not replace the line.

**Why this is a refinement, not a supersession.** The guarantee in point 5 holds: every marketing email carries a visible unsubscribe link, and no manager can remove it. That guarantee is now permanent instead of interim. No designed footer can lose the link, because the link no longer depends on one. Only the expectation of how task-301 would deliver the link is not carried out. ADR-193's Notes reach the same conclusion. ADR-191's own Notes treated a wording difference with ADR-169 the same way.

**One wording fix follows.** The docstring of `footer_html` (`backend/app/subscriptions/texts.py:13-14`) says the line lasts "until task-301's designed footer replaces it". It will be wrong once ADR-193 is built. Correcting it belongs to queue task-350, the brand profile build.

**Nothing is built by this addendum.**

## Related ADRs

### Depends On
- [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]]
- [[ADR-163 — Per-Channel Consent and Addressability]]
- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]

### Referenced By
- [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]
- [[ADR-152 — Secret and Credential Handling]]
- [[ADR-161 — Channel Execution Shapes]] — the envelope carries the List-Unsubscribe URL as delivery metadata.
- [[ADR-193 — An Email's Legal Footer Is Fixed, Its Visible Header and Footer Are Placed Modules]] — makes point 5's footer line permanent and extends it with the brand's legal details.
