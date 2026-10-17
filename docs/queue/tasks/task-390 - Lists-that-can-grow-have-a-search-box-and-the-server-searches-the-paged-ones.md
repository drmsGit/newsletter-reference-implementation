---
id: TASK-390
title: 'Lists that can grow have a search box, and the server searches the paged ones'
status: To Do
assignee: []
created_date: '2026-10-17 10:34'
labels:
  - frontend
  - backend
dependencies:
  - TASK-372
references:
  - docs/design/HANDOFF.md
type: feature
ordinal: 201104
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Raised by Diede in the design review of 2026-10-17 ("most screens are missing a search bar in the list area") and agreed as a design rule: every list that can grow has a search box at the top of its column. The design draws it (docs/design/HANDOFF.md section 9, decision 21; renders 01 to 11, 28 to 36, 39, 40). It is **not** part of TASK-372, because for most of these lists it is not a style change.

**What exists today.** Four screens search: Campaigns, Content, Audiences and Recipients (frontend/src/screens/Campaigns.tsx, Content.tsx, Audiences.tsx, Recipients.tsx, all on the shared SearchBox, with the term kept in the URL as q). The rest have no search, and the manager can only page or filter.

**Why it is separate work.** The lists split in two kinds, and they need different things.
- *Paged on the server* (ADR-185): the approvals list, the decision history, deliveries, decision slots, monitoring and brand profiles. A box that filters the rows on screen would search only the 50 rows of the current page, and say "no match" for something on page 2. Each of these needs a search parameter on its endpoint, with the paging envelope's total counting the matches and the offset starting again at the first match.
- *Not paged:* categories, users and integrations come back as plain lists, so filtering in the client is enough, and Roles and Brands (not drawn) would be the same.

**Open, to settle while building.** Which fields each search matches (a send by its name, a request by its summary, a user by name and address, and so on); the empty-result line of each; and whether adding the term to a list endpoint changes the ADR-185 envelope enough to need a dated addendum on that ADR. The labels drawn in the design ("Find a send by name", "Find a request by summary") are proposals.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The approvals list, the decision history, deliveries, decision slots, monitoring and brand profiles each have a search box that the server answers: the endpoint takes the term, the total and the paging count the matches, and a match beyond the first page is found
- [ ] #2 Categories, users and integrations each have a search box that filters their full list, with an empty-result line
- [ ] #3 A new search term starts again at the first match; the term and the page stay in the URL as on Campaigns and Content
- [ ] #4 Each search says in the task notes which fields it matches, and tests cover a match that is not on the first page of a paged list
- [ ] #5 It is recorded whether the ADR-185 envelope needed an addendum for the search term
<!-- AC:END -->
