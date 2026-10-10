---
id: TASK-301
title: >-
  A visible header and footer in every email: shared structure, per-brand
  content (not the envelope module)
status: Done
assignee:
  - '@claude'
created_date: '2026-10-08 18:26'
updated_date: '2026-10-10 21:22'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200950
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**What the recipient sees at the top and bottom of an email does not exist yet.** Raised by the user 2026-10-08, after task-228.

**Two different things are both called "header". Do not confuse them.**
- **The envelope module.** It is named `header` in code (`storage/modules/email/header.json` and `.html`). It holds the subject and the preheader, both marked `"envelope": true` in `storage/fields.json`. It renders only a hidden preheader span. It is what ADR-086's 2026-10-08 addendum calls the envelope.
- **The visible header.** This is what the recipient sees: a logo, perhaps a navigation bar. It does not exist.

This task is about the visible header and a footer. Whether the envelope module should be renamed so the two stop sharing a name is one of the questions below. It is not assumed.

**What exists today (verified 2026-10-08):**
- No visible header and no footer module. The email modules are `cta`, `editorial`, `header` (the envelope), `hero`, `img_left`, `img_right` and `single_stack`.
- Emails therefore go out with no company details and no unsubscribe link.
- Styling is one `storage/modules/email/brand.css` for the whole deployment, loaded in `backend/app/rendering/service.py:36-44`. It is not per brand, although a deployment has several brands ([[ADR-150 — Tenancy and Access Model]]).
- Nothing holds brand content: no logo, company details, links, or unsubscribe or preference-center address per brand.

**What the user wants covered:**
- A visible header: logo, maybe a navigation bar.
- A footer: company information, links, the unsubscribe link, and possibly a preference-center link.
- How brand-specific content gets in when the structure is the same but the content is not.
- Whether brands may also differ in layout, needing several headers or footers. The user's lean: probably not; "brands have to use the same basic structure".

**Questions for the design session (a starting list):**
- **Kind of thing.** Is the visible header or footer a module a manager places and may leave out, or a fixed frame around every email of a brand? A footer carrying the unsubscribe link is arguably not optional.
- **Where brand content lives.** A per-brand profile (logo, company details, links, addresses) filled into one shared structure is the option matching the user's lean. Per-brand template files is the alternative if layouts differ.
- **The logo needs asset management** (task-112): an asset id, not a typed URL.
- **The unsubscribe link needs its surface first** (task-56): the route, the one-click `List-Unsubscribe` header and the per-brand address. A preference center has no task yet.
- **Styling per brand.** task-94 decided one `brand.css` per deployment. Does a per-brand header or footer change that?
- **Task-228's floor.** It skips a recipient when nothing but the envelope rendered. A visible header and a footer are exactly the decorative modules its addendum deferred: an email holding only those must still count as "nothing to show". This is where the decorative marker gets decided, together with task-108.
- **The name of the envelope module** (above).

**Related:**
- task-56: unsubscribe and double opt-in surfaces; blocks the beta's first send.
- task-94: brand theming.
- task-112: asset management, for the logo.
- task-135: suppression and opt-out reasons.
- task-108: a section-heading module, the other structural module.
- [[ADR-086 — Decision Slots Fail Gracefully]] (2026-10-08 addendum).
- [[ADR-160 — Channel Model and Composition]] (two files per module).
- [[ADR-131 — Email Module Templates Use MJML as Source Format]].

It sits beside task-56 in the queue because both stand between the platform and a real first send. This is a design task: decisions go in an ADR before anything is built.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Decided and recorded: what the visible header and footer are (placed module or fixed frame), where per-brand content lives, and whether brands share one structure
- [x] #2 The unsubscribe and preference-center links, the logo and per-brand styling are each tied to their own task or decided here
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The user, 2026-10-08, added before the design session: even within one brand, several footers may be needed - with an unsubscribe link, without one, with special texts and so on. That may answer the "placed module or fixed frame" question: not a fixed frame. Every email must have a footer, but it is not automatically the same one, unless the footer has dynamic options. So the session weighs:
- several footer variants per brand that the manager chooses between, with a footer always required;
- one footer per brand with dynamic options (unsubscribe shown or not, an extra text).
Open alongside: which emails may go out without an unsubscribe link (a transactional or service email, task-134?), and who decides that.

2026-10-10, design session with the user (one question at a time).

State found first: since task-56 (ADR-191) the rendering frame appends a fixed footer to every marketing email: brand name, unsubscribe link and the List-Unsubscribe header (backend/app/rendering/frame.py around :286-292). Transactional mail gets none. BrandDB holds only key and name. brand.css is still one per deployment. Asset management is still task-112.

Q1, decided: two layers.
- The frame keeps appending what must always be there: the unsubscribe line, extended with the brand's legal details.
- The designed visible header (logo) and footer (links, special texts) are ordinary modules a manager places, so several footer variants per brand are simply several footer modules.
- 'Every email has a footer' is guaranteed by the legal part, not by forcing a module.

Q2, decided: legal details live in a brand profile, and they can differ within a brand. The profile holds several named legal-detail sets with one marked default; a campaign or variant may pick another set, otherwise the default applies. The designed header and footer modules take their content like any module, from content records, which already belong to one brand.

2026-10-10, design session continued. All decisions are recorded in ADR-193, written by adr-author.

- Q3, styling: brands share the same modules, and each brand profile also carries colour and font values applied on top of the shared brand.css at render. How they are applied is open: email clients handle CSS custom properties poorly. Noted on task-94.
- Q4, decoration: a module manifest may declare "decorative": true (the header and the footer; later task-108's section heading). Task-228's nothing-to-show check ignores decorative modules, which answers AC 3 in design.
- Q5, logo: an https URL in the header's content for now, an asset id once task-112 exists. Noted on task-112.
- Q6, naming: the envelope module is renamed from header to envelope, so the visible logo module can be called header. Open for the final-design pass: stored module rows, frames frozen in snapshots and delivery records name 'header'. Either migrate them, or let the readers accept the old name too; a frozen record is what was sent (ADR-183).
- Q7, preference center: parked as its own task.

2026-10-10: AC 3 ('Task-228's floor still treats an email holding only a visible header and footer as nothing to show') was decided here: the "decorative": true manifest flag, ADR-193 point 4. It describes built behaviour, though, so it moved to task-351, whose acceptance criteria state it as 'An email holding only decorative modules and the envelope is skipped as nothing to show', rather than being ticked here unproven.

Design recorded in ADR-193, with an ADR-191 addendum (its footer line is permanent) and back-link, and a playbook entry. Commit 7c70b4e.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The design is decided and recorded in ADR-193. The rendering frame keeps appending the legal minimum to every marketing email: the unsubscribe line plus the brand's legal details from a brand profile, which holds several named sets with a default. The designed visible header and footer are placed modules, marked decorative so they never count as content. Brands share one structure and get their own colour and font. The logo is a URL until asset management (task-112). The envelope module is renamed to envelope. Every open link and asset is tied to a task: build in task-349, task-350 and task-351; preference center task-348; theming task-94. Decided with the user one question at a time; the full suite is green with the records in place.
<!-- SECTION:FINAL_SUMMARY:END -->
