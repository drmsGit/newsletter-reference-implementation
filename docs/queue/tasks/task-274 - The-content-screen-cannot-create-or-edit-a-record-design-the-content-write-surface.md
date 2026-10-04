---
id: TASK-274
title: >-
  The content screen cannot create or edit a record: design the content write
  surface
status: To Do
assignee: []
created_date: '2026-10-04 18:07'
labels:
  - frontend
  - backend
  - needs-adr
dependencies: []
type: decision
ordinal: 300040
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Raised by the user 2026-10-04 while trying the React client: "did we skip the edit part in content or is this part of the tasks queued?" Neither. Nobody decided to skip it, and no task existed for it. This task is that gap, as a design task: it needs a final-design pass and an interview one question at a time, like the campaign write surface had ([[Campaign Write Surface - final design pass]]), before anything is built.

**What the React client has today.**
- The Content list (`frontend/src/screens/Content.tsx`) finds records by title or description, status and category (task-268, task-270).
- Content detail (`frontend/src/screens/ContentDetail.tsx`) shows title, description, status, the fields by their label (task-271) and "Used in" (task-267). It is read-only.
- The only React path that changes a record is the variant editor's per-field "Change *field* in catalogue" on a bound module (task-257, [[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]] point 2), together with Publish (design pass D5).

Missing in React:
- creating a record;
- editing title, description, status and the fields on the content screen;
- assigning and unassigning categories with their scores;
- publishing and the version history;
- duplicating to another brand;
- deleting.

The Jinja UI has all of them (`backend/app/templates/content.html`, `content_detail.html`; handlers `content_create`, `content_edit`, `content_set_status`, `content_delete`, `content_duplicate` in `backend/app/frontend/router.py`).

**Why it fell through.** `docs/react-screen-inventory.md:54` lists content list and detail in the SPA's core loop, with `PATCH /content/{id}` and its merge rule (inventory B19) available. The design work went to the campaign write surface instead; the design pass's D4 put it "ahead of category detail and facets". task-267's own description assumed "the content screen work", but that work was never filed.

**The API is largely there**, all in `backend/app/content/router.py`:
- `POST /` (`:294`), `PATCH /{id}` (`:200`, merge, the one to use), `PUT /{id}` (`:167`, replaces the whole dict; not for the client, B19), `PUT /{id}/status` (`:251`), `DELETE /{id}` (`:268`);
- `POST /{id}/categories` (`:332`) and `DELETE /{id}/assignments/{assignment_id}` (`:547`);
- `POST /versions` (`:371`, publish) and `POST /{id}/duplicate` (`:477`);
- the field list by channel through `GET /content/fields`, labelled since task-271.

Verify each against the code at the start: route shapes, the If-Match version token on PATCH (task-257), and brand scoping.

**Decisions this needs, to be put to the user one at a time:**
1. **Save model.** Autosave on blur, as the variant editor does (D1), or an explicit save? Editing the record here *is* a catalogue edit, unlike the composer where an override is the default (ADR-186).
2. **Reach.** Does an edit here show "used by N unsent campaigns" before saving, as the composer's catalogue act does (ADR-186 point 8, task-224), now that "Used in" sits on the same page (task-267)?
3. **Publish.** Same notice-plus-button as the editor (D5), or a fuller version history on this screen?
4. **Fields by channel.** Email and push fields come grouped from `GET /content/fields`. How a record that is "not prepared for push" differs from one "prepared with nothing" must survive: the empty-field rule `without_empty_presence_fields` (inventory B18) and [[ADR-174 — Channel Readiness Is Asserted, Not Computed]].
5. **Categories and scores.** This screen is where categories get *assigned*. The bind picker only reads them, and per the ADR-175 addendum of 2026-10-04 findability labels belong to facets. Should the screen say what categories are for, the affinity profile ([[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]]), so they are not used as tags? Score entry: free 1–10, or presets?
6. **Create.** Which fields are asked up front? Nothing is required at catalogue level ([[ADR-177 — A Field Is Defined Once, Required Per Module]] point 4).
7. **Delete and duplicate.** Are both in scope now? Delete has a soft block when relations exist (`ContentRecordHasHistoryError`; task-117 notes nothing in the catalogue is hard-deleted).
8. **What is deliberately not here:** the image picker (task-91, task-112), facets (task-207), the machine-ready flag (ADR-179 point 2, unbuilt).

Record architectural answers through the adr-author agent; screen decisions go in a final design pass (a new file, or a section of the campaign write surface pass). Then propose the build tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A design session settles the content write surface (save model, reach, publish, fields by channel, categories and scores, create, delete and duplicate), recorded in an ADR or addendum where architectural and in a final design pass otherwise
- [ ] #2 Build tasks are proposed from it, none started
<!-- AC:END -->
