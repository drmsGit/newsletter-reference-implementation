---
type: adr
status: accepted
topic:
  - architecture
  - decision
  - personalization
created: 2026-06-01
modified: 2026-10-11
source:
  - interview-2026-06-01
depends_on:
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
enables:
  - "[[ADR-086 — Decision Slots Fail Gracefully]]"
---


## Status

Accepted

## Context

Dynamic areas may require one content item or multiple content items.

Examples include one personalized hero or three recommended content blocks.

## Decision

A Decision Slot may resolve one or multiple Content Records.

The slot must define limits such as:

- minimum items
- maximum items
- allowed categories
- excluded categories
- allowed content types
- optional fallback content

## Consequences

### Positive

- supports flexible personalization
- works for single and multi-content modules
- keeps dynamic selection structured

### Negative

- slot configuration becomes more important

## Addendum 2026-10-11 — "show up to" is built: several picks repeat the slot's module

**What prompted it.** task-109. Verified 2026-10-11: the maximum-items limit
named in the Decision above exists as `DecisionSlotDB.max_results`
(`backend/app/campaigns/db_models.py:139`). It is stored, created, duplicated
and shown, but nothing reads it. `StrategyResult`
(`backend/app/decision/strategies/base.py:10-15`) holds one record. Both
strategies build a ranked candidate list and keep only the first.
`DecisionResolutionDB` (`backend/app/campaigns/db_models.py:149-180`) holds one
content record per row, and readers take the latest row. Rendering takes one
pick per module (`resolve_content_for_module` in
`backend/app/rendering/service.py`, `_pick_for_slot` in
`backend/app/rendering/frame.py`). Nothing deduplicates across slots. So every
slot resolved exactly one record, whatever this record allows. The design
sources are [[Variant Editor - design interview]] question 1.6 (*"a queue of
next content"*, *"show up to 3 content records"*), which left open whether the
queue is a rank column or some other shape, and the 2026-10-09 addendum to
[[ADR-176 — A Negative Decision Outranks a Positive One]], under which a slot
whose pick is already bound by hand takes its next ranked pick. That is
task-220, and it waits on this. The playbook's 2026-09-27 entry already named
`max_results` as dead configuration. No later decision-log entry stands behind
this addendum.

**Decided with the user on 2026-10-11**, one question at a time:

1. **Several picks render by repeating the slot's module**, once per pick, best
   first, stacked where the module sits. No new templates. Each copy carries its
   own content id, so link tagging and click attribution credit the right
   record. If fewer are found, fewer are shown. If none are found, the module
   hides as before ([[ADR-086 — Decision Slots Fail Gracefully]]). List-style
   modules that hold several records in one block are not part of this.
2. **"Show up to" is 1–5.** Whoever may edit the slot can change it after
   creation. Until now it could be set only at creation, and it was not shown. A
   push slot is always 1, because a push is one notification (`push.json`
   `max_modules` 1). **There is no minimum and no fallback.** The minimum items
   and fallback content listed in the Decision above stay unbuilt.
3. **No article twice within one email, between slots.** At send, slots are
   resolved in module order. A slot further down skips records that an earlier
   slot already picked for that recipient, and takes its next ranked candidates
   instead. Within one slot a record is never picked twice: a record in two
   categories counts once, at its best row. Hand-bound versus slot (*human beats
   system*) stays with task-220. It is built next on the same mechanism, with
   its own design pass.

**Technical shape, set in the final-design pass.** Claude stated these points;
they were not put to the user as questions.

4. **Storage.** Resolution rows gain `rank` (1 = first, not null, default 1)
   and `pick_set` (one key shared by the rows of one set; NULL on rows written
   before this, which count as a set of one). One execution writes one set.
   Readers take the latest set: the recipient's own if there is one, otherwise
   the slot's global one, as before. A global (non-personalised) slot's set is
   still kept once and updated in place. When an exclusion from an earlier slot
   changes a global slot's picks for one recipient, that recipient gets a set of
   their own for the slot. It is removed again on a later send where the
   exclusion no longer changes anything, so a stale exclusion set never hides
   the current global set. This settles the interview's open rank-column
   question.
5. **Strategies rank.** A strategy returns its ranked candidates up to the
   limit, as distinct records, skipping excluded ones. `top_score` orders by
   category score, then id. `recipient_top_score` orders by combined score, with
   ties in a random order that the stored explanation discloses
   ([[ADR-085 — Decision Resolution Should Be Optionally Explainable]]). The
   single-pick call stays, as the first of the ranked list.
6. **The delivery record** keeps one pick per rendered copy, with its rank.
   Reconstruction renders the same copies in the same order. Picks are still
   decided at send time
   ([[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]
   point 2). "Show up to" is read from the slot at send time, like the slot's
   strategy and filter. It is not frozen into the snapshot.
7. **Slot statistics count picks (rows)**, so "picks made" includes every rank.

The copies of a repeated module carry no override. A module bound to a decision
slot is never overridden
([[ADR-178 — Scope of the Correction, Not Location of the Manager]] point 5,
already built), so the risk named in [[ADR-040 — Introduce Override Layer]]'s
2026-09-27 addendum, several picks wearing one pinned headline, cannot arise.

**Consequences.**

- Previews make no new picks. Point 3 applies at send, so a preview without a
  recipient can still show one record in two global slots.
- A change to "show up to" after approval changes the length of the email that
  is sent, because the value is read at send time (point 6).
- Resolution rows grow by up to five per recipient per slot.

Nothing here changes the Decision section above.

## Related ADRs

### Depends On

- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]

### Enables

- [[ADR-086 — Decision Slots Fail Gracefully]]
