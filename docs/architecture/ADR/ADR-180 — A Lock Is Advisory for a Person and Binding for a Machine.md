---
type: adr
status: accepted
topic:
  - architecture
  - automation
  - governance
  - frontend
created: 2026-09-27
source:
  - "[[Variant Editor - design interview]] Cluster 1, question 1.7, resolved 2026-09-25"
depends_on:
  - "[[ADR-002 — API First Architecture]]"
  - "[[ADR-142 — Autonomous Workflows and the Automation Boundary]]"
  - "[[ADR-153 — Audit and Accountability]]"
  - "[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]"
---

## Status
Accepted

## Context

Two people can open one variant and edit it at the same time, and today the second save silently overwrites the first. *"It can happen and data loss is always bad."* That much is ordinary, and it is not why this record exists.

**The argument that decides the shape of the answer is about machines, not colleagues.** Two humans editing one variant is plausible and rare. The user:

> *"it's realistic that there will be proper ai agents that 'work' parallel in the system. So they need some sort of fence to not start working on something that is edited in that same moment"*

[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] already makes an agent a first-class caller with the same access model as a person, and [[ADR-142 — Autonomous Workflows and the Automation Boundary]] anticipates an orchestrator acting on its own schedule rather than on a manager's. An agent that begins rewriting a variant somebody is mid-edit on produces exactly the silent loss this question is about, except **faster and more often**. So concurrency control on a variant is infrastructure for machine principals rather than a courtesy between two people, and that reframing is what makes the *policy* — who may clear a fence — the decision, while the mechanism underneath it is not one.

**Autosave makes this sooner rather than later.** Question 2.1 chose a composer whose preview needs no render button, which means autosaving on field blur, which makes conflicts **more** frequent rather than less. Both layers below therefore belong with the composer build and neither is safely deferred past it.

**A real, enforced lock was rejected for a failure mode, not for cost.** A lock only its holder can release is a lock held by someone who went on holiday, and breaking it becomes an administrator's errand. A team of colleagues does not need that, and building it would trade a rare problem for a recurring one.

**Optimistic concurrency alone was the user's floor rather than the answer** — *"we need at least B"*. It is a floor because it does not prevent a collision; it only refuses the second write. With autosave in the picture, a floor on its own means colleagues meeting refusals routinely, which is why a social layer sits above it.

**Three facts about the model, verified rather than assumed.** `variants` and `module_instances` both already carry `updated_at` with `onupdate=func.now()`, so a version check needs no schema change. **Neither table records who changed it** — there is no `updated_by` on either, and the nearest actor column anywhere is `ContentVersionDB.created_by` — so *"last updated by X at HH:MM"* has to be read from `audit_events` (`actor_type` + `actor_id`, `subject_type` + `subject_id`, indexed `created_at`) rather than from the row. That makes this the **first real consumer of `audit_events`**, a table `docs/backlog.md` flags as having three unproven properties *precisely because nothing reads it back*.

## Decision

**1. A variant carries an advisory lock, not a real one.**
The composer shows *"blocked by X, last updated HH:MM"* with an unblock control, and **anyone may clear it themselves, without asking**. The expectation is that they check first. The user's own framing is the specification:

> *"Locking would be nice in the form of that it's 'blocked by XX'. Each manager can click on 'unblock' themselves, but they will check before. So it doesn't have to be a real 'lock'. Technically maybe a 'last updated by X on XX at XX:XX - unlock'."*

**It is a social signal rather than an enforcement mechanism, and that is the design.** It is the cheapest thing that works among colleagues and it deliberately avoids the holiday problem a real lock creates.

**2. Optimistic concurrency sits underneath it, and it is an implementation detail rather than a decision.**
`updated_at` is already the version token on both tables, so the whole of it is a comparison on write and a 409 on mismatch. **That layer gets no ADR of its own and this record does not dress it as one.** What is worth writing down is *why the two layers coexist*: the lock prevents the common case socially, and the version check makes the uncommon case — two people who both click through — **visible**.

Silent data loss is the one bug class a person cannot detect, report or work around; they find their work missing later and do not know why. The version check does not prevent the collision. **It converts it from invisible to visible, and that conversion is the whole value.**

**3. The same lock is advisory for a person and binding for a machine.**
A human clearing a fence is exercising judgement — *"I know she is at lunch, this is fine"*. An agent has no such judgement, so **an agent must never clear a fence it did not set**, and a write from a machine principal to a variant fenced by somebody else is refused rather than merged. One field, two policies.

This is the record's reason to exist. Everything else here is either mechanism (point 2) or the ordinary product of the user's answer (point 1); the asymmetry is the new rule, and it is a rule about what a machine principal may *not* do rather than a property of a screen.

**4. Derivation, recorded as such: the asymmetry lives in the rule, and it is a property of the actor type rather than a grantable permission.**
Two things follow from point 3 and are written down so they are confirmed rather than absorbed.

**It is enforced server-side.** [[ADR-002 — API First Architecture]] makes the API the boundary every caller crosses, and [[ADR-142 — Autonomous Workflows and the Automation Boundary]] point 2 requires that every action an orchestrator can trigger is also triggerable in-app — so a rule implemented in the manager client is absent for exactly the caller it exists to constrain. A convention nobody enforces is not the mechanism this decision asked for.

**It is not a permission key.** [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 2 makes the permission vocabulary shared between people and machines, so expressing "may clear a fence" as a key would make it grantable to an integration, which point 3 forbids outright. The distinction is therefore conditioned on the actor type the audit layer already records, not on a grant an adopter can hand out.

## Consequences

### Positive

- **Silent overwrite stops being possible in the composer's edit path.** A manager either keeps the lock, sees whose it is before clearing it, or gets a refusal — never a saved file that quietly lost somebody's paragraph.
- **The machines get their fence before the machines arrive**, which is cheaper than retrofitting it onto a write path an orchestrator is already using. [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] made an agent a principal; this is the first rule that tells one what it may not do.
- **One field carries both policies**, so there is no machine-only locking table, no second concept and nothing to keep in step — which is the same posture ADR-166 point 1 takes towards authorization.
- **The version check costs no schema change.** `updated_at` with `onupdate=func.now()` exists on both tables, so the floor is a comparison and a status code.
- **`audit_events` acquires its first reader, cheaply.** The three properties `docs/backlog.md` calls unproven get exercised by one subject, one lookup and no brand filtering — a far smaller first consumer than the operator screen that item anticipates, and it settles them before that screen is designed.

### Negative

- **Two people who both click through still collide.** The advisory lock is unenforced by design, so the 409 is the backstop, and somebody redoes work. Visible loss instead of silent loss is the trade, and it is not the same as no loss.
- **The asymmetry reintroduces the holiday problem on the machine side.** A lock nobody clears is harmless to a person, who may clear it, and blocking to an agent, which may not. Whether a fence expires, and after how long, is **not settled here** — the alternative is an orchestrator that stops on an abandoned lock and needs a human to notice, which is the failure point 1 rejected arriving through the other door.
- **What a blocked agent does instead is left to implementation** — retry, defer, or raise the conflict to a person. This record settles that it must not write and must not clear; it does not settle what it does next.
- **A UI string now depends on the accountability log.** Because neither table has an `updated_by`, *"blocked by X"* is a read of `audit_events`, so a missing or mistyped `action` shows a manager nothing rather than showing them something wrong elsewhere. [[ADR-153 — Audit and Accountability]]'s Notes warn against the audit log displacing domain records; this leans on it for a product surface without adding a domain column, and the tension is booked rather than resolved.
- **Autosave and both layers are now one piece of work.** A composer that saves on blur without a version check is worse than one that does not autosave at all, so neither layer can trail the composer the way most of the editor's decisions can.

## Notes

- **`actor_id` is an id, not a name, and this record does not resolve that.** Rendering *"blocked by Jana"* or a set of initials needs a join the audit layer deliberately does not do — [[ADR-153 — Audit and Accountability]] point 5 keeps internal identifiers rather than contact details in the log, and point 5's asymmetry is the reason: an operator attribution has to outlive a recipient erasure. Where the display name comes from is a build question with a real constraint on it, and it is recorded as a tension rather than answered.
- **This does not reopen [[ADR-178 — Scope of the Correction, Not Location of the Manager]] point 8, which excludes owner names from the composer.** There the count answers *"how big is this edit?"* and the people behind it are the approval inbox's question — *"the composer reports scope, not people"*. Here the person **is** the signal: an advisory lock nobody can attribute cannot be socially checked, which removes the only mechanism point 1 has. The two records differ on whether the name is the point, not on what the audit log stores.
- **ADR-178 point 6 already leans on this decision without linking to it** — reset is available to anyone who may edit the variant, because *"restricting it to the author recreates the holiday problem the composer's advisory lock was shaped to avoid"*. That record was written first, from the same interview; no addendum is owed for a missing wikilink.
- **Point 3 is the third actor-type asymmetry in [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]'s neighbourhood, not a new parallel system.** That record's point 8 gives a machine a per-request working brand where a person's rides in the session, and its build-note 2 refuses an integration the implied `view` that every role grants. Both are justified the same way this one is: the machine genuinely differs, so one rule reads the actor type. What ADR-166 point 1 rejects is a *second authorization model* — its own credentials, its own scopes, its own log — and nothing here adds one.
- **Wanted and explicitly deferred by the user, not by the drafter:** presence indicators — *"showing users initials in a bubble on top, each that ever worked in that campaign"* — and a slim per-campaign history. *"Not necessary from the beginning."* Both are the natural second consumer of the same `audit_events` lookup this record introduces, which is why they are cheap later and not worth holding the composer for now.
- **This is not a supersession and no ADR's status changes.** The repository has had exactly one supersession ever, [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] over ADR-001 on 2026-09-12, and this is deliberately not a second.
- **`docs/playbook-strategy.md` carries the 2026-09-27 decision-log entry behind this record**, under *Variant Editor Design Interview (ADR-177) — interview closed*, which names *"the machine-versus-human lock policy"* as the first of three ADRs the interview still owed. Nothing here departs from it; the entry's title predates this record and ADR-178.

## Addendum 2026-10-04 — a fence is set by editing and lapses after 30 minutes

Prompted by building task-254, which asked *"How should a variant's fence be set, and when does it end?"* The user's answer, *"Set by editing, lapses"*, settles what Consequences → Negative left open: whether a fence expires, and after how long.

**The decision.** Any edit to the variant — subject or preheader, modules, overrides, slots — sets *"blocked by X, last updated HH:MM"*. The fence **lapses after 30 minutes without edits**, and anyone may unblock it sooner. A forgotten fence therefore never stops a machine for long, which answers the holiday problem point 3 reintroduced on the machine side.

Two options were rejected. A fence that **never lapses** means an abandoned fence stops automation until someone notices — the very failure this record's Negative names. An **explicit *"I'm working on this"* button** means nothing is fenced unless someone remembers to press it.

**Build decisions taken with it — mechanism, recorded as such:**

- **The fence lives on the variant row, as who and when:** actor type, actor id and a text label, plus the time of the last edit. The label is the readable name, the same value `content_overrides.overridden_by` carries via `auth.service.actor_label` — a user's email, `integration:<name>` for a machine. This resolves the first Note's open tension about display names the way task-243 settled override authors: the text label is the readable copy, and `audit_events` keeps the id-based record ([[ADR-153 — Audit and Accountability]]).
- **"Last updated by X at HH:MM" is the fence itself**, refreshed by every composer write, not a read of `audit_events`. task-254's original acceptance criterion — *read from `audit_events`* — is met by the fence instead. The Context's "first real consumer of `audit_events`" and the Negative bullet on a UI string depending on the accountability log therefore describe the reasoning at the time, not the build.
- **Every composer write on both planes refreshes the fence to its actor.** Editing never waits on a fence for a person; point 1 stays advisory.
- **A machine is refused with HTTP 423 Locked** when its composer write targets a variant whose fence is active and held by another actor. 409 already means a stale version (point 2), so the two refusals stay distinct. It is enforced server-side by actor type, as point 4 requires.
- **Unblock follows point 3.** A person may clear any fence; a machine may clear only a fence it holds. Unblocking is audited.

What a blocked agent does next is still open, as the Negative says. The lapse bounds how long it waits; it does not choose between retry, defer and escalation.

## Related ADRs

### Depends On
- [[ADR-002 — API First Architecture]]
- [[ADR-142 — Autonomous Workflows and the Automation Boundary]]
- [[ADR-153 — Audit and Accountability]]
- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]

### Referenced By
- [[ADR-178 — Scope of the Correction, Not Location of the Manager]]
