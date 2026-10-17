---
id: TASK-372
title: The finished design applied to the React screens
status: To Do
assignee: []
created_date: '2026-10-11 20:44'
updated_date: '2026-10-17 10:41'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 201100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** For the November 2026 presentations (docs/business/PRESENTATIONS-2026-11.md), raised by the user 2026-10-11: "finished react design screens". The design work lives in docs/design/ (CONSTRAINTS.md, the user's DESIGN.md and tokens.css, still being finished). Until now visual design and keyboard accessibility were kept out of feature work on purpose, to be done in their own sessions. This is that session for the screens the demo shows.

**Before starting.** The user brings the final design in; read docs/design/ then. Scope: the screens of the demo flow first (campaigns, variant editor, content, slot settings, preview, deliveries and results, settings). Keyboard defects noted in task notes are collected here.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-12, Diede: the neutral author-led Omnichannel Orchestration Reference phase can use a conventional design system; do not invest heavily in bespoke branding. This narrows the meaning of finished design: readable standard typography/components and a coherent November demo flow, retaining comfortable/compact density, accessible focus/states and labelled system/human semantic cues. No prerequisite custom-a/rr logo work or new identity exploration. task-377 owns the neutral rename and current identity assets; this task still owns demo-screen styling. Existing design studies are reference material, not an adoption requirement.

2026-10-12, from task-377: with the long working title, the shell header wraps the name to three lines at phone width and the header row overflows (the email address runs off screen). A layout matter for this task.

2026-10-17, Diede (design session): the finished design is in docs/design/ and is ready to build from. Nothing of it is built in React: the first attempt of 2026-10-12 was rewound on purpose, and frontend/ has no design changes. Start at docs/design/HANDOFF.md (where everything is, what is decided, what the repo already holds that the design must not change, what the first attempt taught us, the open decisions, and section 11, the gaps against this task). Then look at the images, docs/design/renders/ (index: docs/design/renders/README.md), with the canvas page Three columns open beside the code: https://claude.ai/artifact/HEESqGiNZKeWaqT2d5DatL (private to Diede). A copy of every board and of the component stylesheet is in docs/design/canvas-v2/.

What is drawn. The shell (three columns, collapsible navigation, the person's colour avatar), the foundation, the component library, approvals in full (renders 01 to 12), and every screen of this task's demo flow (renders 20 to 43): campaigns; the variant editor with its record picker and slot settings; the preview sheet; the send steps; content with its record page, categories and the image sheet; deliveries with a stranded send and one recipient's message as sent; decision slots; audiences; recipients; monitoring; the decision history; settings (general, brand profile, users, integrations); sign-in. The palette is Linen, Petrol and Pale Pink, the type is the system font, tokens are docs/design/tokens.css.

What is not drawn: Settings Personalisation, Roles and Brands (same pattern as Users and Brand profiles); the category graph; the dialogs (New record, New audience, Suggest from a campaign, Paste people, New brand profile, the new-key dialog, keyboard shortcuts); the Upload new and Web address tabs of the image sheet; dark and increased contrast for the screens 20 to 43 (the tokens carry both, nothing was rendered); empty, loading, error and forbidden states beyond the shared ones; narrow and phone widths.

Read these before building. (1) The boards are layout proposals drawn from what the React screens contain today; they never decide behaviour, and where a board and the code or an ADR disagree the code wins (HANDOFF section 10). The names, figures and dates in them are invented. (2) Eight layout choices need Diede's yes and are open decisions 13 to 20 in HANDOFF section 9: the editor with the navigation collapsed; Monitoring and the decision history as one column of table (a wide-table exception to the three-column rule); the results table split in two; the preview as a sheet; the send steps with the planned sends listed beside them; the audience arithmetic as a section; settings with a list under the sub-menu; the Records, Categories, Graph switch. (3) The system and human cue has only a draft (a neutral chip with a glyph and a word on each module row, render 21), not an approved design; open decision 11. (4) Density has no control drawn (open decision 1). (5) Several screens are still Jinja; HANDOFF section 8 says where the logic may have to change before the pattern fits, and a change of behaviour is a decision to record first, not a style change.

Not done by the design session, left for this task: density, dark-mode switch, the phone layout (proposal: below 800 px the navigation stacks above the screen and starts collapsed), the icon set that replaces the placeholders, which browsers are supported.

2026-10-17, Diede (design review, later the same day): six structure changes were agreed and the boards, renders and canvas (version 51) redrawn. They are in docs/design/HANDOFF.md section 9 (decisions 5, 16, 19 and 21 to 24). Renders 01 to 11, 21 to 24, 28 to 36, 39, 40 changed; 44 (AI prompts) and 45 (create dialogs) are new.

In scope for this task: (a) the AI prompts get their own Settings entry, General keeps the limits (the provider and default model moved with the prompts; Diede to confirm); (c) the editor has an Open preview button with the p key and the sheet, with no preview group in the details; (e) settings lists are a drill-in (the menu is replaced by a back control, the title with its New button, search and the list); (f) every list header has a New button that opens a dialog, in place of the inline create forms (the dialogs are render 45; New record has none drawn).

Not in this task: (b) search on every list that can grow is TASK-390, because the paged lists need a search parameter on the server; build a search box here only on a list that already searches (Campaigns, Content, Audiences, Recipients). (d) dragging is TASK-391, and only on the preview sheet's module list. The editor's module stack stays non-draggable: the Variant Editor interview (2026-09-25) rejects dragging there and VariantEditor.tsx says so. An earlier answer in the review proposed dragging on the stack; that was wrong and is corrected.

2026-10-17, Diede (design review), correction to (a) above: the AI prompts are a list of records, drilled into like the brand profiles. Column 2 lists the four AI tasks (no New button, no search: they are the platform's own); each record's page holds only that task's model, output mode and prompt with its versions (render 44). The AI provider, the default model, the key status and the limits stay in General, because they are global and cannot be a record in that list (render 33). This replaces the earlier line that the provider moved with the prompts. HANDOFF section 9, decision 23; canvas version 52.
<!-- SECTION:NOTES:END -->
