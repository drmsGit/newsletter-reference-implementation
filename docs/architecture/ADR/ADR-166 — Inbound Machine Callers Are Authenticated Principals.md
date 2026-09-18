---
type: adr
status: accepted
topic:
  - architecture
  - security
  - access
  - automation
  - governance
created: 2026-09-13
modified: 2026-09-18
source:
  - "Machine authentication design interview (2026-09-13)"
depends_on:
  - "[[ADR-002 — API First Architecture]]"
  - "[[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]"
  - "[[ADR-140 — AI Capability Layer]]"
  - "[[ADR-142 — Autonomous Workflows and the Automation Boundary]]"
  - "[[ADR-143 — AI-Assisted Development Boundary]]"
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-151 — Authentication and Sessions]]"
  - "[[ADR-152 — Secret and Credential Handling]]"
  - "[[ADR-153 — Audit and Accountability]]"
  - "[[ADR-154 — Erasure and Retention]]"
enables:
  - "[[ADR-164 — Channel Feedback and Signals]]"
---

## Status
Accepted

## Context

The JSON API is an unauthenticated control plane. `main.py` applies `enforce_csrf` and `enforce_policy` over the UI router and includes the twelve JSON routers below it with no guard at all: **69 routes, 36 of them state-changing**. Among them `POST /delivery/send-instances/{id}/send`, which fires real mail; `POST /recipients/{external_id}/consent`, which writes the compliance record the defence against a UWG §7 complaint rests on; `GET /recipients/`, which returns the recipient list; and `POST /insight/events`, which writes engagement straight into the signal layer. Anyone who can reach the port can do all of it.

That was a defensible local-development posture and is not one for a reachable host. The sharper point is that the halves are now mismatched: with gate 4 closed, **the UI is locked while the API beneath it is open**, which is worse than either state alone, because it looks protected. This is launch gate 3, raised to P0 because it blocks public exposure and not merely Mode B.

Three records have been deferring to this one. [[ADR-151 — Authentication and Sessions]] closes by scoping itself to human authentication and parking machine callers as a separate concern. [[ADR-152 — Secret and Credential Handling]] closes by distinguishing credentials the platform *holds* from credentials it *issues*, and covering only the former. [[ADR-153 — Audit and Accountability]] §3 already models the actor as "*some* authenticated principal from the start" precisely so this could arrive without revisiting every write path. [[ADR-142 — Autonomous Workflows and the Automation Boundary]] cannot deliver Mode B without it, and [[ADR-164 — Channel Feedback and Signals]] §7 plans the conversion callback on the assumption that it lands.

**Four of those five foundations have since been accepted.** When this was drafted on 2026-09-13, [[ADR-150 — Tenancy and Access Model]] through [[ADR-154 — Erasure and Retention]] had all sat at proposed since 2026-08-02, and the acknowledged cost was building on proposals rather than leaving the API open while the cluster was ratified. By acceptance on 2026-09-18 only [[ADR-152 — Secret and Credential Handling]] remains `Proposed`. The exposure is therefore one record wide instead of five — and it is the record this one leans on least, because ADR-152 scopes itself to credentials the platform *holds* while point 3 below governs credentials it *issues*, a line ADR-152 drew itself.

The shape of the answer was contested on one axis. A **parallel authorization system for machines** — its own credential model, its own scopes, its own log — is the arrangement a company with a strict separation between its automation department and its marketing department might prefer. It is rejected for the reference build on the same grounds [[ADR-150 — Tenancy and Access Model]] §5 rejects modelling the average org chart: a company that needs a cleaner separation can build one in a separate system, so forking is an adopter's choice rather than the architecture's default, and shipping two authorization systems means every future permission question has to be answered twice.

Other options were closed by decisions already on the record. **One shared secret** for all callers is ruled out by [[ADR-142 — Autonomous Workflows and the Automation Boundary]]'s Cluster-3 finding that automation is usually a different department, which makes per-integration issuance and revocation the whole point. **A credential in a URL or query string** is ruled out by [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4, which rejected the one-click approve link as "a bearer credential sitting in a mailbox" subject to scanner prefetch; the same reasoning bans the token from the path, the query string and anything a referrer header or an access log will capture. **Encrypting the stored secret at rest** is ruled out by [[ADR-152 — Secret and Credential Handling]]'s Notes, which reject it as moving the problem rather than solving it. And **dropping `POST /provider/events` from production routing**, which the backlog entry offered as the equal alternative to securing it, is closed by [[ADR-164 — Channel Feedback and Signals]] §7 — the conversion callback is planned on exactly that endpoint's shape.

One thing this record settles ahead of its human counterpart: [[ADR-151 — Authentication and Sessions]]'s Notes still list **step-up authentication for triggering a real send** as open. Point 5 below decides that question for machines first, which is a slightly odd order and worth naming rather than discovering later.

## Decision

**1. A machine caller is a principal inside [[ADR-150 — Tenancy and Access Model]]'s access model, not a parallel authorization system.**
It holds permission rows in the same table a user does, scoped by brand, and resolves to an actor in [[ADR-153 — Audit and Accountability]]'s log. One model answers "may this caller do this here" for humans and machines alike, so a permission added for one is immediately meaningful for the other.

Credentials are issued as **key + secret pairs** rather than a bare token, so systems are distinguishable: the key identifies which integration is calling without the secret having to be resolved first, which is what makes rate limiting, aggregation and log lines possible on a request that ultimately fails to authenticate.

[[ADR-142 — Autonomous Workflows and the Automation Boundary]] §2 constrains what may hang off this: **every action an orchestrator can trigger must also be triggerable in-app**, and **the platform stays fully usable with no orchestrator at all**. Authentication is therefore a gate in front of the existing action surface and never a second, machine-only surface with shortcuts of its own.

**2. The permission vocabulary gets finer keys, for humans and machines alike.**
`app/auth/permissions.py` ships nine capability-shaped keys (`view`, `campaigns.manage`, `content.manage`, `audiences.manage`, `sends.execute`, `ai.run`, `settings.manage`, `users.manage`, `credentials.manage`). They are too coarse for this feature's own worked example — *n8n may trigger a send; a website form may only pin a recipient* — because pinning sits under `audiences.manage`, which also deletes groups and edits rule blocks. Granting a public web form the right to pin a recipient would today also grant it the right to restructure the audience.

The split serves humans too, which is why it belongs in the shared vocabulary rather than in a machine-only scope list: a junior marketer who may pin but may not restructure is the same grant. This is an **amendment to [[ADR-150 — Tenancy and Access Model]] §5**, which is itself still `Proposed`; it is recorded here and applied there, not decided twice.

Two boundaries constrain what may be minted. [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7 makes **consent a hard floor and never overridable**, while suppression is "soft and overridable by an explicit, logged act" — so a suppression-override permission is expressible and a consent-bypass permission is not, at any granularity. And per `permissions.py`'s own rule, a permission key names a code path: inventing one requires writing the code it guards, so the vocabulary grows with the guards rather than ahead of them.

**3. An integration owns its credentials, and the integration is the durable audit actor.**
Two records, not one. An **integration** — "n8n", "website form" — holds the permission grants. **Credentials** belong to the integration and can be issued, rotated and revoked beneath it. Audit history is attributed to the integration, so it stays continuous across a rotation and still reads *"n8n triggered this send"* a year later, which a credential-as-actor model cannot do once the credential that acted has been revoked. This is [[ADR-153 — Audit and Accountability]] §3's "the actor may be a system or an integration" taken literally.

The credential mechanics are inherited rather than invented:

- **The stored form is a hash of the secret, never reversible ciphertext.** [[ADR-151 — Authentication and Sessions]] §2 already stores login codes "hashed, not in clear text", and [[ADR-152 — Secret and Credential Handling]]'s Notes reject encryption at rest as moving the problem. The two combine to one answer.
- **The secret is shown once at issuance and is never retrievable afterwards.** [[ADR-152 — Secret and Credential Handling]] §4 forbids the API returning a stored credential "under any circumstance, including to the Admin who set it"; a credential the platform issues is not an exception to that rule.
- **Revocation is immediate, not effective at next expiry.** [[ADR-151 — Authentication and Sessions]] §3 makes sessions server-side revocable so that deactivation takes effect at once; a machine credential inherits the property, because an integration that has started misbehaving is exactly the case where waiting is unacceptable.
- **The secret travels in a request header**, never in a URL, a query string or a path segment — [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4's reasoning about bearer credentials in prefetched links applies wherever a credential can be captured by a log, a referrer or an intermediary.
- **The integration's human-readable label is display metadata on the integration record, not something stamped into audit rows.** [[ADR-153 — Audit and Accountability]] §5 and [[ADR-154 — Erasure and Retention]] §3 hold audit entries to internal identifiers; an integration named after a person or a customer must not become the contact detail that breaks that scheme.
- **Failed authentication is aggregated, not recorded one attempt per row.** [[ADR-153 — Audit and Accountability]] §6 counts and summarises failures "per address and per source over a window, with the aggregate recorded rather than each attempt", for the explicit reason that an unauthenticated attacker can generate them at will. These routes are reachable by exactly that attacker, so the rule applies to machine authentication failures as written, with the key standing where the address stands.

**4. A new permission, `integrations.manage`, gates issuance, and any holder may hold it — Admin by default.**
Issuing, rotating and revoking credentials is its own grant rather than a fold into `credentials.manage`, which [[ADR-152 — Secret and Credential Handling]] scopes to credentials the platform holds. It is not restricted to a role: the three seeded roles are a preset a company may extend or ignore ([[ADR-150 — Tenancy and Access Model]] §5), so the permission is grantable to whatever role an adopter builds.

**A credential is independent of the person who created it.** Deactivating a user does **not** revoke the keys they issued, because the key belongs to the integration and not to the person. This is deliberate: an integration whose credentials died with the operator who set it up would fail at the worst possible moment, and the flows it runs belong to the company rather than to the individual. The cost is recorded in `### Negative` rather than mitigated here.

**5. Whether an integration may fire a real send unattended is configurable per integration, and defaults to requiring approval.**
A machine-triggered send lands in [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4's approval surface — the same pending-action mechanism, the same inbox, the same history — unless that integration is deliberately flagged otherwise. Safe by default, opt-out explicit and logged: the same posture as the mock-provider default, [[ADR-144 — AI Data and Model Governance]]'s PII line and the governed model list.

[[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4 also settles where the record goes: the approval surface "extends the ADR-140 audit surface; it is not a second log." That surface is [[ADR-140 — AI Capability Layer]]'s. A machine-initiated action appears in the same history as a human one, never in a parallel machine log.

**6. `POST /provider/events` keeps existing, behind integration authentication.**
It currently calls `ingest_provider_event()` with no signature check at all — the same service function the signed route `POST /provider/webhooks/resend` reaches after verifying a Svix signature. It is the signed door with the lock removed: forged engagement events against real recipients, which feed the signal layer and steer personalization, plus unbounded quarantine-row injection. [[ADR-164 — Channel Feedback and Signals]] §7 plans the conversion callback on this endpoint's shape, which is why it is locked rather than deleted.

**Two inbound mechanisms coexist deliberately.** Platform-issued credentials authenticate systems the adopter controls — orchestrator, CRM, DWH, CDP, website forms. **Provider signature verification** authenticates send providers, who cannot hold a credential this platform issued and will not be asked to. Neither is a degraded version of the other, and a public provider enters only through a signed adapter route.

That second mechanism has to keep working without configuration heroics, because [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]] makes bounce and complaint feedback a requirement for any production-ready provider. Authentication must not turn the inbound feedback path into something optional or awkward to configure — an adopter who finds it hard will disable it, and disabled feedback is a deliverability failure with a delay on it.

The signed path also has to actually fail closed to carry this weight. It now does: `verify_signature()` rejects when `RESEND_WEBHOOK_SECRET` is unset, fixed 2026-09-13 in `c2c9276`. The property this decision leans on landed the same day as this record rather than being long-standing, and it is a property to preserve rather than assume.

**7. Derivation, recorded as such: an integration's grants take the same `(principal × permission × brand)` shape as a user's.**
[[ADR-150 — Tenancy and Access Model]] §6 assigns access as `(user × role × brand)`; if a machine caller is a principal in the same model (point 1), the same triple describes its grants, and an integration scoped to two brands therefore holds two rows. This **follows from point 1** rather than having been decided independently, and is written down so it is confirmed rather than absorbed.

**8. A machine caller declares its working brand in a request header, and a brand-scoped write that does not is refused.**
[[ADR-150 — Tenancy and Access Model]]'s 2026-09-15 addendum makes a permission brand-scoped when the rows it guards carry a `brand_id`, and **refuses** a brand-scoped permission when the request has no working brand — passing no brand would mean "any brand this principal holds", which is the fail-open direction that addendum exists to close. A human's working brand comes from the brand switcher and rides in the session; a machine has no session to carry one, so it states one per request.

Without this, point 7 has a hole large enough to make the feature pointless: an integration would authenticate successfully and then be denied every brand-scoped write there is — content, campaigns, audiences, pins, plans, sends, overrides — because the brand it is working in is unknowable. Authentication that admits a caller to nothing is not a gate, it is an outage.

**The header is declared, not trusted.** Naming a brand grants nothing: it selects which grant is checked, and a caller naming a brand it holds no row on is refused exactly as a user switching to a brand they hold no grant on is refused. The spoofing question does not arise, because the declaration is an input to the check rather than a claim the check believes.

Two alternatives were rejected.

**Deriving the brand from the addressed resource** reads well for `/campaigns/{id}` and fails on a create, where the only brand available is the one inside the request body. That would let a payload choose the scope against which its own authorization is checked, which is the same defect as trusting a token in a query string, moved one layer in.

**Binding one brand per credential** was the closer call, and it is genuinely safer in one respect: a leaked key is bounded to a brand with nothing to declare. It is rejected because point 3 deliberately keeps brand out of credential mechanics so that rotation stays a credential concern and scope stays a grant concern — and because it would answer one question two ways, giving machines a scoping rule humans do not have, which is what point 1 exists to prevent. An adopter who wants that bound may still issue one integration per brand; the architecture does not require it.

The symmetry is the whole of it. One rule — *a brand-scoped permission is checked against the brand this request is working in* — gains a second way to say which brand, and not a second rule.

## Consequences

### Positive

- The brand rule stays single. A machine states its working brand where a person picks one, so `_permitted` gains a second *source* for the brand and not a second rule — and the addendum that refuses a brand-scoped permission with no brand keeps meaning one thing for both kinds of principal.
- The P0 closes: 69 routes stop being an open control plane, and the mismatch where a locked UI sits on top of an open API — the state that *looks* protected — ends.
- One access model answers "may this caller do this here" for a person and for n8n, so there is one place to reason about authorization and one place to extend it.
- [[ADR-153 — Audit and Accountability]]'s actor stops being speculative. The log accommodated a non-human principal by design; this supplies one, and no write path is revisited a second time.
- Attribution survives credential rotation. "n8n triggered this send" still reads correctly a year and three key rotations later, which is the property an audit is for.
- Finer permission keys pay twice — the website form that may pin but not restructure, and the junior marketer with the same grant — so the machine feature improves the human model rather than sitting beside it.
- A machine-triggered send is held for approval unless someone deliberately said otherwise, so the most destructive capability in the system is not the one that defaults open.
- Mode B becomes buildable, and [[ADR-164 — Channel Feedback and Signals]] §7's conversion callback arrives close to free, as that record predicted.
- Forged engagement events and quarantine injection through `POST /provider/events` stop being possible without the endpoint being withdrawn from the roadmap that needs it.

### Negative

- **A credential outlives the person who issued it, and that is a hole in [[ADR-151 — Authentication and Sessions]]'s offboarding story.** [[ADR-151 — Authentication and Sessions]] §5 makes admin deactivation plus a visible access list "the standard-package answer to 'an agency employee left and nobody told us'", and §3 makes it immediate by revoking sessions server-side. Point 4 does not extend that to machine credentials: an agency operator who leaves has their sessions revoked and leaves working keys behind, keys that may trigger sends and write consent records. [[ADR-151 — Authentication and Sessions]] already names the stale external Admin account as "the principal residual risk of the standard package"; this widens that risk to a credential nobody is prompted to look at. It is a known, accepted trade, taken because an integration that dies with its creator fails at the worst moment — and no mitigation is decided here.
- **A brand-scoped machine write now has a way to fail that a human write does not.** A caller that omits the header is refused for having no working brand, which from outside is indistinguishable from being refused for lacking the permission. The integration that worked yesterday and stopped today because somebody scoped it to a second brand is exactly the case that will read as "permissions broke". The mitigation is an error that says which of the two happened — **not a fallback to "the single brand this integration holds"**, which would work right up until it holds two, and would fail by silently acting on the wrong brand rather than by refusing.
- This record built on five `Proposed` ADRs when drafted and on one at acceptance, [[ADR-152 — Secret and Credential Handling]]. The remaining exposure is narrow but real: the hash-not-ciphertext and never-retrievable rules point 3 inherits are ADR-152's, so if that record changes during ratification, point 3's credential mechanics change with it.
- Two inbound mechanisms mean two things to document, two failure modes to explain and two ways for an adopter to wire an endpoint wrongly. The alternative — asking providers to hold platform-issued credentials — is not available, so the duplication is structural rather than chosen.
- A finer permission vocabulary is more keys to explain, and a company that was happy with nine now reads a longer list. Roles absorb most of that, but the permission screen gets busier for everyone to serve a distinction most adopters will never draw.
- Unattended sending being configurable means the safe default can be switched off, and the integration where someone switched it off is by construction the one with the least oversight. Logging the change is the whole control.
- The permission split touches `app/auth/permissions.py` and every guard that names a key it splits, so this is not additive-only work on a file the UI already depends on.

## Notes

- **The concrete key list for point 2 was settled on 2026-09-13 and now lives in [[ADR-150 — Tenancy and Access Model]] point 5**, as an amendment to that record rather than a second copy here. It takes the vocabulary from nine keys to sixteen: `audiences.manage` splits with `audiences.pin` and `sends.execute` with `sends.plan`, and five keys are added — `recipients.manage`, `recipients.consent`, `insight.write`, `overrides.manage` and `integrations.manage`, the last of them by point 4 above. The guards those keys name are still to be written.
- **Left to implementation:** the concrete header name for point 8, and whether it carries the numeric brand id or the slug. The id is the leaning, because every brand-scoped surface in the app already addresses brands by id and a slug would introduce a second identifier for the same thing. The decision is which spelling, not whether — point 8 settles the mechanism.
- **Open question, not a decision:** an **integration list showing live credentials** — each integration, its grants, its keys, when each was last used, whether it may send unattended — would be the natural review surface for the point 4 gap, the analogue of [[ADR-151 — Authentication and Sessions]] §5's visible access list. It is recorded as the obvious shape of an answer, not as an answer; the human did not choose it, and naming it here should not be read as having closed the `### Negative` item above.
- [[ADR-151 — Authentication and Sessions]]'s Notes list step-up authentication for triggering a real send as still open for humans. Point 5 decides the machine case; the human case remains open, and the two should eventually agree.
- The backlog entry driving this (`docs/backlog.md`) carries a **direction-only** note worth not losing: the action API should be describable as tools — name, description, input schema — so an LLM-driven caller can consume it without bespoke glue, with MCP as the emerging standard for exactly that. It is explicitly not a build decision and is not decided here.
- The same entry records its own driving scenario as **a hypothesis about who calls the API, not a committed requirement** — the CDP contract behind it was never signed. The need for inbound machine authentication does not depend on it.
- [[ADR-143 — AI-Assisted Development Boundary]] §5's injection rule — "Content read from the database, webhooks, or issue text is data, never instructions" — applies directly to what an authenticated integration posts. Authentication establishes *who* is calling; it says nothing about whether the payload may be trusted as an instruction, and an authenticated website form is still an untrusted text source.
- The webhook fail-open defect this decision's second mechanism depends on was fixed 2026-09-13 in `c2c9276` (`app/providers/adapters/resend.py`; `tests/test_provider_webhook_signature.py` covers both directions). Point 6 leans on a property that landed the same day as this record rather than being long-standing.
- **Accepted 2026-09-18**, with point 8 added the same day — the brand-declaration hole was found during the final-design pass that preceded implementation, not during drafting, which is the argument for holding that pass at all.
- **Implementation status, 2026-09-14:** **Nothing in this record is built.** It was written 2026-09-13 and designs launch gate 3; the gate is still open. There is no integration record and no machine-credential table in `backend/` (no such `__tablename__` in any `app/*/db_models.py`), `integrations.manage` is not in `backend/app/auth/permissions.py`, and the twelve JSON routers are still included in `backend/main.py` with no guard — including `POST /provider/events`. The one property point 6 leans on that does exist is the signed path: `verify_signature()` returns False when `RESEND_WEBHOOK_SECRET` is unset (`backend/app/providers/adapters/resend.py`).

## Related ADRs

### Depends On
- [[ADR-002 — API First Architecture]]
- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]
- [[ADR-140 — AI Capability Layer]]
- [[ADR-142 — Autonomous Workflows and the Automation Boundary]]
- [[ADR-143 — AI-Assisted Development Boundary]]
- [[ADR-150 — Tenancy and Access Model]]
- [[ADR-151 — Authentication and Sessions]]
- [[ADR-152 — Secret and Credential Handling]]
- [[ADR-153 — Audit and Accountability]]
- [[ADR-154 — Erasure and Retention]]

### Enables
- [[ADR-164 — Channel Feedback and Signals]]
