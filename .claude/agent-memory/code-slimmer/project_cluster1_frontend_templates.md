---
name: cluster1-frontend-templates
description: Results of the 2026-08-21 frontend/ + templates/ sweep — what is confirmed live there, so the next sweep does not re-flag it
metadata:
  type: project
---

Cluster 1 (`backend/app/frontend/router.py`, `backend/app/templates/`) swept
2026-08-21. **No dead routes and no orphaned templates exist there.** Verified
mechanically, not by eye — do not re-run this as a "maybe dead" hunt.

**Why:** the cluster looks like a dead-code target (2,927 loc in one file, 65
handlers, 24 templates) but every route and every template is reachable. Two
sweeps spending effort on the same negative result is waste.

**How to apply:** if a future sweep touches these dirs, start from the
*duplication and query* findings below, not from reachability.

Confirmed live, never flag:
- **All 24 templates.** `forbidden.html` is rendered from `backend/main.py`
  (the 403 handler), not from `frontend/router.py` — it is the only one with no
  reference inside `app/`.
- **All 65 route handlers.** Every POST action path appears in a template, some
  built by Jinja string concatenation.
- `POST /ui/audience-groups/{id}/blocks/{id}/edit` — reached only through the
  `block_form(action, ...)` **macro** in `audience_group_detail.html`, whose
  action is built with `~` concatenation. A literal-path grep misses it.
- `GET /ui/audience-groups/{id}/criteria-preview` — reached only from a
  client-side `fetch()` in `audience_group_detail.html`. The only JS-only route
  in the cluster.
- `title` in every TemplateResponse context — consumed by `base.html`'s
  `<title>`, never by the page template. It is not an unused context key.
- Function-local imports of `app.ai.*` in the router are *not* breaking an
  import cycle (`app.ai` does not import `frontend`), but they are a style
  choice, not dead code.

Method that worked and is worth repeating: an AST pass over
`TemplateResponse(...)` calls to diff context keys against template bodies, and
a second pass turning each `@router` path into a regex (`{param}` →
`[^"']*`) matched against all templates at once. Both are in the sweep
transcript; they gave a clean negative in minutes. Watch two false-positive
sources: `**ctx` dict merges hide keys from the AST, and Jinja `~`
concatenation hides paths from literal greps.

Related: [[seams-do-not-flag]], [[review-only-never-edit]]
