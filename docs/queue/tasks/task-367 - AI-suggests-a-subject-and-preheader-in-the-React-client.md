---
id: TASK-367
title: AI suggests a subject and preheader in the React client
status: To Do
assignee: []
created_date: '2026-10-11 20:44'
labels:
  - frontend
  - backend
dependencies: []
type: feature
ordinal: 200700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** For the November 2026 presentations (docs/business/PRESENTATIONS-2026-11.md). The AI subject and preheader suggestion exists only in the Jinja UI: `POST /ui/campaigns/{id}/variants/{vid}/suggest-subject` (`backend/app/frontend/router.py:1425`). There is a JSON route on the campaigns router (`/campaigns/variants/{variant_id}/suggest-subject`, used by `backend/tests/test_ai_budget_period.py`), but the React variant editor offers nothing. This task gives the variant editor the button, shows the suggestions, and lets a person take one into the subject and preheader.

**Related.** task-100 (progress and double-submit protection for AI calls, wanted with this). task-125 (today's suggestion only works for hand-composed campaigns, which collides with decision slots — its decision is needed before the demo shows both). The three new AI abilities wanted for the demo build on this: create and categorise content, translate content, prepare a variant from a topic.
<!-- SECTION:DESCRIPTION:END -->
