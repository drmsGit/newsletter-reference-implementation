---
type: reference
created: 2026-10-10
---

# Design constraints: what the code allows

For the design session. It says what the design is free to decide, and where the
code, email clients or earlier decisions set limits. Checked against the code on
2026-10-10. When the design is ready, it comes into the repo here (`docs/design/`),
is checked against this page, and conflicts are settled before anything is built.

**The split.** The design decides the *look*: tokens, components and their
states, page patterns, the email visual language. The repo decides *behaviour*:
which fields a screen has, what a button does, the wording of legal and system
texts. Those come from decisions already recorded (ADRs, interview records). A
design that changes behaviour is a decision to record first, not a style change.

## Two surfaces

| | The manager app | The emails |
|---|---|---|
| Who sees it | People running campaigns, at `/manager` | Recipients, in their mail program |
| Built with | React, with React Aria components | HTML tables, one shared stylesheet inlined at send |
| Freedom | Nearly full | Limited by what email clients render |

## 1. The manager app

**What exists.** One plain stylesheet, `frontend/src/index.css`, with no CSS
framework and no preprocessor. It has nine design variables today:

| Variable | Value |
|---|---|
| `--brand-fg` | `#1a1a1a` |
| `--brand-bg` | `#ffffff` |
| `--brand-muted` | `#6b6b6b` |
| `--brand-line` | `#d8d8d8` |
| `--brand-accent` | `#2a5db0` |
| `--brand-danger` | `#b3261e` |
| `--brand-font` | `system-ui, -apple-system, "Segoe UI", sans-serif` |
| `--brand-radius` | `4px` |
| `--brand-space` | `8px` |

There is no dark mode and one layout breakpoint (900px).

**Free to decide:** colours, type scale, spacing, radius, shadows, and how every
component looks. The components come from React Aria, which supplies behaviour
and accessibility but no look of its own, so nothing visual is fixed by the
library.

**Give it as** a token table (name and value) that maps onto CSS custom
properties, plus each component's states. The components the app uses:

- Button, including a button that is busy or disabled
- Text field and text area, including a field with an error
- Choice: a dropdown with a label
- Data table, keyboard-navigable (React Aria grid), with paging
- Notices: errors (`role="alert"`) and quiet status lines
- Lists of checkboxes and options
- Dialog
- Tabs, if the design uses them

**States every component needs:** default, hover, keyboard focus (always
visible), pressed, disabled, invalid, and loading where it applies.

**Limits:**
- **Accessibility:**
  - Text contrast WCAG AA, at least 4.5:1, or 3:1 for large text.
  - A visible focus ring on everything focusable.
  - Nothing conveyed by colour alone.
- **Dense data.** Most screens are lists and tables of campaigns, content,
  people and approvals. Design for many rows, not cards of five.
- **Screens and their contents are fixed by earlier decisions.** The app has
  these pages:
  - sign-in;
  - approvals: inbox, history, detail;
  - campaigns, a campaign, and the variant editor;
  - monitoring;
  - settings;
  - content, a content record;
  - audiences, an audience;
  - recipients, a recipient;
  - decision slots, a slot;
  - deliveries, a delivery;
  - brand profiles, a profile (since 2026-10-11, task-350).

  Their fields and flows come from interview records (`docs/react-screen-inventory.md`).
  A mock-up is a reference for look, not a spec for what a screen contains.
- **Layout and keyboard accessibility are their own later session.** Visual
  polish is not added screen by screen while features are built.

## 2. The emails

**What exists.** An email is a stack of modules a manager places. Each module
type has a manifest (its fields) and a template (HTML tables with `.module-*`
classes). The module types and the fields they show:

| Module | Shows |
|---|---|
| `hero` | A headline and a button |
| `editorial` | A block of text |
| `cta` | A button (label and link) |
| `img_left` | A section heading, an image on the left, a headline, body text and a button |
| `img_right` | The same, with the image on the right |
| `single_stack` | The same, stacked |
| `envelope` | **Invisible.** The subject and preheader; it renders no visible content. Called `header` until 2026-10-10 (task-349), which frees that name for the visible logo header. |

Styling is one file for every email, `storage/modules/email/brand.css`, inlined
into each email when it is sent. It uses these classes: `.module-wrapper`,
`.module-headline`, `.module-body`, `.module-button`, `.module-image`,
`.module-image-cell`, `.module-content-cell`, `.module-section-heading`,
`.module-hero`, `.module-cta`. The default font is Arial or Helvetica.
**Today no fixed content width is set** (`width: 100%`): the design should choose
one. Around 600px is the common choice.

**Decided and coming (ADR-194, 2026-10-11, which replaced ADR-193); the design should cover these:**
- **Brand profiles.** A brand has as many profiles as it needs (a flashy
  marketing look, a calm transactional one, a dark Black Friday one), and each
  email variant picks one. A profile carries the look (colours, fonts, sizes,
  spacing, radius), images (the logo), texts (service hotline, footer texts,
  unsubscribe wording, legal details) and links (menu links). **Which fields a
  profile has is declared per installation in a setup file**, so the design
  should name the fields it needs (for example two font sizes or four) and say
  which of its values come from the profile and which are shared.
- **A visible header module:** logo and menu links, from the email's profile.
- **A footer module:** links, hotline and texts from the profile, plus one
  optional free text per email. A manager places them or leaves them out.
- **A fixed legal footer** at the bottom of every email (marketing,
  transactional and tests). It is not a module, and no manager can remove it.
  It holds the profile's legal details (legal name, address, imprint and
  privacy links), and for marketing the unsubscribe line with the profile's
  wording. It is plain and small today (12px grey, centred). The design may
  style it but not drop or hide any of it.
- **Decorative modules** (header, footer, later a section heading) are fine to
  design freely; they never count as an email's content.

**Limits set by email clients.** These are not ours, and they are the hard part:
- **Layout is tables.** Flexbox, grid, `position`, floats and multi-column CSS
  are not reliable across clients.
- **No CSS variables.** Per-brand colours and fonts are filled in when the email
  is built, not looked up by the client.
- **Fonts:** web fonts work in some clients and fall back in others (Outlook,
  Gmail). Every font needs a safe fallback, and the design should look right in
  the fallback.
- **Images:** many clients block images until the reader allows them. A logo or
  hero image needs alt text, and the email must still make sense without it. No
  text baked into images.
- **Width:** design for one column, around 600px, readable on a phone.
- **Dark mode:** clients invert colours by their own rules. Transparent logos and
  very light or very dark brand colours need checking against that.
- **Buttons:** a coloured link styled as a button works everywhere; rounded
  corners and shadows degrade in some clients (old Outlook), so the design
  should survive square corners.

## 3. Other surfaces (mostly out of scope)

- **Push notifications** carry only a title and body text, with no visual design.
- **The unsubscribe page** (`/unsubscribe/{token}`), which a recipient opens
  from an email, is a small public page. Its wording is fixed by ADR-191 and
  English for now; its look may follow the brand.
- **The older Jinja screens** are frozen and will be retired (task-312). Don't
  design for them.

## What the repo will check when the design comes in

1. Every email design against the client limits above.
2. Every screen mock-up against what that screen must contain.
3. The tokens against the accessibility targets (contrast, focus).
4. The profile fields against ADR-194: what the design takes from a brand
   profile, and what is shared by every email.
5. Anything that changes a recorded decision is flagged for a decision first.
   For example: the manager app is one palette per installation, and only the
   working brand's logo comes from its brand profile (ADR-194).

Related: [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] (which replaced ADR-193),
[[ADR-131 — Email Module Templates Use MJML as Source Format]],
[[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]],
[[ADR-173 — The Manager Client's Runtime Dependencies]], task-94 (theming),
task-350, task-351 and task-354 to task-356 (the brand profile, header, footer and look builds), task-112
(assets, for logos).
