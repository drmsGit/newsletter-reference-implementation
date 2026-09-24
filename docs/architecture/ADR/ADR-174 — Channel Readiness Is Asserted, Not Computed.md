---
type: adr
status: accepted
topic:
  - architecture
  - channels
  - content
  - approvals
created: 2026-09-24
source:
  - "Manager Workflow design interview (interview-prep), Cluster 2 / Q3, Q3b, Q6b — cluster closed 2026-09-21"
depends_on:
  - "[[ADR-082 — AI May Recommend but Not Publish]]"
  - "[[ADR-142 — Autonomous Workflows and the Automation Boundary]]"
  - "[[ADR-160 — Channel Model and Composition]]"
  - "[[ADR-161 — Channel Execution Shapes]]"
  - "[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]"
---

## Status
Accepted

## Context

[[ADR-160 — Channel Model and Composition]] point 3 settled that channel readiness is *a property of the content record* and that channel fields are separate and required rather than derived from email fields. It did not say how that property comes to be true. [[ADR-161 — Channel Execution Shapes]] point 7 answered it in passing, as a rider: *"Catalogue readiness is 'push fields not empty'"* — readiness computed from the data, no state and no act. That is the answer this record reverses.

**The reason is that filling fields and declaring a record fit to go out are different claims, and only the second one is a decision.** A manager who types a push title into a record has done authoring work; they have not said "this may go to a device". Computing readiness from field emptiness conflates the two and hands the decision engine an assertion nobody made — the record becomes selectable the instant the last field is populated, including mid-edit, including by an agency that has never had its copy read by anyone here. [[ADR-160 — Channel Model and Composition]] point 3's own promise that decision slots *"filter candidates to channel-ready records"* is what makes this expensive rather than cosmetic: a computed flag means the engine's candidate set is a side effect of keystrokes.

**The cluster principle this record is one instance of was not asked for; it emerged across five questions and it should outlive this decision: the system reports, the manager decides.** The system does not collapse a section because it looks empty, does not infer readiness from filled fields, does not un-assert what a person asserted, and does not nag about a gap. It makes facts visible at the moment they bite and leaves the judgement to the person. Where a signal is genuinely load-bearing it becomes a **check at the point of action** rather than a nag earlier on, which is exactly the shape point 3 below takes.

**The automation pressure is what makes the machine case urgent rather than theoretical.** The same interview established that content authoring is explicitly outsourceable — to an agency or to an AI agent — and that this is the *sustainable* pattern rather than an edge case, because the decision engine's value is proportional to catalogue depth and campaign-first authoring leaves a slot with nothing to choose between. So the author of a push title is frequently not a person with a session, which turns "who may say this is ready" from a UI question into an access-model one. [[ADR-082 — AI May Recommend but Not Publish]] is unambiguous that production decisions may only use approved content records and that a machine may draft but not publish; a machine that could mark its own output ready would satisfy the letter of that record while defeating it, because *ready for push* is precisely what the decision layer consumes.

**A rejected option is worth keeping: auto-unmarking when a required field is emptied.** It is the tidy answer — the flag and the fields never disagree, no warning state exists, nothing can travel to a send in an inconsistent condition. It was rejected because it undoes a deliberate act on the strength of a transient one: a manager who clears a field to retype it loses the mark silently, and discovers it only when a slot stops choosing the record. Consistency bought by overruling the person is the same trade as auto-collapsing an empty section, and the same answer applies.

## Decision

**1. Channel readiness is asserted by a person, per channel, and stored on the content record.**
It is explicit state, not a computation over `content`. A manager marks a record ready for push deliberately, the same act shape as publishing, and the decision layer trusts that mark rather than inspecting fields. This **strengthens [[ADR-160 — Channel Model and Composition]] point 3 rather than amending it** — readiness was already a property of the content record, and is now a stored property rather than a derived one, which is what gives the candidate filter, the per-channel list filter and the slot candidate count something real to read.

**Readiness is a different axis from `status`, and the two must not be merged.** `status` stays the record's own lifecycle — `active` / `inactive`, constrained to exactly those two at `backend/app/content/service.py:85`, where the comment already refuses to invent a richer vocabulary locally. That axis answers *may this record be newly selected at all*; readiness answers *may it go out on this channel*. A record can be active and ready for email and not ready for push, and there is no ordering between the two facts. Collapsing them would produce a status enum that grows by one value per channel registered, which is the same mistake as putting channel into the campaign's structure.

**2. The fields and the flag may disagree, and the system does not resolve that for the manager.**
When a required field for a channel is emptied on a record already marked ready, the client **warns and keeps the mark** — *marked ready for Push, but `push_title` is empty* — wherever the record appears. It does not auto-unmark, and it does not block the edit.

The reasoning is in Context and is not re-argued here, but the honest reading of what this buys is worth stating: the warning is **information, not a control**. It can be ignored, and an ignored warning travels. That is only acceptable because point 3 exists; without a check at the point of action this decision would be a deliberate hole with a tooltip over it.

**3. A required-field check runs before a send fires. This is not optional and it does not exist today.**
"Let the send catch it" presumes something checks, and nothing does. `resolve_module_variables` (`backend/app/rendering/service.py:296-306`) defaults a missing field to `""`, and `ModuleVariable.required` (`backend/app/modules/registry.py:41`) is surfaced to the Jinja form and to `GET /modules` and **enforced nowhere** — so today an empty push notification ships to a real device with no warning anywhere in the system, and the first party to learn is the recipient. The check belongs in the pre-flight the send review screen performs, and it is one of the narrow set of things that **blocks** rather than informs: the system blocks what is broken and reports what is merely questionable, and an empty required field on a message that reaches a device is broken rather than questionable.

This is the only place in this record where the system overrules a person, and the asymmetry is deliberate. Point 2 refuses to overrule a manager's assertion about *intent*; point 3 refuses to ship a payload that is *malformed*. Those are different claims about different objects, and a check that conflated them would be the nag point 2 rejects.

**4. An integration may assert readiness, and its assertion routes through the approval inbox.**
A person marking a record ready is not held — the same shape as firing a send, where a person doing it *is* the approval. A machine's assertion creates a held action a person decides.

This **reuses [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4's held-action machinery rather than inventing a review concept**: the platform stores the pending action, the orchestrator or agency call finishes immediately rather than parking a long-running execution, and approving executes it. It honours [[ADR-082 — AI May Recommend but Not Publish]] **without needing an exception** — the machine still recommends, the person still publishes — which is the whole reason to spend a held action here rather than grant integrations a readiness permission.

Two concrete obligations fall out, and the second is the one that bites silently. A new approvable action is owed in `backend/app/approvals/actions/`, which today registers exactly two — `send.fire_send_instance` and `ai.apply_subject_preheader`. And it needs an `APPROVABLE_ROUTES` entry in `backend/app/auth/policy.py`: that table is **fail-closed by omission**, and it currently holds one route, so without an entry a machine asserting readiness gets a hard 403 rather than a hold — a correct refusal that reads exactly like a broken integration.

**Nothing new enters the permission model.** There is no per-channel authoring right and no split between writing and governing: a person who may edit content may edit all of its channels and assert readiness on any of them. Registering a channel stays the two files [[ADR-160 — Channel Model and Composition]] point 6 promises, rather than also adding a permission, a role and a grant per channel.

## Consequences

### Positive

- **Readiness becomes a checkable fact rather than an emergent one.** [[ADR-160 — Channel Model and Composition]] point 3's promise that slots filter candidates to channel-ready records — declared by `top_score`'s `candidate_filter_fields` and never implemented — finally has a column to filter on, and the slot's candidate count has something countable.
- **Per-channel readiness becomes a filter dimension**, which is what makes a newly registered channel workable: a manager filters to "not ready for WhatsApp" when they decide to work on it, and no banner, badge or rollout queue is needed.
- **The empty-push hole closes.** Point 3 fixes a defect that predates this decision entirely and that nothing in the repository had written down: `required` was declared in manifests, rendered into forms, and never enforced on the path where it mattered.
- **Machine-authored content gets a human gate with no new concept.** The approval inbox, the audit trail and the expiry behaviour already exist; this adds a second action type to machinery built to carry several, and the approval detail screen already renders the server's rows generically rather than knowing action types.
- **[[ADR-082 — AI May Recommend but Not Publish]] holds literally rather than approximately.** No carve-out, no "AI-authored records are trusted if fields are complete", and the boundary sits at the one act that determines what the decision layer may select.

### Negative

- **New per-channel state on the content record, and a migration for it.** This repository has no Alembic — tables come from `create_all` plus hand-written `backend/scripts/migrate_*.sql`, nineteen of them so far — so a schema change is a file somebody writes, reviews and runs in the right order, not a generated artefact. The shape is also not free of judgement: readiness is per record *per channel*, so it is either a column set that grows with every channel registered or a child table, and the cheap answer is the one that makes adding a channel a migration again.
- **A warning state can travel all the way to a send, and the warning is therefore not a control.** Point 2 deliberately allows a record to sit marked-ready-but-incomplete indefinitely, visible and ignorable. Everything that keeps that safe is in point 3, which means **the entire safety of this decision rests on an unbuilt check** — and until it is built, this record has made an inconsistent state legitimate without the thing that catches it. That is the correct order to decide in and the wrong order to ship in.
- **The approvals inbox gains a second and potentially high-volume input, and it was built for the first.** A send approval arrives a few times a day; an agency delivering forty records delivers forty held actions in one call. The inbox is a single flat list, and content review could swamp the send approvals that are the higher-stakes item in it. Filtering by action type and by requester is the answer chosen, which is a mitigation rather than a solution — a manager who has to filter to find a send approval is one filter click away from missing it.
- **An adopter whose editorial process is richer than this gets no support for it.** Readiness is one binary assertion per channel plus a machine-assertion hold. A house with a copy desk, a legal review and a brand check has three gates and this model has one, so they either overload the single flag or keep their real process outside the system where nothing can filter on it. That is the cost of refusing an ownership, assignment or "waiting on" concept, and it is a real cost rather than a theoretical one for exactly the mid-sized organisations this architecture is aimed at.
- **The `status`/readiness split is one more axis a manager must hold in their head**, on a screen that already grows a section per channel. Two independent state axes is the honest model and it is not the simple one, and the first support question this produces will be someone asking why an active record is not being selected.

## Notes

- **This makes an [[ADR-161 — Channel Execution Shapes]] rider false, and it must be corrected rather than quietly ignored.** Point 7's rider — *"Catalogue readiness is 'push fields not empty'"* — is not narrowed by this record, it is contradicted: readiness is asserted, not computed. The rider was **never implemented**, so nothing breaks and no data is wrong; what is wrong is the record. The rest of point 7 stands untouched — the authoring contract still lives in the module manifest, lengths are still an editor input constraint rather than a validation gate, and the provider/manifest/channel split is unchanged.
- **This is a dated addendum to ADR-161, not a supersession, and the distinction was checked rather than assumed.** ADR-161's Decision is about execution shapes, provider interfaces and where the authoring contract lives; the readiness rider is one clause inside point 7 and none of the rest of the record depends on it. Superseding a record over one falsified clause would discard eight points that are still in force. **This repository has had exactly one supersession ever — [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] over ADR-001, on 2026-09-12 — and this is deliberately not a second.** The addendum text is reported with this record rather than applied to it, per the rule that a new record does not edit an accepted one.
- **Precision on the approvals plumbing, because the two numbers differ and the difference matters.** `backend/app/approvals/actions/` registers two actions; `APPROVABLE_ROUTES` in `backend/app/auth/policy.py` maps exactly one route, the send. So the work point 4 owes is a registered action *and* a route entry, and shipping the first without the second produces a 403 on a route that looks configured. **The existing mismatch is not a defect, and saying so avoids a false reading:** `ai.apply_subject_preheader` is created by a service calling `approvals.request_approval` directly (`backend/app/ai/orchestration.py:102`), so it never passes the guard and needs no route entry. `APPROVABLE_ROUTES` exists for the other mechanism — a route tripping `ApprovalRequired`, where the guard must be told what to queue. Readiness needs a route entry only if a machine asserts it by calling a route, which is the shape point 4 assumes.
- **Deliberately not decided here: what blocks the send beyond an empty required field.** Zero recipients clearly blocks and the recipient cap already raises; whether a thin decision slot or an excluded force-add joins them is open, and getting that list wrong in either direction is how the review screen becomes either a rubber stamp or an obstacle. This record contributes one entry to that list and does not settle it.
- **Also not decided: whether a marked-but-incomplete record should be excluded from slot candidacy.** Point 1 says the engine trusts the mark and point 2 says the mark survives an emptied field, which together mean a slot can select a record that the send will then refuse. That is the honest consequence of the two decisions and it is survivable — the failure is caught at the send rather than at the selection — but it is a second place the same fact could be checked, and checking it in both is how the two answers drift apart.

## Related ADRs

### Depends On
- [[ADR-082 — AI May Recommend but Not Publish]]
- [[ADR-142 — Autonomous Workflows and the Automation Boundary]]
- [[ADR-160 — Channel Model and Composition]]
- [[ADR-161 — Channel Execution Shapes]]
- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]
