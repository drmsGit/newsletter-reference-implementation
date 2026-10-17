---
type: reference
created: 2026-10-17
---

# Renders of the v2 design

What the design looks like, as images, for the session that builds it (queue task TASK-372). Read [[HANDOFF]] first; these pictures are what its words describe. Rendered 2026-10-17 from `../canvas-v2/` (the snapshot of the canvas), at 1x.

**They are renders of a prototype.** The boards are Design Components drawn from invented sample data (names, ids, dates, warning texts). The font is the system font, which on the Mac they were rendered on is SF Pro; another system draws its own. Where an image and the repo's real screen disagree about what a screen contains, the repo wins ([[DESIGN]]).

## The approvals screen, 1440 × 900

| File | Shows |
|---|---|
| `01-approvals-light.png` | The reference screen: navigation, list with filters and foot, the request open with its decision docked at the bottom. The one to build against. |
| `02-approvals-dark.png` | The same screen in dark. |
| `03-approvals-nav-collapsed.png` | The navigation collapsed to its icon rail: the brand tile, the icons, the person's avatar above the sign-out icon. The details column takes the freed width. |
| `04-approvals-increased-contrast.png`, `05-approvals-dark-increased-contrast.png` | The increased-contrast sets, light and dark: stronger lines and text, the same layout. |

## The decision states, on the full screen, 1440 × 900

| File | Shows |
|---|---|
| `06-state-pick-one.png` | A request that offers options: "Choose one", Approve disabled with its hint. |
| `07-state-requester-no-longer-allowed.png` | Approving would withdraw the request: the notice above the warnings, the flag in the list row. |
| `08-state-cannot-decide.png` | The person may not decide: the quiet status line, no decision group. |
| `09-state-approving.png` | The busy state: "Approving…" with the spinner, the field and Reject disabled. |
| `10-state-already-decided.png` | Decided: the status chip, who decided, the reason; no decision group. |
| `11-state-could-not-load.png` | The load error in the details column. |
| `12-states-board.png` | The same states side by side, with the list column's empty, filtered-empty, loading and error lines. 1280 × 2700. |

## The foundation and the components

| File | Shows |
|---|---|
| `13-foundation-light.png`, `14-foundation-dark.png` | Layout and column widths, the indent rule, every colour with its computed contrast, the initials avatar rule with samples and the whole hue wheel, the type scale, size, space and shape. 1280 × 4200. |
| `15-components-light.png`, `16-components-dark.png` | The component library with every state: buttons, filter pull-down and menu, fields, option lists and tabs, status chips, icons, initials avatars, navigation items and rail, list item and foot, group card, notices, the action group. 1280 × 2780. |
| `17-screen-patterns.png` | The three-column pattern as wireframes for approvals, campaigns, editor, audience and settings. Region names only. 1440 × 1860. |
| `18-navigation-component.png`, `19-details-component.png` | The navigation column (232 wide) and the details column (760 wide) on their own. |

## The other screens, light, 1440 wide

Added 2026-10-17 for TASK-372. Each is a full screen in the three-column pattern, drawn from what the React screen contains today (the wording, fields and tables are the real ones; the names, figures and dates are invented). Heights are the content's measured height, so they differ.

| File | Size | Shows |
|---|---|---|
| `20-campaigns.png` | 1440 × 1840 | Campaigns: the list with the create form and search; the open campaign with its results (two tables), each variant with its modules and decision slots, and New blank variant. |
| `21-editor.png` | 1440 × 1540 | The variant editor, navigation collapsed. Column 2 is the module stack; column 3 the brand profile, preview bar, envelope fields with the AI suggestions, and the open module. A module bound to a record, one typed in, one on a decision slot (the cue chips tell them apart). |
| `22-editor-picker.png` | 1440 × 1300 | The same editor with the record picker open on a module. |
| `23-editor-slot.png` | 1440 × 1620 | The same editor with a decision slot's settings open: strategy, how many it shows, categories, number fields with an invalid value and its message, "Use one content record instead". |
| `24-preview-sheet.png` | 1440 × 900 | The preview as a sheet over the editor: who it is shown for, the state of each module, the rendered email. |
| `25-send-plan.png` | 1440 × 1380 | Send a variant, steps 1 to 3: what goes out, the optional test send, planning the send. Column 2 lists the sends planned and not sent yet. |
| `26-send-ready.png` | 1440 × 1100 | The same screen once a send is planned: step 4, docked at the foot of the details with the real-email warning and "Send real email to 1,180 people". |
| `27-content-record.png` | 1440 × 2760 | Content: the list with its filters, and one record page with every section (status, publication, details, draft with AI, translations, the channel sections, performance, categories, published versions, used in). |
| `28-categories.png` | 1440 × 1280 | The categories list with the create form; one category's page (name and type, where it sits, its records, signal, delete). |
| `29-deliveries.png`, `30-delivery-stranded.png` | 1440 × 880, 1440 × 1020 | Deliveries: the list, and a send with its recipients; and the same send when it looks stranded, with "Release this send". |
| `31-delivery-as-sent.png` | 1440 × 1180 | One recipient's message as it was sent: the changed-templates notice, envelope, the message, fields, modules. |
| `32-decision-slots.png` | 1440 × 1240 | Decision slots: the list, and a slot's page (what it chooses from, what it has picked, latest picks). Read-only. |
| `33-settings-general.png` | 1440 × 1980 | Settings: the sub-menu in column 2, General in column 3 (sending, sign-in sessions, signals, AI with its per-task block). |
| `34-settings-brand-profile.png` | 1440 × 2600 | Settings, brand profiles: the sub-menu with the profile list under it, and one profile's form with every group. |
| `35-settings-users.png`, `36-settings-integrations.png` | 1440 × 800, 1440 × 840 | Users (the person, their access, sign-in) and integrations (keys, the permission grid per brand, sending without a person). |
| `37-audiences.png` | 1440 × 2740 | Audiences: the list; the audience editor with an open rule, leave-out rules, people added by hand, and the arithmetic of who a send reaches. |
| `38-recipients.png` | 1440 × 1120 | Recipients: the list, and a person's read-only page with its six sections. |
| `39-monitoring.png`, `40-decision-history.png` | 1440 × 760 each | The two **wide-table exceptions**: one column of table in place of list and details. Monitoring is one table with no counts; the decision history has seven columns. |
| `41-sign-in.png`, `42-sign-in-code.png` | 1440 × 640 each | Sign-in, outside the shell: the address step, and the code step with its error. |
| `43-image-sheet.png` | 1440 × 900 | "Choose an image" as a sheet over a content record: Library tab with the grid and the selected image. |

## What the renders do not show

- **Narrow and phone widths.** The rule is in [[HANDOFF]] (below about 1,100 px the details wrap under the list; on a phone one column at a time) but no layout was drawn for it. The prototype's columns have fixed minimum heights, so a render of it at phone width would mislead; it is deliberately not here.
- **Dark and increased contrast for screens 20 to 43.** Every board takes `theme` and `contrast` props and uses only the tokens, so the sets apply, but none of these screens was rendered in them. The approvals screen (01 to 05) and the libraries (13 to 16) are.
- **Screens and parts still not drawn.** Settings: Personalisation, Roles and Brands (a list and a form, same pattern as Users and Brand profiles). The category graph. The "Upload new" and "Web address" tabs of the image sheet. The dialogs: New record, New audience, Suggest an audience from a campaign, Paste people, New brand profile, the new-key dialog, the keyboard-shortcuts dialog. Empty, loading and error lines of these screens; the shared lines are on `12-states-board.png`. The approvals inbox, history link and detail are 01 to 12.
- **Hover and pressed on the real screen.** They are drawn on the component boards (15, 16), not on the screen renders.
- **Motion.** The spinner is a still frame.

## How they were made

From `../canvas-v2/`, with the Claude Design runtime script saved beside the boards as `support.js` (it is the canvas's own `artifact-type/dc-runtime.js`, which the canvas serves to every board; it is not stored here), served on localhost and photographed by headless Chrome:

```bash
cd <folder holding the boards, ui.css and support.js>
python3 -m http.server 8765 --bind 127.0.0.1 &
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars \
  --force-device-scale-factor=1 --window-size=1440,900 --virtual-time-budget=9000 \
  --user-data-dir="$(mktemp -d)" --screenshot=out.png http://127.0.0.1:8765/V2Approvals.dc.html
```

The variants (increased contrast, the screen in each state, the dark library) are one-line wrapper pages that import a board with props (`theme="dark"`, `contrast="more"`, `state="options"`), as the dark board in the canvas does; they are not kept. Window heights for the tall boards are the boards' measured content heights.

Screens 20 to 43 were made the same way, each board at 1440 × its content height. The height of each board was measured in the browser with the minimum heights switched off, then written into the board (and into `../canvas-v2/canvas.json`), so a frame fits its content. Boards with a variant (`mode`, `step`, `part`, `state`) are wrapper pages that import the board with that prop, as `V2EditorPicker`, `V2SendReady`, `V2DeliveriesStranded`, `V2SettingsProfile`, `V2SettingsUsers`, `V2SettingsIntegrations` and `V2SignIn2` do; those wrappers are in `../canvas-v2/`.

**Found while rendering the later screens, and fixed in `ui.css`:** plain links in a screen came out browser-blue (they now take the accent); a disabled plain button kept a grey fill; a wide column in a wrapping row dropped under the navigation when its table was wide (it now has a flex basis); native checkboxes were browser-blue (now the accent); the list column's labels sat 12 px left of its one text indent.

**Found while rendering, and fixed in the canvas:** three board frames were shorter than their content and clipped it (Foundation lost its whole "Size, space and shape" section, Patterns and States lost their last rows). The frames now fit, and the lower row of boards moved down to make room.
