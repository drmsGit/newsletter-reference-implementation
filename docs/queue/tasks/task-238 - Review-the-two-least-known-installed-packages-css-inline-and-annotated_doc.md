---
id: TASK-238
title: 'Review the two least-known installed packages: css-inline and annotated_doc'
status: To Do
assignee: []
created_date: '2026-10-01 21:26'
updated_date: '2026-10-08 19:11'
labels:
  - backend
dependencies: []
priority: p3
type: chore
ordinal: 208900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🟡 **[Chore] — low priority, one-time provenance check.** The 2026-10-01 dependency sweep found every installed Python package to be an established name except two that deserve one look. **`css-inline` 0.21.0** is a direct dependency (`app/rendering/service.py` imports it) and processes newsletter HTML. It is a Rust-compiled wheel, so what runs is a binary and not readable Python, and it has a small maintainer base. It is real and long-standing, so this is a trust-and-maintenance question and not a name-confusion one: who maintains it, how recently it released, whether it is signed or has a public build pipeline, and whether a pure-Python alternative is worth the cost. **`annotated_doc` 0.0.4** arrives transitively (not in `requirements.txt`, not imported by us) and looks like a FastAPI-ecosystem package; confirm which parent requires it and that the PyPI project links to the expected repository. Also worth one pass when the lock exists (task-235): the frontend names `@exodus/bytes`, `obug`, `@bramus/specificity`, `uri-js-replace`, `cookie-es` and `index-to-position` are unfamiliar but all enter through known parents (jsdom, vitest, openapi-typescript) and are dev-only, so they are the lowest concern.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 For css-inline: maintainer, release cadence, repository and build provenance are recorded, with a keep or replace verdict
- [ ] #2 For annotated_doc: the requiring parent package and the PyPI-to-repository link are confirmed
- [ ] #3 The outcome is recorded on this task; no inventory file is added to docs unless the user asks
<!-- AC:END -->
