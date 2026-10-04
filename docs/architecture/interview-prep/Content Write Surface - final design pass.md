---
status: decided
date: 2026-10-04
---
# Content Write Surface — final design pass

**Status: decided, 2026-10-04 (task-274), with the user, one question at a
time. Nothing here is built yet. The work is filed as task-275 to task-282.**

The React content screens could find and show a record but not write one. The
only React path that changed a record was the variant editor's per-field
"Change *field* in catalogue" (task-257). The user asked on 2026-10-04 whether
the edit part had been skipped. It had not been decided against; it had never
been filed. This pass settles how the record page writes a record, before
anything is built — the same step [[Campaign Write Surface - final design pass]]
took for the composer.

## Governing records, and what was already decided

- [[Manager Workflow - design interview]] (MW), not reopened:
  - **Q4:** the content screen is "the primary authoring surface and stays
    full-featured"; the composer's edit-in-place is "an accommodation".
  - **Q2:** labelled sections down the page, every channel always visible,
    collapsed by hand, not tabs. Fields in the manifest's declared order.
  - **Q3 and Q3b:** readiness is asserted by the manager per channel.
  - **Q6:** whatever the screen can do, the JSON plane must also do.
- [[Variant Editor - design interview]]:
  - "a catalogue edit being visible to other campaigns is the point of a
    catalogue, not a hazard … the hazard is … silence about reach";
  - a catalogue edit does not reach a send until someone publishes.
- [[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]]
  governs the composer only. On this screen, changing the catalogue is the intent.
- [[ADR-177 — A Field Is Defined Once, Required Per Module]] point 4: nothing is
  required at catalogue level.
- [[ADR-080 — Human-governed Taxonomy Before AI Selection]]: humans define the
  scoring. Its addendum of 2026-10-04 records decisions 4 and 5 below.
- [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]]: categories
  feed the interest profile, and findability is facets' job.
- [[ADR-128 — Version Content for Auditability and Restoration]]: a version is
  what a send used.

## The API, verified 2026-10-04

The write routes exist, all in `backend/app/content/router.py`:
- **create:** `POST /`;
- **edit:** `PATCH /{id}`, which merges by channel group and checks If-Match;
- **status:** `PUT /{id}/status`;
- **delete:** `DELETE /{id}`;
- **categories:** assign with `POST /{id}/categories`, remove with
  `DELETE /{id}/assignments/{aid}`;
- **publish:** `POST /versions`;
- **duplicate:** `POST /{id}/duplicate`.

Two corrections to task-274's own text. First, on delete, the block that
`force` cannot lift is `ContentRecordHasHistoryError` (slot picks and
overrides exist). The removable kind is `HasRelationsError` (assignments,
versions and module links). Second, `PATCH` cannot change status; that is
`PUT /{id}/status`.

## Decisions

1. **Save model: autosave on blur, with the version check** — the editor's
   D1. Each field saves when it loses focus, through `PATCH` with its channel
   group and `If-Match`; a stale save shows on the field with "load their
   version". The publish gate is what keeps sends safe.
2. **Reach: a passive line above the fields, no confirmation.** "Edits here
   change this record for N unsent campaigns; sends use the published
   version", linking to "Used in" (task-267). A prompt on every field would
   train people to click through it.
3. **Publish: the composer's notice and one-click Publish (D5) at the top, and
   a compact read-only version list below** (number, who, when; each openable).
   No restore or compare for now. ADR-128 names restoration; deferring it is
   the user's choice, not a reading of the ADR.
4. **Category scores are whole numbers from 1 to 10, enforced for every
   caller.** The API, the Jinja form and the CSV import refuse anything else
   rather than clamping. Existing rows outside the range are reported for a
   person and never changed silently. (ADR-080 addendum.)
5. **Categories are edited in place.**
   - Each assignment's score is a 1–10 choice changed in place, through a small
     new route, so the record never drops out of the category mid-change.
   - Remove per row; add with the picker's hierarchy dropdown.
   - One line under the heading: "Categories build each recipient's interest
     profile. For finding content, facets will follow."
   - No creating categories on this screen. (ADR-080 addendum.)
6. **Create: a small dialog with Title (required) and Description**, which
   creates the record and lands on its page, where fields autosave. The Jinja
   form's required `headline_medium` is not carried over (ADR-177 point 4).
7. **Scope: status and duplicate now; delete waits for task-117** (whether the
   catalogue ever hard-deletes), so React does not settle that question by
   building the button. Deactivating is how a record is retired meanwhile.
8. **Per-channel readiness and the machine-ready flag are a separate task
   (task-282).** The record page leaves a placeholder in each channel section.
9. **The defects found are filed as bugs ahead of the build** — D3's pattern:
   - unaudited content writes (task-275, against [[ADR-153 — Audit and Accountability]] point 4);
   - `GET /content/fields` sorted by name rather than declared order
     (task-276, against MW Q2);
   - `GET /content/{id}/versions` answering `[]` instead of 404 (task-277).

## Where each part lands

| Part | Server | Client | Task |
|---|---|---|---|
| Field order | `catalogue_fields` in declared order | sections group `/content/fields` by `channel` | task-276 |
| Audit | an event for create, status, delete, assign, score, unassign | — | task-275 |
| Version list | `GET /{id}/versions` answers 404 outside the brand | read-only list | task-277, task-279 |
| Score range and in-place change | refuse outside 1–10 everywhere; list out-of-range rows; new score route | — | task-278 |
| Record page | existing `PATCH`, `PUT /status`, `POST /versions`, `/duplicate`, `/unsent-campaigns` | `ContentDetail.tsx`: sections, autosave, reach line, publish notice, versions, status, duplicate | task-279 |
| Categories section | task-278's route plus assign and unassign | `CategoryChoice`, in-place score, note | task-280 |
| Create | `POST /` | dialog on the Content list | task-281 |
| Readiness | model, migration, approval path (task-206) | a mark per channel section | task-282 |

**Deliberately not touched:**
- the composer's catalogue act (ADR-186);
- the Jinja content screens, which keep working on the same services until
  they are retired, delete included;
- the image picker (task-91, task-112);
- facets (task-207);
- category creation;
- restoring old versions.

## What could break

- **A status change makes an open editor's version token stale.** The status
  route takes no token but bumps `updated_at`. The record page must refetch
  after a status change, or the next field save is refused as somebody
  else's (task-279).
- **Enforcing the score range can refuse a CSV import that used to clamp.**
  That is the intent, but someone's import file may need fixing.
- **Push's empty-means-absent rule** (`without_empty_presence_fields`) must
  survive autosave: clearing a push field removes the key rather than storing
  `""`.
