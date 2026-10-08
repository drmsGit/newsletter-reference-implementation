---
id: TASK-301
title: >-
  A visible header and footer in every email: shared structure, per-brand
  content (not the envelope module)
status: To Do
assignee: []
created_date: '2026-10-08 18:26'
labels:
  - needs-adr
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
- [ ] #1 Decided and recorded: what the visible header and footer are (placed module or fixed frame), where per-brand content lives, and whether brands share one structure
- [ ] #2 The unsubscribe and preference-center links, the logo and per-brand styling are each tied to their own task or decided here
- [ ] #3 Task-228's floor still treats an email holding only a visible header and footer as nothing to show
<!-- AC:END -->
