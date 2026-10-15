---
type: adr
status: accepted
topic:
  - architecture
  - content
  - decision
  - governance
  - data-model
created: 2026-09-27
modified: 2026-10-15
source:
  - "[[Variant Editor - design interview]] question 1.8 (resolved 2026-09-25) and question 2.9 (resolved 2026-09-26)"
depends_on:
  - "[[ADR-011 — Store Reusable Content Only]]"
  - "[[ADR-013 — Content Reference Instead of Content Copy]]"
  - "[[ADR-080 — Human-governed Taxonomy Before AI Selection]]"
  - "[[ADR-082 — AI May Recommend but Not Publish]]"
  - "[[ADR-162 — Channel Rendering and Artifacts]]"
  - "[[ADR-174 — Channel Readiness Is Asserted, Not Computed]]"
---

## Status
Accepted

## Context

A module manifest's `cms` boolean decides where a module's variables come from: `manifest.cms` is the branch at `backend/app/rendering/service.py:162`, and it sends rendering either to the resolved content record or to the `module_data` blob on the module instance. The manifests split six ways today — `email/header` and `email/cta` and `email/hero` static, the three image modules and `push/notification` catalogue-bound — and nothing in the record set said why the line sits where it does.

**The user proposed moving it to the far end, and the argument was coverage rather than consistency.** The proposal was that **all** non-decorative modules become `cms: true`: *"If a manager is forced to select content definitely everything is categorized. That leaves only decorative 'modules' as 'non cms modules' like divider."* The prize is real and it is worth stating in its strongest form, because it is the reason the narrower line has to be justified rather than assumed. Categorisation exists for exactly one purpose the user established earlier — building the recipient's affinity profile — and content typed straight into `module_data` is invisible to that profile forever. Every hand-typed module is therefore a small permanent hole in the signal the decision layer runs on, and holes of that kind are never noticed, because nothing reports the absence of a record that was never created.

**The narrower line was taken anyway, and the deciding test is whether a field carries topical signal.** A test is available because categorisation feeds one thing rather than several: [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]] records the user's own framing — *"CategoryDB and the whole 'categorize content' is ONLY meant for the 'build a dynamic affinities profile of each recipient'"*. `hero` is a headline and body copy about a subject, so it passes, and its invisibility to the affinity profile today is a genuine defect. `cta` is *"Book now"* and `header` is a subject line written for one campaign; a catalogue row for either would add an affinity record worth nothing while filling the catalogue with one-offs. That degrades the very thing the coverage argument protects, and it collides directly with [[ADR-011 — Store Reusable Content Only]], which already places one-off campaign content in the composition layer *"as an override or manually configured module content"* on the grounds that an uncontrolled catalogue makes automation and recommendation worse rather than better.

**A counter-argument was offered and rejected on its merits, and the rejection is the sharper reasoning of the two.** The counter was that the strict line becomes workable if the override layer carries the per-campaign variation — bind `cta` to a canonical *"Read more"* and override the label each time, preserving coverage without one-off rows. The user took the narrower line **and** confirmed in the same breath that *"an override is an everyday tool"*, so the counter was not refused for lack of cheap overrides. **It addressed the wrong objection.** Cheap overrides solve the *friction* of routing every CTA through the catalogue; they do nothing about the fact that a catalogue row carrying no topical signal is worthless whatever it costs to create. The conditional conflated cost with value, and the two have to be separated before this line can be argued at all.

**The second decision arrived in the same cluster, raised by the user rather than asked for.** During question 2.8: *"toggl for 'machine ready' that way a manager can decide if it's save to use this content record (we need this anyway, maybe there's content that's only allowed for a specific target group or time or any other reason that must be excluded from machine pick)"*. This is a third assertion axis on the content record, and [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] point 1 already made the argument against merging axes once, for a different pair: collapsing `status` and channel readiness would produce an enum that grows by one value per channel registered. The same reasoning applies again and reaches the same answer.

**The axis nearest to it is not an axis at all, and the distinction is what makes the flag worth having.** `DecisionSlotDB.candidate_filter` is *the slot saying what it wants*; machine-ready is *the record saying whether it may be taken at all*, and it applies to every slot at once. A slot filter cannot express "never, automatically, by anyone" without every slot author remembering to write it — the fail-open shape this repository refuses elsewhere, and the same reasoning [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]] point 6 used when it made a separation structural rather than conventional.

**And it must be asserted rather than computed, for [[ADR-174 — Channel Readiness Is Asserted, Not Computed]]'s own reason.** The exclusions the user lists — a target-group restriction, a time window, *"any other reason"* — are **intent**, and no computation over the `content` blob can see intent. A record with every field filled says nothing about whether a person is willing for a machine to place it unsupervised.

## Decision

**1. Catalogue binding follows topical signal. `hero` becomes `cms: true`; `header` and `cta` stay static; decorative modules stay static.**

The test is **does the field carry topical signal**, and it is the right test because categorisation feeds exactly one consumer — the recipient's affinity profile. A module whose copy is about a subject belongs in the catalogue, because binding it is what makes it visible to that profile. A module whose copy is envelope or call-to-action text does not, because a catalogue row for it produces affinity records worth nothing and leaves the catalogue full of single-use entries, which is [[ADR-011 — Store Reusable Content Only]]'s stated failure mode rather than a new one.

**`header` staying static keeps [[ADR-162 — Channel Rendering and Artifacts]] point 1 intact.** Subject and preheader live in a module *because they are fields of an email*. Making them catalogue content would have asserted that they are something else — a reusable communication unit in [[ADR-012 — Content Records Represent Communication Units]]'s sense — which is exactly what a subject line written for one send is not.

**Known cost, accepted:** `cta` and `header` copy stays invisible to the affinity profile permanently. Nothing is lost that the profile could have used, because neither carries a topic.

**2. "Machine ready" is a third assertion axis on the content record: a manager-set flag answering *may a machine pick this without a person deciding?*.**

It is stored on the record, set by a person, and read by the decision engine. It is not merged with either existing axis:

| Axis | Answers | Set by |
|---|---|---|
| `status` (`active` / `inactive`) | may this record be newly selected at all | a person |
| channel readiness | may it go out on this channel | a person ([[ADR-174 — Channel Readiness Is Asserted, Not Computed]] point 1) |
| **machine ready** | **may a machine pick it without a person deciding** | **a person** |

A record can be active, push-ready and *not* machine-selectable — a piece that is legally sensitive, time-bound, or meant for one audience only, which a person must place deliberately. There is no ordering between the three facts and none of them implies another.

**It is a record-level fail-closed flag, and that is what distinguishes it from `candidate_filter`.** The filter is the slot's statement of what it wants; this is the record's statement of whether it may be taken, binding on every slot at once and on slots written by people who have never heard of this record. Expressing the same refusal as a filter would require every slot author to remember it, which is a guarantee that holds until the first one forgets.

**It is asserted, not computed**, for the reason in Context: the exclusions it expresses are intent, and intent is not visible in the `content` blob.

**It governs the decision engine, not authorship.** This is consistent with [[ADR-082 — AI May Recommend but Not Publish]] and with [[ADR-176 — A Negative Decision Outranks a Positive One]] — a negative assertion on the record outranks any slot's positive selection — and it is narrower than either. It says nothing about who may draft a record, and nothing about what a person may place by hand.

## Consequences

### Positive

- **The affinity profile gains the one field set that was actually missing from it.** `hero` is editorial copy about a subject and has never been categorisable. Point 1 takes the coverage proposal's real prize without paying for it in one-off catalogue rows.
- **The catalogue keeps its meaning.** [[ADR-011 — Store Reusable Content Only]] stops being a rule that the module model quietly pressures, and the test in point 1 gives a future module author something to apply rather than a precedent to copy.
- **A decision about a *field* now has a stated test rather than a stated list.** The next module to be written is classified by asking whether its copy carries a topic, not by looking at what `hero` does.
- **The engine gains a refusal it can trust.** Point 2 gives the decision layer a fact that means *a person considered this and said no to automation*, which nothing in the model could express before — `status = "inactive"` withdraws a record from everything, and there was no way to withdraw it from machines alone.
- **Three axes stay three facts.** The `status` enum does not grow, `candidate_filter` does not acquire a convention, and the axis that governs machines is readable on the record rather than distributed across every slot.
- **The flag composes with the filter surface that already exists.** [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]] point 1 makes system axes further axes in one filter surface, so *"show me active, push-ready records that are not machine-selectable"* needs no new narrowing mechanism.

### Negative

- **Flipping `hero` to `cms: true` is a manifest change *and* a data migration, and the direction is unusual.** Rendering branches on `manifest.cms` (`backend/app/rendering/service.py:162`) to decide whether variables come from `module_data` or from a content record, so the flag **orphans every existing hero `module_data` blob** the moment it flips — the data is not converted, it stops being read. Migrating it means **existing `module_data` must become content records**, and `ContentRecordDB.title` and `ContentRecordDB.brand_id` are both NOT NULL (`backend/app/content/db_models.py:15`), so each one needs **a title and a brand invented for it**. A title is an editorial act, not a backfill expression. `header` and `cta` need no migration at all, because nothing about them changes.
- **A hero is now two objects where it was one.** A manager who typed a headline into a module now selects a record, and the everyday case — a headline written for this campaign and no other — is the case [[ADR-011 — Store Reusable Content Only]] says should *not* become a catalogue row. The override layer is what absorbs it ([[ADR-178 — Scope of the Correction, Not Location of the Manager]] point 2), and that is a workflow cost paid on the most prominent module in an email.
- **A third state axis is a third thing a manager holds in their head**, on a record screen that [[ADR-174 — Channel Readiness Is Asserted, Not Computed]]'s Negative already noted grows a section per channel. The first support question this produces is someone asking why an active, ready record is never chosen by a slot.
- **Point 2 is new state on the content record and this repository has no Alembic.** Tables come from `create_all` plus hand-written `backend/scripts/migrate_*.sql`, so the column is a file somebody writes, reviews and runs in the right order — and the backfill value is a judgement rather than a default (see Notes).
- **The flag is fail-closed in shape and fail-open in the code that exists.** Both strategies filter candidates with `ContentRecordDB.status == "active"` and nothing else (`backend/app/decision/strategies/top_score.py:52`, `backend/app/decision/strategies/recipient_top_score.py:89`). A new axis that each strategy must remember to apply is a fence that the next dropped-in `.py` walks past, which is the same criticism point 2 makes of `candidate_filter`, arriving one layer down.
- **The catalogue's coverage hole is narrowed rather than closed, permanently and by choice.** Envelope and CTA copy will never feed the affinity profile, so anyone reasoning about coverage from this record has to know that the missing signal is deliberate rather than pending.

## Notes

- **This is not a supersession and no ADR's status changes.** Nothing above reverses a Decision section. [[ADR-162 — Channel Rendering and Artifacts]] point 1 is kept intact by point 1 rather than narrowed by it, and [[ADR-011 — Store Reusable Content Only]] is applied rather than amended. This repository has had exactly one supersession ever — [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] over ADR-001, on 2026-09-12 — and this is deliberately not a second.
- **A dated addendum is owed on [[ADR-174 — Channel Readiness Is Asserted, Not Computed]], and it is reported with this record rather than applied here.** That record's point 1 names two axes and argues that they must not be merged; a reader will reasonably take two to be the set. Point 2 above adds a third to the same object for the same reason, which is an extension of that argument rather than a contradiction of it — so an addendum, not a supersession, per the pattern ADR-101 and ADR-003 established. The text is in the report accompanying this record, per the rule that a new record does not edit an accepted one.
- **This record complements [[ADR-177 — A Field Is Defined Once, Required Per Module]] and deliberately does not extend it.** That record's own Notes drew the line: questions 1.8 and 2.9 are decisions about **content records**, not about the field model, and were excluded from it for that reason. ADR-177 governs what a field *is* and where its definition lives; this one governs which modules read a record at all, and what a record says about being taken. They share an interview and nothing else, and folding either into the other would produce a record about two objects.
- **`cms` is a boolean and question 1.8 is the first of two places the interview found it too coarse.** The second is the optional heading a slot-bound module needs — *"this might be of interest"* — which must hide when the slot hides and therefore cannot be a separate module, but has no way to be a hand-typed field on a CMS module. The storage already permits it, since the `CHECK` on `module_instances` constrains only the two foreign keys and `module_data` may sit beside a `decision_slot_id`; the renderer ignores it. Logged as a gap in `docs/backlog.md`, not decided here, and point 1 neither creates nor fixes it.
- **The decorative class is presently empty in code, so point 1 governs it at creation rather than changing anything today.** `storage/modules/email/` holds six manifests — `header`, `hero`, `cta`, `img_left`, `img_right`, `single_stack` — and there is no divider. The section-heading module question 1.3 established as missing is *structural punctuation dividing an email into areas*, in the same family as a divider; the test in point 1 classifies it static when somebody writes it, which is the test being applied rather than a second decision.
- **Machine-ready is a flag, not a facet, and the two must not be conflated.** [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]] governs axes a manager declares for **finding** records and point 6 keeps them structurally out of the decision engine. Machine-ready is the opposite on both counts: it is declared by this architecture rather than by an adopter, and its whole purpose is to reach the engine. It appears in the filter surface as a system axis, which point 1 of that record already provides for.
- **Deliberately not settled: the flag's default, and the backfill value for existing rows.** A fail-closed flag that defaults to selectable is fail-open on the day it ships, and a fail-closed default silently empties every slot's candidate set until somebody goes through the catalogue. Both are defensible and the choice belongs with the migration, which is where the record count is known. It is named here because getting it wrong in the open direction is precisely the failure the flag exists to prevent.
- **Also not settled: whether an integration may assert machine-ready.** [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] point 4 gives channel readiness a machine path through the approval inbox's held actions, so the machinery exists and the question is live. A machine marking its own output machine-selectable without that hold would be self-certification of the kind [[ADR-082 — AI May Recommend but Not Publish]] refuses. Point 2 says the flag is manager-set and no machine path exists today; which shape it takes if one is wanted is left to the record that decides it.
- **`docs/playbook-strategy.md` carries the 2026-09-27 decision-log entry behind this record**, under *Variant Editor Design Interview (ADR-177) — interview closed*, whose point 3 names *"a record for catalogue binding plus the machine-ready axis"* among the three ADRs still owed. This is that record. The entry's heading names only ADR-177 because these records had not been written when it was logged; nothing here departs from the entry.

## Addendum 2026-10-04 — a field may be typed in the module, beside the content

Prompted by building task-223, which asked *"How should a catalogue module carry one hand-typed field (the optional heading) beside its content fields?"* The user's answer, *"Per-field source"*, closes the gap the fourth Note logged: `cms` is a boolean, point 1 made it decide whether *all* of a module's fields come from the catalogue or from `module_data`, and a boolean cannot express a mixture.

**Why a mixture is needed.** [[Variant Editor - design interview]] question 2.6 (2026-09-26) asked for an optional heading over a slot-bound module — *"this might be of interest"* — that must not render when the slot finds nothing. A separate heading module cannot do that: it would float above nothing for exactly the recipients [[ADR-086 — Decision Slots Fail Gracefully]] protects. The heading belongs to the slot-bound module.

**The decision.**

- **`cms` still says whether a module is catalogue-bound. Per field, `source` defaults to the content; `source: "module"` marks a field typed in the module itself.** Its value is stored in `module_data`, which the `CHECK` on `module_instances` already allows beside a content record or a slot. The module's other fields still come from the content record or the slot's pick.
- **`source` is declared per *(module, field)* in the manifest, like `required`** ([[ADR-177 — A Field Is Defined Once, Required Per Module]] point 4), and not in `fields.json`: where a value comes from is a property of the module that uses the field, not of the field.
- **A module-sourced field renders only when its module renders.** A slot that finds nothing hides the module, heading included ([[ADR-086 — Decision Slots Fail Gracefully]]).
- **A module-sourced field is never overridden.** It is the module's own and is edited directly; overrides stay for catalogue values ([[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]], which superseded ADR-178).
- **First use: an optional `section_heading`** on email's catalogue modules that sit in the body — `img_left`, `img_right`, `single_stack` — defined once in `fields.json` per ADR-177.

One option was rejected: a built-in optional heading on slot-bound modules only, rendered by the email renderer. It was the smallest change, but it was a special case that only email and only slots would get.

Point 1 is unchanged. A hand-typed heading carries no topic, so keeping it out of the catalogue applies point 1's test. It does not make an exception to it.

## Addendum 2026-10-05 — Machine ready: its starting value, and only people set it

Prompted by task-282, which found that machine ready (point 2) had been decided and never built. The user decided the points below on 2026-10-05 in the task-282 design interview, one question at a time. They settle the two questions the Notes left open: the flag's default and backfill, and whether an integration may set it. Where each part lands in the code is in [[Channel Readiness - final design pass]].

**1. Starting value.** A new record starts **not** machine ready: it fails closed, as point 2 says. Existing records start machine ready, set by the migration, because slots pick them today; turning them all off would silently empty every slot. The demo seed marks its slot content machine ready.

**2. Only a person may turn it on or off.** An integration's attempt is refused, not held. The flag is the human gate on what machines may pick, so a machine setting it, even through the approval inbox, would be the machine approving its own access. This is the same "people only" shape as the second addendum of 2026-10-02 to [[ADR-150 — Tenancy and Access Model]], which refuses a machine credential on every settings write. Turning it off is people only too, so that one rule covers the flag.

This is where machine ready parts from channel readiness. An integration may remove a channel readiness mark directly and may ask, through the approval inbox, to add one ([[ADR-174 — Channel Readiness Is Asserted, Not Computed]]'s addendum of 2026-10-05, point 5). It has neither path for machine ready.

**3. The decision engine reads it,** together with channel readiness. A record is a slot candidate only if it is machine ready and marked ready for the slot's channel ([[ADR-174 — Channel Readiness Is Asserted, Not Computed]]'s addendum of 2026-10-05, point 2). Both strategies and the read-only candidate count now draw on one shared `candidate_query` (`backend/app/decision/strategies/base.py:176`), which today filters on `status == "active"` and the sending brand only (`base.py:203-209`); the line numbers in the fifth Negative are from before that query was shared.

Nothing above changes this record's Decision section.

## Addendum 2026-10-15 — the first use of a module-typed field is withdrawn

Prompted by [[ADR-198 — The Email Block Set Is Seven Blocks, Square Images and Text Links]] (queue task-371). Nothing above changes this record's Decision section.

- **The mechanism of the addendum of 2026-10-04 stands.** A catalogue-bound module may still declare a field with `source: "module"`, typed in the module itself.
- **Its first use is withdrawn.** ADR-198 point 5 takes `section_heading` off the image blocks, and its Headline block takes the role. Existing values stay in `module_data` and no longer show.
- **The retired Single Stack still carries it.** Its manifest, `storage/modules/email/single_stack.json`, keeps `section_heading` with `source: "module"`, and the block renders it unchanged (ADR-198's addendum of 2026-10-15, point 5). It is now the only manifest that declares `source: "module"`. The tests of the mechanism now use Single Stack.
- **The concern behind the 2026-10-04 addendum is accepted as a cost.** That addendum kept the heading inside the module because a separate heading module "would float above nothing for exactly the recipients [[ADR-086 — Decision Slots Fail Gracefully]] protects". ADR-198's Headline block is such a separate module, and ADR-198 accepts this in its Negative: when a slot finds nothing, the module below is hidden and a Headline above it still shows.
- **The Headline block is `cms: false`.** The fifth Note expected a section-heading module to be classified static by point 1's test.

## Related ADRs

### Depends On
- [[ADR-011 — Store Reusable Content Only]]
- [[ADR-013 — Content Reference Instead of Content Copy]]
- [[ADR-080 — Human-governed Taxonomy Before AI Selection]]
- [[ADR-082 — AI May Recommend but Not Publish]]
- [[ADR-162 — Channel Rendering and Artifacts]]
- [[ADR-174 — Channel Readiness Is Asserted, Not Computed]]
