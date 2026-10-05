---
status: decided
date: 2026-10-05
---
# Channel Readiness — final design pass

**Status: decided, 2026-10-05 (task-282), with the user, one question at a time.
Nothing here is built yet. The work is filed as task-283 to task-287, and
task-206 now depends on task-283 and task-210.**

A content record's per-channel readiness and its "machine ready" flag were
decided long ago and never built. Nothing in the code names either. The
Content Write Surface pass (decision 8) split them out. This pass settles what
the earlier records left open, before anything is built.

## Already decided, not reopened

- [[Manager Workflow - design interview]]:
  - **Q3:** readiness is asserted by a person per channel, stored on the record,
    a different axis from `status`. The engine trusts the mark rather than
    inspecting fields.
  - **Q3b:** if a required field is emptied, warn and keep the mark; the send
    catches it. Auto-unmarking was rejected.
  - **Q5 and Q8:** readiness is a filter dimension.
  - **Q6b:** an integration's assertion goes through the approval inbox, while
    a person's is not held.
  - **Q11:** the picker opens on content ready for the channel, and an unready
    record appears marked, not absent.
  - **Q14:** the three states are not ready, ready, and pending action.
- [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] points 1-4, with the
  send-time required-field check (point 3), which is now built.
- [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]]
  point 2: a record-level, fail-closed "machine ready" flag set by a person and
  read by the decision engine.
- [[Variant Editor - design interview]] 2.8: a module-specific gap is warned at
  bind time. 2.9 is the machine-ready toggle.

## Decisions

The architectural ones (1-4, 6 and 7) are recorded in the 2026-10-05 addenda
to ADR-174 and ADR-179.

1. **Storage: one row per record and channel that is marked ready,** with who
   marked it and when. Unmarking deletes the row; the audit log keeps the
   history. A new channel needs no migration.
2. **Machine ready starts off for new records and on for existing ones.** The
   migration sets existing records on, because slots pick them today. The demo
   seed marks its slot content on.
3. **Decision slots need both: machine ready AND ready for the slot's channel.**
   The migration marks today's active records ready for email, so no slot goes
   empty. Push readiness is only ever marked by a person.
4. **The picker and the Content list read readiness in this first build.**
   `GET /content/` gains a "ready for" filter and per-row `ready_for`. The
   picker opens on records ready for the variant's channel, with a switch to
   show the rest, each marked "Not ready for <Channel>". The Content list gets
   a "Ready for" filter.
5. **The warning fires when the record can fill no module of that channel,**
   and says what each kind of module needs. Push: "Marked ready for Push, but
   Notification text is empty". Email: "no email module can use it: Hero
   banner needs Hero headline; image modules need Headline". It is computed on
   the server. A gap for one specific module is the picker's fit note's job.
6. **Only a person may turn machine ready on or off;** an integration is
   refused. The flag is the human gate on what machines may pick.
7. **The Jinja content screen shows readiness read-only;** marking happens in
   the React client. Its stale "readiness has no meaning" text and the test
   pinning it go.
8. **An integration may remove a channel mark directly;** adding one stays held
   (task-206). Until task-206 is built, an integration's attempt to mark is
   refused, so nothing goes through unheld.
9. **A slot also skips a record that cannot fill the slot's module** (decided
   2026-10-05 before task-284, the user's choice of three options). Every
   required field of the module the slot is bound to must be filled in the
   record's **latest published version**, which is what a pick renders, so a
   record never published is no candidate. The check sits in `candidate_query`
   beside the two marks. The mark and its warning are untouched. Nothing else
   checks a slot's pick: the send check skips slot modules, and task-228 only
   skips a recipient whose slots all came up empty. Widening task-228 was not
   chosen now. Recorded in ADR-174's addendum "A slot passes over a record
   that cannot fill its module".

## Where each part lands

| Part | Server | Client | Task |
|---|---|---|---|
| State, migration, routes | readiness table; `machine_ready` column; migration with the backfills; mark/unmark and machine-ready routes; detail fields with warnings; `ready_for` on `GET /content/` | — | task-283 |
| Slots | `candidate_query` requires both marks and a published version that fills the slot's module (decision 9); the count agrees; seed marks | — | task-284 |
| Record page | — | a Ready switch per channel section (who/when, warning); a Machine ready switch by the status | task-285 |
| Picker and Content list | (task-283's filter) | picker opens on ready records, with a switch for the rest; a "Ready for" filter on the list | task-286 |
| Jinja | read-only display; stale text, test and ADR-161-rider comments removed | — | task-287 |
| Integration holds | widen the approval guard beyond sends; add the action and its route entry; no deadline (task-210) | inbox shows it | task-206 |

**Deliberately not touched:**
- the send-time required-field check (built; unchanged);
- the empty-push-field rule `without_empty_presence_fields` (unchanged; only
  its stated reason, the false ADR-161 rider, is corrected);
- facets;
- a variant's own "ready" status;
- what counts as a "thin" slot (MW Q4b, still open).

## What could break

- **Every slot whose records are not marked.** The email backfill covers
  today's active records. A record activated later, or one meant for push,
  must be marked first. Tests that build slot candidates need the marks in
  their fixtures (task-284).
- **The approval guard holds only sends today.** An approvable-route entry
  alone would not hold the readiness route, so task-206 must widen the guard.
  Until then task-283 refuses an integration's mark outright.
- **The migration** must run before any Python edit while the preview backend
  reloads (ADR-181's pending-migration refusal).
