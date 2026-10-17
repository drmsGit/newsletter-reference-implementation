---
type: reference
created: 2026-10-12
---

# Canvas snapshot, v2 (three columns)

A copy of the v2 boards of the Claude Design canvas "Approvals redesign" (https://claude.ai/artifact/HEESqGiNZKeWaqT2d5DatL, page "Three columns"), first taken 2026-10-12 and brought up to the screens added on 2026-10-17 (canvas version 52), so the design does not depend on the canvas staying reachable. It matches the published files. Start from [[HANDOFF]].

| File | Board |
|---|---|
| `V2Approvals.dc.html` | The approvals screen, three columns (the navigation collapse works in Play) |
| `V2ApprovalsDark.dc.html`, `V2ApprovalsCollapsed.dc.html` | The same screen, dark, and with the navigation collapsed |
| `V2Foundations.dc.html` | Layout, the indent rule, colour with computed contrast, type, size and space |
| `V2Components.dc.html` | The component library with every state |
| `V2Patterns.dc.html` | Wireframes of the screen patterns: approvals, campaigns, editor, audience, settings |
| `V2DetailStates.dc.html` | The states of the list and details columns |
| `V2Nav.dc.html`, `V2Detail.dc.html` | The navigation and details columns as components, imported by the screen |
| `V2Campaigns`, `V2Editor` (+ `V2EditorPicker`, `V2EditorSlot`), `V2PreviewSheet`, `V2Send` (+ `V2SendReady`) | The campaign flow: campaigns, the variant editor with its record picker and slot settings, the preview sheet, the send steps. Added 2026-10-17. |
| `V2Content` (+ `V2Categories`, `V2ImageSheet`) | Content: list and record page, categories, the image sheet |
| `V2Deliveries` (+ `V2DeliveriesStranded`), `V2DeliveryAsSent`, `V2DecisionSlots` | Deliveries, one recipient's message as sent, decision slots |
| `V2Monitoring`, `V2ApprovalsHistory` | The two wide-table screens (one column of table, no list and details) |
| `V2Audiences`, `V2Recipients` | Audiences with the rule editor, recipients with a person's page |
| `V2Settings` (prop `part`: general, prompts, profile, users, integrations; wrappers `V2SettingsPrompts`, `V2SettingsProfile`, `V2SettingsUsers`, `V2SettingsIntegrations`), `V2SignIn` (+ `V2SignIn2`) | Settings and sign-in |
| `V2CreateDialogs` | The create dialogs behind every "New ..." button |
| `ui.css` | The foundation and the component library, linked by every board |
| `canvas.json` | The layout of the canvas, with its pages and Diede's sticky notes |

**These are not runnable here.** A `.dc.html` file is a Design Component: it needs the Claude Design runtime (`support.js`), which the canvas supplies. Read them as markup and as the specification of each state. `canvas.json` also lists the first-draft boards (page "First draft"), whose files are not copied: that version is superseded, and its content was drawn from invented data. The names and figures in the boards are invented placeholders.

**`ui.css` is the prototype's stylesheet**, with the same colour values as `../tokens.css` (checked, light and dark). Production CSS is written against the real components; see [[HANDOFF]] section 5.
