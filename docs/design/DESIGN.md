---
type: reference
status: draft
created: 2026-10-10
---

# Manager app design: direction and tokens

**Status: not final. The direction is correct, the values and the drawn components are not.** This page records what the design session agreed on 2026-10-10 and what it left open. Nothing here is a spec to build from yet. It is checked against [[CONSTRAINTS]] before anything is built, and conflicts are settled first.

**Update 2026-10-12:** the type, the screen layout and the visual reference changed. See the last section, "Update 2026-10-12: three columns and Apple criteria". Where it disagrees with the text above, the update wins.

Files in this folder: `CONSTRAINTS.md` (what the code allows, written by the repo), `DESIGN.md` (this page), `tokens.css` (the tokens, same `--brand-*` names as `frontend/src/index.css`; the v2 values since 2026-10-12), `HANDOFF.md` (everything a session needs to build v2), `canvas-v2/` (a snapshot of the v2 canvas boards and the component library), `renders/` (those boards as images, with an index).

The visual reference is the design canvas "Approvals redesign" in Claude Design, page "Three columns" (since 2026-10-12). It replaces the earlier canvas "Tarrow Design System", which is retired together with the name. It is a look reference only.

## How to use this in a code session

The design decides the look. The repo decides behaviour (CONSTRAINTS, "The split"). So:

- A code session may change frontend styling to follow this page. It never changes backend code, functions, ADRs or API contracts to make a screen match a mock-up.
- When a mock-up and the code or an ADR disagree, the code wins. Stop on that element, report what the mock-up shows and what the code says, and ask. Do not invent data, fields or endpoints.
- All sample content in the canvas (brand, people, ids, counts, percentages, scores) is invented. The product name comes from `product.json`, never typed into code.

## Scope

In: the manager app's look (tokens, components, page patterns). Out, deliberately: the emails (their visual language, brand slots, header and footer modules, fixed legal footer), push, the unsubscribe page, the older Jinja screens. Email is a separate design job with its own limits (CONSTRAINTS section 2). The manager app is one palette per install, not per brand.

Layout and keyboard accessibility are a later session of their own (CONSTRAINTS). This design does not add polish screen by screen.

## Direction (agreed)

A calm instrument. The UI exists so a person can see what the system did and why, and change it cheaply.

1. **Evidence before decoration.** Numbers, reasons, timestamps and identifiers are the content. No illustration, gradients or emoji.
2. **The system speaks quietly, but distinctly.** Anything a strategy, proposal or AI chose carries one marker (half-filled circle) and one colour (teal), inline and small. It must still be distinguishable, because some adopters will run mostly on system proposals.
3. **Humans pin.** An override is a pin, visible in one colour (ochre) and cheap to make. It shows what the system would have picked. Friction depends on scale or anomaly, not on category.
4. **State is never colour alone.** Every status pairs a label and a shape with its colour. Teal and ochre must differ in greyscale.

Also agreed: the system font (SF Pro on Apple devices) with the system monospace for ids and counts (changed from IBM Plex Sans and Mono on 2026-10-12); a comfortable default density with a compact option (the density feature stays); keyboard shortcuts are discoverable through React Aria (`?`, Alt, Ctrl) and are not printed on buttons.

## Settled and open

| | State |
|---|---|
| Direction: calm, flat, evidence first | Settled |
| System in teal, human in ochre, status never by colour alone | Settled in principle, values open |
| Density: comfortable and compact | Settled that it stays, token values open |
| Type: system font and system mono | Settled 2026-10-12 (replaces Plex) |
| Palette values, radii, spacing | Not final |
| Dark mode | Proposal. It does not exist today and needs a decision |
| How many tokens | Open. 9 exist, about 30 are proposed. CONSTRAINTS says the app's palette is meant to stay small |
| Component designs | Not final (see below) |
| Page layout and composition | Not decided. See "What the screen explorations showed" |

## Identity (proposed, round 06, not adopted)

Provisional direction from Diede: the full wordmark "Tarrow" in IBM Plex SemiBold with the two custom flat-armed r's in normal contexts; the same two r's side by side (rr) as the icon-only symbol where the name cannot fit. Placeholder if the name changes. Not cleared (name or logo). Working choice for now (Diede): the squarer a (a2); a0 and a1 are kept as alternatives. Construction, clear space, minimum sizes, fallback policy and states are in `logodevelopment/round-06/source/identity-principles.md`; discussion in `logodevelopment/LOGO-DISCUSSION.md` [28]. Tokens, components and CONSTRAINTS are unchanged.

## Tokens

`tokens.css` keeps the nine existing names with new values: `--brand-fg`, `-bg`, `-muted`, `-line`, `-accent`, `-danger`, `-font`, `-radius`, `-space`. It adds the groups below. Each addition is a proposal that needs a reason before it ships.

| Group | Tokens | Why proposed |
|---|---|---|
| Surfaces | `-surface`, `-surface-2`, `-line-strong`, `-accent-fg`, `-focus` | Panels, hover, control borders, focus ring |
| System voice | `-system`, `-system-bg`, `-system-line` | Marks what the system chose |
| Human voice | `-human`, `-human-bg`, `-human-line` | Marks pins and waiting on a person |
| Status | `-success`, `-info`, `-danger-bg` and their tints | Approved, sent, failed |
| Type, shape, density | `-font-mono`, `-radius-chip`, `-radius-panel`, `-row-height`, `-row-pad`, `-control-height` | Mono ids, three radii, density |

Type scale: caption 12/16 (uppercase, 0.06em), small 13/20, body 14/22, lead 16/24, h2 20/28, h1 24/32. Space unit 8px. Radii 4 (chip), 6 (control), 8 (panel). Comfortable row 48px, compact 36px. Focus ring 2px, offset 2px, keyboard only.

Accessibility targets from CONSTRAINTS (text contrast at least 4.5:1, or 3:1 for large text; visible focus on everything focusable; nothing by colour alone): the pairs were chosen to meet them, but no contrast check has been run on the tokens yet. That is one of the repo's checks.

## Components

Drawn on the canvas "Components" board: button (primary, default, ghost, destructive, disabled, icon-only), text field and select, table rows (comfortable and compact), status chips, a banner, a module card in three states, a "why this pick" panel, an anomaly prompt.

CONSTRAINTS requires these states for every component: default, hover, keyboard focus, pressed, disabled, invalid, loading where it applies. Not covered yet:

| Component | Missing |
|---|---|
| Button | Pressed and busy (loading) states drawn |
| Text field and text area | Invalid (with error text), disabled, text area |
| Choice (dropdown with label) | Drawn as a plain select only |
| Data table (React Aria grid, paging) | Keyboard focus on cells and rows, paging control, loading and empty states |
| Notices | The `role="alert"` error notice and the quiet status line |
| Checkbox and option lists | Not drawn on the Components board |
| Dialog | Not drawn |
| Tabs | Drawn only inside screen mock-ups |

The status chips, module card, "why this pick" panel, anomaly prompt and the teal/ochre rail are not React Aria components and not in CONSTRAINTS' component list. They express behaviour (explanations, overrides, anomaly checks) that the repo decides. Treat them as look explorations until the behaviour is confirmed by an ADR or interview record.

## What the screen explorations showed

Screens were drawn only to test the look (sign-in, approvals inbox, campaign builder, audience, content, and two flow diagrams). They are references for look, not specs for what a screen contains (CONSTRAINTS). The approvals inbox was drawn three ways:

1. **Calm instrument.** Ruled and boxy. Clear, but boxy.
2. **Soft.** Large radii, grouped widgets, a floating action bar. The grouping into separate widgets helped; the floating bar and translucent surfaces pulled focus away from the work.
3. **Blend.** Flat, ruled, docked actions. Too many lines, too much pressed together, things that cross.

Direction that follows, still to be tested: separate content into a few widget-like groups with space between them instead of one grid of ruled lines; keep surfaces opaque and actions anchored, not floating; fewer dividers; keep the dense table behaviour for real lists. This is a leaning, not a decision.

Screen work is paused until the way of working in this session is clearer. The screen boards stay on the canvas as exploration and are not part of what is agreed.

## What the repo will check (from CONSTRAINTS)

1. Email designs against client limits: not applicable yet, no email design exists.
2. Every screen mock-up against what that screen must contain: not done.
3. The tokens against the accessibility targets: not done.
4. Brand slots against ADR-193: not applicable to the manager app, open for email.
5. Anything that changes a recorded decision is flagged first. Candidates already visible: adding dark mode, adding about 20 tokens to a palette meant to stay small, and any screen content that implies behaviour not yet decided (override reports, category weights, the Original and Overridden flag, AI category suggestions).

## Update 2026-10-12: three columns and Apple criteria

**Decided by Diede.**

- Every screen is three full-height columns: (1) navigation, collapsible to an icon rail; (2) header and list in one column, with no rule between title, filters and list, and with paging and the screen's history link at the foot of the list; (3) details on the light ground (Linen) from the very top, with the action group docked on the same ground. Text in a column starts on one indent (list 20 px, details 40 px). Parts that share a function sit together.
- Screen mapping: approvals = list, details and the decision. Campaigns = list, then variant and channels. Editor = modules list, content selection, preview. Audience = list, then selection rules. Settings = sub menus, then details.
- The type is the system font plus the system monospace. No hosted font files (ADR-171).
- **The palette** (2026-10-17): Diede offered three and asked for one pick or none. Linen / Petrol / Pale Pink was picked: Linen is the ground, Petrol the one action colour, Pale Pink the "you are here" marker of the selected navigation item only. The other two were rejected: neither could carry an action colour at 4.5:1, and both sat on the status hues (gold and rust on waiting amber, burgundy on failed red). Pale Pink is also the failed red's hue, so it is never a status or a surface. The reasoning and the measured figures are in [[HANDOFF]], section 4, with the earlier values for reverting.
- **The initials avatar takes its colour from the name** (added 2026-10-13): hash the name into a number and turn it into a hue, so everyone gets their own colour, the same on every reload. It is the signed-in person's avatar in the navigation foot, replacing the email text above Sign out, and the brand's tile in the collapsed rail. The rule, the per-theme saturation and lightness, the contrast and test vectors are in [[HANDOFF]], section 4; the tokens are `--brand-avatar-bg-s`, `-bg-l`, `-fg-s` and `-fg-l` in `tokens.css`.
- The look follows Apple's desktop criteria, taken from the skill `dickwu/apple-design-skill`. That skill paraphrases Apple's Human Interface Guidelines, and its numbers have not been re-read at developer.apple.com. In practice: a linen ground with white cards, 28 px controls (36 px for the one decision action), capsule status chips, hairlines instead of boxes, opaque surfaces everywhere.

**Drafted by Claude, approved with the whole design.** Diede approved the design as a whole on 2026-10-12 and did not go through these one by one, so revisit any of them if the build shows trouble.

- The split-view composition for approvals (the route stays `/approvals/:id`).
- The colours derived from the three palette colours (tints, text, hairline and field-border values, dark and increased-contrast sets), and no teal "system" voice on approvals.
- `--brand-line-strong` raised so field borders reach 3:1.
- An increased-contrast value set, and dark mode.
- New token names: `--brand-sidebar`, `--brand-selected`, `--brand-shadow`, `--brand-control-height-sm` and `-lg`.
- Placeholder icons, because SF Symbols are licensed for Apple platforms only.
- The editor's preview as a second group in column 3.

**Where the values live.** `tokens.css` in this folder now carries the approved v2 values (system font, the Linen ground, the Petrol accent, dark and increased-contrast sets). The canvas "Approvals redesign" holds the foundation and the component library, and `canvas-v2/` in this folder is a snapshot of it, with `ui.css` as the component library. `frontend/src/index.css` still holds the old placeholder values: nothing of v2 is built in React yet.

**Status of the build.** Not started. A first implementation of the shell and the approvals screen was written on 2026-10-12 and rewound at Diede's request, because the aim of that session was this documentation. [[HANDOFF]] has everything the session that builds it needs: where the design is, what is decided, what the repo already holds that must not change, what the first attempt taught us, what is open, and what may have to change for the screens still in Jinja.

**Content check.** The approvals screens in the earlier canvas showed things the repo does not back: an email "as sent" preview, "Request changes", Pending/Decided/Mine tabs, a density toggle, system-proposed audience numbers, an override rate, a check panel, snapshot ids, A/R key hints on buttons, and a role line for the signed-in user. The v2 screen draws only what `frontend/src/screens/Approvals.tsx`, `ApprovalDetail.tsx` and `docs/react-screen-inventory.md` contain.

**Open: density.** This document settled that the density option stays, but the approvals screen has no such control today, so v2 does not draw it. It needs a place (the navigation foot or Settings) and a decision before it is drawn.

**Update 2026-10-17: the rest of the screens are drawn.** At Diede's request the screens that were missing were drawn in the three-column pattern so the build session has them: campaigns, the variant editor with its record picker and slot settings, the preview sheet, the send steps, content (list, record page, categories, image sheet), deliveries (with a stranded send and the message as sent), decision slots, audiences, recipients, monitoring, the decision history, settings (general, brand profile, users, integrations) and sign-in. They are renders 20 to 43 in `renders/`, boards in `canvas-v2/`, and on the canvas. Each was drawn from what the React screen contains today, not from the Jinja pages. **They propose layout and never decide behaviour.** The proposals that need a decision (the wide-table exception for Monitoring and the decision history, the send steps beside a list, the audience arithmetic as a section, settings with a list under the sub-menu, the editor with the navigation collapsed, a draft of the system and human cues) are open decisions 13 to 20 in [[HANDOFF]] section 9. Still not drawn: Settings → Personalisation, Roles and Brands, the category graph, the dialogs, and dark and increased contrast for these screens.

**Review of 2026-10-17: six structure changes.** Diede reviewed the drawn screens and agreed: (a) the AI prompts are their own Settings entry, a list of records like the brand profiles with one record per AI task, and General keeps the provider and the limits; (b) every list that can grow gets a search box (drawn; most lists need server support, so building it is a separate task); (c) the editor has a Preview button with the P key and the sheet, with no preview group in the details; (d) the module list in the preview sheet can be dragged (a separate feature task; it is the one surface where the recorded Variant Editor decision allows dragging, and the module stack keeps its arrows and Alt+Arrow with no dragging); (e) settings lists are a drill-in, so a long list has the whole column; (f) every list header has a "New ..." button that opens a dialog, in place of inline create forms. [[HANDOFF]] section 9, decisions 21 to 24 (and 5, 16, 19), records them. One reading to confirm: the AI provider and default model stay in General with the limits, because they are global and cannot be a record in a list of prompts.
