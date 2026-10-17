---
type: reference
status: draft
created: 2026-10-12
---

# Design handoff: the manager app, v2 (three columns)

For the session that builds this. It says where the design lives, what was decided, what the repo already holds that the design must not change, what a first attempt at building it taught us, and what is still open. Read [[DESIGN]] (the update at its end) and [[CONSTRAINTS]] with it.

**Status, 2026-10-12.** Diede approved the design ("design is approved"). **Nothing of it is built in React.** A first implementation was tried the same day and rewound at Diede's request, because the aim of the session was this document, not code. Section 7 records what that attempt taught; the code itself is not kept in the repo.

**Rendered 2026-10-17.** The boards were rendered to images, in `docs/design/renders/` (index: `docs/design/renders/README.md`), and every image was looked at. Rendering found three board frames shorter than their content (Foundation, Patterns, States), which clipped it; they are fixed in the canvas and the snapshot. No built screen has been compared with the renders yet, because none is built. **For the queue task, TASK-372, section 11 says what the design covers and what it does not.**

**Screens drawn, 2026-10-17.** Diede asked for the missing screens to be drawn so the build session has them: campaigns, the variant editor (with its record picker and slot settings), the preview sheet, the send steps, content (list, record, categories, the image sheet), deliveries (with a stranded send and one recipient's message as sent), decision slots, monitoring, the decision history, audiences, recipients, settings (general, brand profile, users, integrations) and sign-in. They are 20 to 43 in `docs/design/renders/`, boards in `docs/design/canvas-v2/`, and on the canvas (version 48). Each was drawn from what the React screen contains today, gathered by reading `frontend/src/screens/`, not from the Jinja pages and not from memory. Where drawing needed a layout nobody had decided, the board makes a proposal; those are open decisions 13 to 20 in section 9. **A board is a proposal for layout only. It never decides behaviour.**

## 1. Where everything is

| What | Where |
|---|---|
| The visual reference | The Claude Design canvas "Approvals redesign", page "Three columns": https://claude.ai/artifact/HEESqGiNZKeWaqT2d5DatL (private to Diede; read it with the Artifact tool). Page "First draft" holds the superseded first version and Diede's sticky notes. |
| A snapshot of it | `docs/design/canvas-v2/`: every v2 board as `.dc.html`, `ui.css` (the component library), `canvas.json` (the layout, with Diede's notes). Matches the published version of 2026-10-17 (canvas version 48). |
| The tokens | `docs/design/tokens.css`. Same `--brand-*` names as `frontend/src/index.css`, which still holds the old placeholders until the build. |
| The component library | `docs/design/canvas-v2/ui.css`. It is the prototype's stylesheet, not production CSS. |
| What it looks like | `docs/design/renders/`: 43 images. 01 to 19: approvals in light and dark, every decision state, the foundation, the component library, the patterns. 20 to 43: the demo flow and the other screens. Index and how they were made: `docs/design/renders/README.md`. |
| The status of every decision | [[DESIGN]], the update at its end. |
| What the code and email clients allow | [[CONSTRAINTS]]. |
| What each screen really contains | [[react-screen-inventory]], [[react-migration-inventory]], and the screens in `frontend/src/screens/`. |

The earlier canvas "Tarrow Design System" is retired together with the name. Do not use it as a source: it was drawn from invented content.

## 2. Decided, and what was drafted

**Decided by Diede**

- Every screen is three full-height columns (section 3).
- The type is the system font plus the system monospace. No hosted font files ([[ADR-171 — Nothing Required to Run This Platform Is Commercial]]).
- The look follows Apple's desktop criteria, taken from the skill `dickwu/apple-design-skill`. It paraphrases Apple's Human Interface Guidelines; its numbers were not re-read at developer.apple.com.
- The navigation column collapses to an icon rail.
- Diede liked the hairline borders and the subtle highlights of the first draft, and they stay.
- **The palette** (2026-10-17): Diede offered three and asked for one pick or none. **Linen / Petrol / Pale Pink** was picked, and the other two were rejected, on measured grounds (section 4). Linen is the ground, Petrol the one action colour, Pale Pink the "you are here" marker in the navigation.
- **The initials avatar takes its colour from the name** (added 2026-10-13): hash the name into a number, turn it into a hue, so everyone gets their own colour, the same on every reload. The rule is in section 4.

**Drafted by Claude and approved with the whole design** (Diede approved the design as a whole and did not go through these one by one, so revisit any of them if the build shows trouble)

- The colours derived from the three palette colours (the sidebar, hover and selected tints, the text, hairline and field-border colours, and the dark and increased-contrast sets), each checked for contrast. No teal "system" voice on the approvals screens.
- `--brand-line-strong` raised so a field border reaches 3:1 on every surface.
- An increased-contrast value set that follows the system setting.
- Dark mode (opt-in with `<html data-theme="dark">`; no switch exists in the app).
- New token names: `--brand-sidebar`, `--brand-selected`, `--brand-highlight`, `--brand-shadow`, `--brand-control-height-sm` and `-lg`, and the four `--brand-avatar-*`.
- The split view for approvals, with the route staying `/approvals/:id`.
- Placeholder icons, drawn because SF Symbols are licensed for Apple platforms only.
- The editor's preview as a second group in the details column.

## 3. The structure rule

Three columns, every one running from top to bottom and scrolling on its own.

1. **Navigation.** Always there. One flat level, 28 px rows, 232 px wide, collapsing to a 56 px icon rail. The toggle is the first control. The product name (from `product.json`, never typed), the working brand's logo and the brand switcher sit at the top. At the bottom, the signed-in person's initials avatar (it replaces the email text that stood there) with Sign out under it; the display name is the avatar's accessible name and the email is its hover text.
2. **Header and list in one column**, 380 px (minimum 300). The large title, a count and the filters sit on the list's own surface, **with no rule between them and the list**. What belongs to the list sits at its foot: paging, and the screen's history link.
3. **Details**, flexible (minimum 480), **the light linen ground from the very top**. Groups are white cards. The action group is docked at the bottom **on the same ground**, with a soft fade where content passes under it instead of a rule.

**One indent per column.** Every line of text in a column starts on one vertical line: 20 px in the list (8 inset plus 12 padding), 40 px in the details (24 inset plus 16 padding). A group's title sits above its card on that same line.

**Parts that share a function sit together.** The decision history belongs to the approvals list, so its link is at the foot of the list, beside the pager.

Below about 1,100 px the details wrap under the list; at phone width it is one column at a time.

**Which screen is which pattern**

| Screen (renders) | Column 2 | Column 3 | Decided by |
|---|---|---|---|
| Approvals (01 to 12) | The approvals, with filters | The request and its decision | Diede, drawn in full |
| Campaigns (20) | The campaigns: create form, search, list, pager | The campaign: facts, results, each variant with its modules and decision slots, New blank variant | Diede's pattern; drawn 2026-10-17 |
| Variant editor (21 to 24) | The modules, one row each with its move and remove controls and a cue chip | Brand profile, preview, envelope fields, then the open module's fields. The preview opens as a sheet (24). Drawn with the navigation collapsed to the rail, to give the editor the width | Diede's pattern; drawn 2026-10-17; the sheet and the collapsed rail are proposals |
| Sending a variant (25, 26) | The sends planned and not sent yet | The four steps as groups, one under the other; step 4 is docked at the foot | **Proposal**: list kept visible beside the steps (open decision 17) |
| Content (27, 28, 43) | Title and New record, the Records / Categories / Graph switch, search, the three filters, the list | The record page with all its sections, or the category page. Choosing an image opens a sheet (43) | Diede's pattern for lists; drawn 2026-10-17. The graph is not drawn |
| Audiences (37) | The audiences, with the New and Suggest buttons and search | The editor: name, rules in and out, people added by hand, who a send reaches | Diede's pattern; drawn 2026-10-17; the arithmetic is a section, not a right-hand column (open decision 18) |
| Recipients (38) | The recipients, with search | A person: six read-only sections | Proposal, drawn 2026-10-17 |
| Deliveries (29 to 31) | The sends | The send and its recipients; a stranded send; one recipient's message as sent | Proposal, drawn 2026-10-17 |
| Decision slots (32) | The slots | A slot: what it chooses from, what it has picked | Proposal, drawn 2026-10-17 |
| Settings (33 to 36) | The sub-menu; below it, for the parts that have a list, that list | The part: General, a brand profile, a user, an integration | Diede's pattern (sub-menu, then details); the list under the sub-menu is a proposal (open decision 19) |
| Monitoring (39) | One column of table, no list and details | | **Exception** (open decision 14) |
| Decision history (40) | One column of table, reached from the foot of the approvals list | | Proposal; wide-table exception (open decision 14) |
| Sign-in (41, 42) | Outside the shell: one card on the linen ground, two steps | | Drawn 2026-10-17 |

Not drawn: Settings → Personalisation, Roles and Brands (a list and a form, as Users and Brand profiles); the category graph.

## 4. The foundation

The values are in `tokens.css`; this is what the numbers mean.

**Type.** System font, SF Pro on Apple devices; `ui-monospace` for ids and counts. Large title 26/32 bold (once per screen, in the list column), title 22/28 semibold (the heading of the details), headline 15/20 semibold (group titles), body 13/18, strong 13/18 semibold (list item titles), caption 12/16 in the secondary colour (meta, help, counts), mono 12/16. Two judgement calls against Apple's macOS styles: body leading is 18 not 16 because warnings run to several lines, and the caption floor is 12 not 10 so secondary text stays readable. Tabular figures on for counts and times.

**Size and space** (4 px grid). Controls 24 / 28 / 36 px high: 28 is Apple's desktop default, 36 is for the one decision action of a screen, 24 for dense rows. Radii: 6 controls, 10 cards and selected rows, capsule for chips. List inset 8, row padding 12; details inset 24, card padding 16; gap between groups 20; navigation inset 12. A hairline is 1 px; a push button has a 0.5 px shadow; the focus ring is 2 px with a 2 px offset, for the keyboard only.

**Colour.** Three colours from Diede's palette (2026-10-17), everything else derived and checked. **Linen** `#fcf8f2` is the ground (`--brand-bg`): the details column and the page. **Petrol** `#1a5d74` is the one action colour (`--brand-accent`): the primary button, links, navigation icons and the focus ring. **Pale Pink** `#f4bebb` (`--brand-highlight`) is the "you are here" marker: the selected navigation item, and nothing else. White (`--brand-surface`) is cards and the list column; `--brand-sidebar` is the navigation, a deeper linen; `--brand-selected` is the selected row, a pale petrol tint. Waiting on a person is the warm tint, approved the green one, running the blue one, failed the red one, expired and withdrawn neutral. **Colour is never the only signal**: every status has a glyph and a word. **Note the change of meaning:** in v1 `--brand-bg` was white; in v2 it is the ground, and white is `--brand-surface`.

**Why palette 1, and not the other two** (measured). A palette has to give the app one action colour that carries white text at 4.5:1, and its colours must not sit on a status hue, or decoration starts to read as a status. The status hues: failed red at 3 degrees, waiting amber at 36, approved green at 138, running blue at 210.

- **Palette 1, Linen / Petrol / Pale Pink: chosen.** Petrol carries white text at 7.34:1, the strongest of any colour offered, and is as near the running blue as the old accent was. Linen is a warm near-white, fine as a ground. Pale Pink sits at hue 3, exactly the failed red, so as a surface tint it would be indistinguishable from the failed tint (`#fde8e6`). That is why it has one narrow role: the navigation's "you are here", a fill behind a bold label, far from any status. It is never a status and never a content surface.
- **Palette 2, Antique Gold / Blush Pink / Burgundy: rejected.** Antique Gold gives only 2.96:1 with white text, so it cannot be a button or a link colour, and it sits 6 degrees from the waiting amber. Burgundy sits 3 degrees from the failed red, so every primary button would look destructive.
- **Palette 3, Cornflower / Chartreuse / Rust: rejected.** Cornflower gives 2.06:1 and Chartreuse 1.35:1, so neither can carry an action. Rust sits 9 degrees from the waiting amber and would read as a permanent warning.

*Revert path.* The first v2 values, neutral cool greys with accent `#0066cc`: ground `#f2f2f7`, sidebar `#ebebf0`, hover `#eeeef3`, selected `#e4eef9`, hairline `#d9d9df`, field border `#7a7a80`, text `#1d1d1f`, secondary text `#5f5f65`, accent and focus `#0066cc`; dark: ground `#111113`, card `#1c1c1e`, accent `#4da3ff`. `--brand-highlight` did not exist then; the selected navigation item used `--brand-selected`. The canvas keeps its version history.

**Contrast, computed from the hex values** (WCAG relative luminance; text needs 4.5:1, a field border and the focus ring need 3:1). Lowest text pair: 5.56 in light (the running chip), 4.58 in dark (secondary text on the selected row), 7.02 in light with increased contrast, 4.66 in dark with increased contrast. Lowest field border, focus ring or icon: 3.58, 4.15, 5.41 and 4.66. The pairs checked: text, secondary text and the link colour on the page, a card, the sidebar and a selected row; the label on the primary button; each status chip; the Reject label; a field border on the page, a card, the sidebar and a well; the focus ring on the same and on the selected row and the highlight; the navigation icon on the highlight. A build must re-run this on the tokens it ships.

**Motion and transparency.** None, except a spinner on a busy button, which stops under Reduce Motion. Every surface is opaque, so Reduce Transparency changes nothing. Apple's translucent "Liquid Glass" material was left out on purpose: an earlier session found translucent surfaces pulled focus away from the work.

**Initials avatar** (rule from Diede, 2026-10-13). A circle for a person, a rounded square for a brand, with initials in it. Its colour is a function of the name, so the same name is the same colour on every device and every reload, with no random number and nothing stored.

1. **The name** is taken as shown: a person's display name, a brand's name, and the email only when there is no name. Trim it, normalise it to NFC, lower-case it, so "Anke Voss", "  anke voss " and "ANKE VOSS" are one colour.
2. **Hash** it with FNV-1a, 32 bit, over its UTF-16 code units: start at `0x811c9dc5`; for each unit, xor it in, multiply by `0x01000193`, keep 32 bits.
3. **Hue** is the hash modulo 360.
4. **Colour**: background `hsl(hue S L)`, initials `hsl(hue S L)`, with the saturation and lightness of the active theme (the `--brand-avatar-*` tokens in `tokens.css`).
5. **Initials**: the first letter of the first word and of the last word, upper case. One word gives one letter. For an email, take the part before the `@`, drop anything after a `+`, split it on dots, underscores and hyphens, and use the same two letters.

| Theme | Background (S · L) | Initials (S · L) | Lowest contrast over all 360 hues |
|---|---|---|---|
| Light | 50% · 90% | 60% · 24% | 5.65 |
| Dark | 32% · 24% | 70% · 86% | 7.30 |
| Light, increased contrast | 50% · 86% | 70% · 16% | 8.29 |
| Dark, increased contrast | 32% · 16% | 80% · 92% | 11.72 |

The saturation and lightness are fixed per theme, and only the hue varies, so the initials stay readable on every hue; the lowest value in every theme is at hue 60, the yellows. Text needs 4.5:1. **The colour is decoration, never the signal**: the initials carry the identity, so two names that land on near hues cost nothing. Avatar hues overlap the status colours, so an avatar is always a circle or a rounded square with letters, never the capsule with a glyph and a word that a status is.

*Reference implementation* (JavaScript, matches the boards):

```js
function avatarHue(name) {
  const s = name.trim().normalize('NFC').toLowerCase()
  let h = 0x811c9dc5
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h % 360
}
```

In React, set the hue on the element as `style={{ '--avatar-hue': avatarHue(name) }}`; the `.avatar` class in `canvas-v2/ui.css` does the rest, and a theme change needs no code. (The canvas boards set `background` and `color` inline from the same numbers, because the canvas runtime does not set custom properties.)

*Test vectors*, for the build's test: Nordlicht Kaffee gives NK and hue 206; Maria Hartmann MH 176; Jonas Weber JW 121; Anke Voss AV 319; Robin Approver RA 156; Acme Agency AA 210; Scheduler S 242. Email only, no display name: `m.hartmann@nordlicht-kaffee.example` gives MH and hue 163, `kim.lee@example.test` KL and 200, `anna+news@example.test` A and 93 (the `+news` is dropped), `support@example.test` S and 244. Over 20,000 synthetic names the hashes spread across all 360 hues, the busiest hue holding about 1.4 times the average.

**Where it is used.** Two places. **The signed-in person**, in the foot of the navigation column, above Sign out, in the expanded column and in the collapsed rail: it replaces the email that was shown as text there. Its name is the person's display name, or the email when there is none (the session user has `display_name`, optional, and `email`). The avatar has `role="img"` with the display name as its label, and the email as its hover text. **A brand**, as the rounded-square tile that stands in for the brand switcher in the collapsed rail. Nowhere else: no screen shows a person's picture or role yet, and avatars beside a requester or a decider are not drawn (open decision 10).

## 5. The component library

Defined as classes in `canvas-v2/ui.css` and drawn with every state on the board "Components". The React Aria component to build each on is in the right column.

| Component | Class | States drawn | Build on |
|---|---|---|---|
| Button | `btn`, `btn-primary`, `btn-destructive`, `btn-plain`, `btn-sm`, `btn-lg`, `btn-icon` | default, hover, pressed, keyboard focus, disabled, busy | `Button` |
| Filter pull-down | `btn pulldown` | closed, hover, focus, open | `Select` with its label inside the control |
| Menu and option list | `group`, `menu-i` | selected, hover | `Popover` and `ListBox` |
| Text field, text area | `field`, `lbl`, `help`, `err` | default, focus, invalid with error, disabled | `TextField` |
| Option lists | `opt` | selected, unselected, disabled | `RadioGroup`, `CheckboxGroup` |
| Tabs, segmented control | `seg` | selected, unselected | `Tabs` |
| Status chip | `chip`, `chip-wait`, `chip-ok`, `chip-run`, `chip-bad` | five statuses | none (plain element) |
| Navigation item | `nav-item`, `col-nav.is-collapsed` | default, hover, selected, focus, collapsed | `NavLink` |
| Brand switcher | `brand-btn`, `brand-tile` | expanded, collapsed | the existing `BrandSwitcher` |
| Initials avatar | `avatar`, `avatar--square`, `avatar-sm` | people (circle), brands (rounded square), 24 and 32 px, every theme | plain element with `role="img"` and the name as its label |
| List item and list foot | `item`, `list-foot` | default, hover, selected, focus, flagged | `GridList` |
| Group card and fact row | `group`, `group-title`, `fact` | n/a | plain elements |
| Notice | `notice`, `notice-alert` | quiet line, warning row, alert | plain elements with the right `role` |
| Action group | `decide` | n/a | plain element, sticky at the bottom |

**Added 2026-10-17, while drawing the other screens.** These are in `ui.css` too, but they are drawn only inside the screens (20 to 43), not on the "Components" board, so their states (hover, focus, disabled) follow the buttons and fields above and are not drawn separately.

| Component | Class | Where it appears | Build on |
|---|---|---|---|
| Back link | `back` | Above a details title that came from a list or a parent (Campaigns, Categories, Users) | `Link` |
| Search box | `search` | Top of a list | the existing `SearchBox` (its label, Search button and Clear) |
| List tools and create form | `list-tools`, `list-form` | Column 2: the Records / Categories / Graph switch, "New campaign", "Create a category" | plain elements, `Tabs` for the switch |
| Select button, full width | `select-btn` | Every `Choice` in a details form | `Select` |
| Data table | `dtable-wrap`, `dtable`, `num`, `nw`, `is-total` | Results, modules, recipients, picks, permissions | the existing `DataTable` (a real table) |
| Switch | `switch` | "Machine ready", "Ready for Email" | `Switch` |
| Collapsible section | `dsc` | Results, the channel sections of a record | `Disclosure` or `<details>` |
| Field row, button row | `frow`, `btnrow`, `quiet`, `numlist` | Inside a group card: one field per row with a hairline between; a row of buttons; a quiet line with a glyph; a list of lines | plain elements |
| Sheet | `scrim`, `sheet` | The preview, choosing an image | `Modal` with `Dialog` |
| Wide column | `col-wide` | Monitoring and the decision history only | plain element |
| Drawing aids | `mail`, `ph-img`, `sk` | A stand-in for a rendered email, an image, a line of text | none: **not components, never build them** |

Forced-state classes (`is-hover`, `is-pressed`, `is-focus`, `is-disabled`) exist only so the board can draw a state; the build uses the real states React Aria exposes (`data-hovered`, `data-pressed`, `data-focus-visible`, `data-disabled`).

## 6. The approvals screen, in full

**What the repo says it contains** (from `frontend/src/screens/Approvals.tsx`, `ApprovalDetail.tsx` and [[react-screen-inventory]]; check them again, they move).

*The list.* The title "Approvals". Two filters, Action and Requested by, each offering only values this brand's requests carry (the server's `filter-options`). Rows newest first, 50 a page, a Newer and Older pager driven by the server total ([[ADR-185 — Lists That Grow With Data Are Paged in One Envelope]]). Each row: Request, Summary, Requested by (name and "person" or "integration", plus "no longer allowed; approving withdraws it" when the requester has lost the right), Expires ("No deadline" when it has none). **No actions in the list.** The filters and the page live in the URL.

*The decision history* is a screen of its own, a wide table (Request, Summary, Outcome linked to the delivery, Requested by, Decided by, Ended, Reason) with the same filters. "Log and queue stay separate" (Manager Workflow Q1.6).

*The details.* The request's label and summary. A quiet status line "You cannot decide this request." plus the reason when `may_decide` is false. An alert when the description failed. "Before you decide": the warnings, shown and never enforced. Facts: Status, Requested by (the type only), Requested, Expires, then Decided, Reason given and "Why it did not run" when present, then the server's own label/value rows, rendered generically. A paragraph when approving would withdraw the request. The decision group, only when the request is pending and `may_decide`: a "Choose one" option list only when the action offers options, an optional reason ("Reason (optional; the requester sees it)"), and the buttons **Approve and run** and **Reject**.

**Behaviour the design must not change**

- Approve has **no confirm step** (decided 2026-10-03: a confirm trains people to click through it). It runs the action ([[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4).
- Reject stays available when the request is blocked. Approve is disabled while `blocked_reason` is set, or while a pick-one has no choice.
- `may_decide` is read from the server, never computed by the client.
- Only a person with a session may decide ([[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]).
- The inbox is the home screen ([[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]]). The requester is always shown with its kind ([[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]).

**States**: loading ("Loading…"), empty ("Nothing is waiting for a decision."), filters match nothing ("No request matches these filters."), could not load (an alert), forbidden, already decided, blocked, requester no longer allowed, pick-one, busy while approving. All are drawn on the boards "Approvals, states" and "Details column".

**Not backed by the repo, so not drawn** (the first canvas showed them from invented content): an email "as sent" preview on the approval, "Request changes", Pending/Decided/Mine tabs, a density toggle, "system proposed / added by hand" audience numbers, an override rate, a consent/cap/link check panel, snapshot ids, A and R key hints printed on buttons (shortcuts are found through `?`, Alt and Ctrl), a role line for the signed-in person (their initials avatar is drawn, in the navigation foot), a count badge in the navigation. Sample names, ids and dates on the boards are invented placeholders, and the warning texts are examples of the real kinds, not the server's strings.

## 7. What the first build attempt taught us

A first implementation of the shell and the approvals screen was written and rewound. It passed type-check and the existing tests, but was never run in the browser. These are the findings worth keeping.

**Order that worked.** Tokens, then the global CSS (buttons, fields, pull-downs, tables, popovers, dialogs), then the shell (navigation column), then approvals. The shell and the global CSS reach every screen at once, so look at several screens after each step.

**`--brand-bg` changed meaning.** Old rules that used it as "white" (buttons, popovers, dialogs, the text colour on an accent fill) must move to `--brand-surface`, or they take the ground colour instead of white. Search the whole stylesheet for it.

**The list as a React Aria `GridList` keeps the old tests honest.** It renders the grid and row roles, so tests that ask for `role="grid"` named "Waiting for a decision" still passed. Keep each requester's text in an element of its own (a test asks for `integration` exactly), and keep "no longer allowed; approving withdraws it" in exactly one element (a test counts matches, case-sensitively).

**Open problem: marking the open request for assistive technology.** `GridListItem` does not pass `aria-current` through, so the open row was highlighted only by a class, and a test that asked for the attribute failed. Options to evaluate: a controlled single selection (`selectionMode="single"` with `selectedKeys`), but check what a click then does, because with an existing selection a click may toggle rather than fire the row action; or a `ListBox`; or setting the attribute through a ref. Decide before building.

**The list keeps its filters and page when a request opens.** The filters are in the URL, so opening `/approvals/7` must carry the current query string, or the list beside it silently widens. The draft did this with `navigate({ pathname, search: location.search })` and a test.

**Routing.** A pathless layout route renders the list and an `Outlet`; `/approvals`, `/approvals/:id` and `/` sit inside it, `/approvals/history` outside. The open request is the address, as before, so links, reload and the back button still work. The inbox component rendered alone must keep working: the existing tests render it that way.

**Full-bleed columns.** The main area normally has padding; a screen laid out as list plus details needs none. The draft used `.shell__main:has(> .split) { padding: 0 }` (CSS `:has`, current in all evergreen browsers; confirm that is acceptable for the supported browsers). Each column scrolls on its own, so the split is `height: 100vh` with the page itself not scrolling, and the action group is `position: sticky; bottom: 0` inside the details column.

**The collapsed rail.** Hide labels with CSS that keeps them readable by a screen reader (the standard visually-hidden rules), never remove them, so no second set of `aria-label`s is needed. The brand switcher collapses to a tile showing the first letter, with the full name still in the page. Remember the choice in the browser (`localStorage`, in a `try`/`catch`; a convenience only).

**Headings.** The list column has the one `h1`; the request's label is an `h2` and its group titles are `h3`.

**The email is no longer shown as text.** The shell's existing test finds the signed-in email on the page (`findByText(A_SESSION.user.email)`). With the avatar in the foot the email is only the hover text, so that test must change: assert the avatar by its accessible name (the display name, or the email when there is none) and keep the Sign out button findable by its name when the rail is collapsed. A sighted person can no longer read their address without hovering; Diede chose that, but a visible display name beside the avatar is an easy option if it is missed.

**Copy the draft added that the repo must decide:** "Select a request to review it." (the details before anything is open), the list's count line ("N waiting for a decision", or "N match these filters"), and the loss of the dash before "no longer allowed". It also dropped the "← Approvals" back link and moved the history link from the top of the page to the foot of the list. Real behaviour kept: the pager renders nothing when everything fits on one page, where the board shows "1–7 of 7".

**Not verified at all:** a live render of the real app (use both preview servers, `api` and `client`; sign in with the dev code; scratch data only), dark mode, increased contrast, the collapsed rail, narrow widths, the sticky action group over a long request, and the other screens under the new global CSS.

## 8. Screens still in Jinja: where the logic may have to change

Several screens are still Jinja and not built in React ([[react-migration-inventory]], [[react-screen-inventory]]; the Jinja screens are frozen and will be retired, task-312). **The design must not be applied by porting each Jinja page one to one.** The three-column pattern assumes things a server-rendered page does not do, so some screens need their logic reshaped, and **a design that changes behaviour is a decision to record first, not a style change** ([[CONSTRAINTS]]).

What the pattern assumes, to check per screen before it is built:

- **A list and one record load separately and independently**, with the list staying put while the record changes. A Jinja page that renders list, record and form in one request does not fit; it needs a list read and a record read, each with its own states.
- **Selecting is the address.** The open record is in the URL, and the list's filters and page too, as approvals does. Decide the route for each screen.
- **Lists that grow are paged in one envelope** ([[ADR-185 — Lists That Grow With Data Are Paged in One Envelope]]).
- **Each screen has one prominent action**, docked in the details. Several Jinja pages carry multiple equal buttons or a multi-step form; decide which one is primary and where the rest go.
- **Multi-step flows** (sending a variant) and **the editor** (modules, content selection, preview) do not fit "list, then details" exactly. They are drawn now (renders 21 to 26) with a proposal each, but a drawing is not a decision about the logic: the editor works on a stack of modules, and the send is four steps whose step 4 only appears once step 3 has planned the send. Check both against the screen before building.
- **Anything computed in the page** (derived counts, limits, overrides) is presentation the SPA computes itself, but rules stay on the server ([[react-screen-inventory]]).

A checklist for each screen, to answer before drawing or building it: What is the list? What does choosing an item do to the address? What is the one primary action? What are the groups in the details? What are its empty, loading, error, forbidden and already-done states? Which Jinja behaviour must survive, and which part needs a decision first?

## 9. Open decisions

1. **Density.** [[DESIGN]] settled that a compact option stays, but no screen has the control and v2 does not draw it. It needs a place (the navigation foot, or Settings) and a decision.
2. **Marking the open row** for assistive technology (section 7).
3. **The wording** of the details placeholder and the list count.
4. **The icon set** that replaces the placeholders.
5. **The editor's preview**: a second group in the details, or its own fourth column on wide windows.
6. **Dark mode**: whether to build a switch, and whether the app should follow the system's light or dark setting. The draft follows the contrast setting automatically and leaves dark mode opt-in.
7. **The unassigned screens.** Drawn since 2026-10-17 (section 3); what the drawings propose is decisions 13 to 20 below.
8. **Which browsers are supported**, for `:has` and the `mask` used by the pull-down chevron.
9. **Email** is a separate design job ([[DESIGN]] scope); nothing here covers it.
10. **More places for avatars.** Decided: the signed-in person in the navigation foot, and the brand tile in the collapsed rail. Undecided: whether a person's avatar shows beside a requester or a decider. The repo holds a requester's name and kind (person or integration), and an integration has no person to draw.
11. **The system and human cues** for decision slots (section 11). A proposal is drawn in the editor (render 21): a chip with a glyph and a word, "Record", "Slot" or "Typed in", on each module row, in the neutral chip style, so no colour carries the meaning. It is a draft of the treatment, not a decision. It marks how a module's content is chosen: a record a person bound, a decision slot that picks for the system, or text typed in. Whether that is the "system and human cue" TASK-372 means is for Diede to say.
12. **Narrow and phone layouts**: a rule exists, no layout was drawn (section 11).

*Raised by the screens drawn on 2026-10-17. Each is a layout proposal on a board; none changes behaviour.*

13. **The editor drawn with the navigation collapsed** (render 21). It gives the module stack, the fields and the preview room. Is it the editor's default, or the person's own collapse, as on every other screen?
14. **Two wide-table screens**, Monitoring (39) and the decision history (40). Both are one table with five and seven columns, which does not fit a 380 px list. They are drawn as one column in place of list and details. The alternative is a list of rows with the facts stacked, which loses the scan across columns. This breaks "every screen has list and details", so it needs Diede's yes.
15. **Results on the campaign page** (20). The server's table has twelve columns; it is drawn as two tables (delivery counts, then engagement) so it fits the details column. Splitting is a layout choice; the figures and their wording are the server's.
16. **The preview as a sheet** (24), as it is an overlay today, drawn larger. Open decision 5 (a second group, or a fourth column) still stands.
17. **Sending a variant** (25, 26). The list of planned sends stays in column 2 beside the steps, instead of the steps having no list. The alternative is no column 2 and the steps in column 3 only.
18. **Who a send reaches** on the audience page (37). Today a right-hand column beside the rules; in the details column's width it is a section after the rules and the hand-added people. The arithmetic rows and their wording are unchanged.
19. **Settings with a list** (34, 35, 36). Column 2 holds the sub-menu and, under it, the part's list (profiles, users, integrations), which is two levels in one column. The alternative is the sub-menu as a switch at the top of column 3. General has no list at all, and Brands is a list with inline forms and no details; Roles and Personalisation (not drawn) would follow the Users pattern.
20. **Content's Records / Categories / Graph switch** (27, 28) is drawn as a segmented control at the top of column 2, where the repo has a horizontal sub-navigation. The graph itself is not drawn and may not fit three columns: it is a drawing with a table and a selected-item panel.

## 10. Starting the build

1. Read this page, the update at the end of [[DESIGN]], [[CONSTRAINTS]], [[react-screen-inventory]] and [[react-session-brief]]. Look at the renders in `docs/design/renders/`, and keep the canvas page "Three columns" open next to the code.
2. **Before any code change**, state the files, what changes, the governing ADRs and what could break (`CLAUDE.md`). Hold the final-design pass for the first screen: where each part lands, which existing components it reuses (`Choice`, `Pager`, `DataTable`, `ScreenState`, `BrandSwitcher`), what it deliberately leaves alone.
3. **Check the queue** before starting (`backlog task list --status "To Do" --sort ordinal --plain`), the work is TASK-372, "The finished design applied to the React screens" (section 11 says what its scope needs beyond this design); task-94 (theming) is related. Check ChatGPT's handoff first (`git fetch`, new commits on `origin/codex/*`, new notes in `docs/queue/docs/`).
4. **Order**: tokens and global CSS, the shell, approvals, then one screen at a time, each with a decision about its Jinja counterpart.
5. **Verify** with type-check, the test suite, lint and a build, then **a live render** of the real app beside the canvas. Render the canvas boards too: the Claude in Chrome extension reaches the private artifact with Diede's own session.
6. The design decides the look; the repo decides behaviour. When a board and the code or an ADR disagree, the code wins: stop on that element, say what each shows, and ask. Never invent data, fields or endpoints. Nothing is committed unless Diede asks.

## 11. Gaps against the queue task (TASK-372)

TASK-372, "The finished design applied to the React screens", is the build this design is for. It was written for the November 2026 demo and says: the demo flow's screens first (campaigns, variant editor, content, slot settings, preview, deliveries and results, settings). Its notes of 2026-10-12 (Diede) say the neutral phase can use a conventional design system and should not invest in bespoke branding, and that the screens keep comfortable and compact density, accessible focus and states, and labelled system and human cues. Read against that, the design covers less than the task needs:

**What is designed.** The shell (three columns, navigation and its rail, the person's avatar), the foundation, the component library, **approvals in full** (every decision state, light and dark, with increased contrast), and, since 2026-10-17, **every screen of the demo flow**: campaigns, the variant editor with its record picker and slot settings, the preview, the send steps, content with its record page, categories and image sheet, deliveries with a stranded send and the message as sent, decision slots, audiences, recipients, monitoring, the decision history, settings (general, brand profile, users, integrations) and sign-in. Renders 20 to 43; the layout choices that needed a decision are open decisions 13 to 20 in section 9.

**What the 2026-10-17 screens are, and are not.** They are light-theme layouts of the real screens' contents, with invented names and figures. They are **not** drawn in dark or increased contrast (the tokens carry both; nothing was rendered), not drawn in their empty, loading, error and forbidden states beyond the shared ones on render 12, not drawn at narrow widths, and not interactive. They keep the three-column rule except the two wide-table screens (open decision 14).

**What has still nothing:** Settings → Personalisation, Roles and Brands (a list and a form, as Users and Brand profiles); the category graph (a drawing with a table; it may not fit three columns); the dialogs (New record, New audience, Suggest from a campaign, Paste people, New brand profile, the new-key dialog, keyboard shortcuts); the "Upload new" and "Web address" tabs of the image sheet. The build can apply the pattern and the component library to these, but "a design that changes behaviour is a decision to record first" ([[CONSTRAINTS]]); where a screen has a decision slot, a record bound to a variant, or a send in flight, check the state against the screen, not against the picture.

**Density.** The task keeps comfortable and compact. v2 draws neither as a choice: one density (28 px controls, 76 px list items) and no control for changing it. Open decision 1.

**System and human cues.** The task keeps labelled system and human cues; they are what tells a manager that a decision slot's record was picked by the system or pinned by a person. The first draft had them as a teal "system pick" and an ochre "pinned by you". v2 dropped the teal because the approvals screen does not need it and the new palette has no system colour, so the cue had no design. The editor render (21) now carries **a draft**: a neutral chip with a glyph and a word on each module row (Record, Slot, Typed in). It carries a word and a glyph, not a colour alone ([[CONSTRAINTS]]). It is not approved, and the slot, variant and campaign screens use it only where drawn. Open decision 11.

**Phone width.** The task records that the shell header overflowed at phone width with the long working title: the name wrapped to three lines and the email ran off the screen. The v2 shell changes both: the email is an avatar with the name beside the toggle. But the phone layout itself was never drawn (section 4 gives only the rule). Proposal for the build: below 800 px the navigation stacks above the screen and starts collapsed. Open decision 12.

**The name.** The product's name comes from `product.json` and is never typed into code (TASK-377 owns the rename and the current identity assets); the shell shows it from `PRODUCT_NAME`.
