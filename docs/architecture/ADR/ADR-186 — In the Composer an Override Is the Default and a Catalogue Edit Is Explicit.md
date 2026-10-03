---
type: adr
status: accepted
topic:
  - architecture
  - overrides
  - content
  - decision
  - frontend
created: 2026-10-03
source:
  - "User decision 2026-10-03, after trying the built variant editor (task-258, slice 6) on the dev server"
  - "[[Campaign Write Surface - final design pass]] D5 and D6, decided 2026-10-03"
depends_on:
  - "[[ADR-178 — Scope of the Correction, Not Location of the Manager]]"
  - "[[ADR-040 — Introduce Override Layer]]"
  - "[[ADR-041 — Override Precedence]]"
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
  - "[[ADR-153 — Audit and Accountability]]"
  - "[[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]]"
---

## Status
Accepted

## Context

[[ADR-178 — Scope of the Correction, Not Location of the Manager]] decided where an edit made from inside the composer lands, and decided it for the catalogue: points 1–3 made typing in a catalogue-bound field edit the content record, with **"Override here"** as the explicit act that converts a field to a campaign-local override. Its reasoning was the scope of the correction — *"a typo is wrong everywhere"* — and a trajectory argument: a catalogue default produces no debt when a manager is not thinking about it, so the override rate measures genuine campaign-specific intent.

**That default was built (task-256, task-257, task-224, task-258) and the user tried it on the dev server on 2026-10-03.** Their verdict:

> *"it's too easy to change the approved content in the catalogue directly. So default should be 'override here' and with a click you can change it in the catalog."*

Two findings from that same session show the risk is not hypothetical, and both are about a catalogue write the manager did not mean to make.

- **The audit log recorded a catalogue write followed 0.1 s later by an override holding the pre-typing value** (task-261, module 36, record 65). The field saves on blur ([[Campaign Write Surface - final design pass]] D1); pressing "Override here" blurs the field first, so the typing landed in the catalogue, and the override was then created from the value as rendered before the save. One intent produced two writes, the wrong one first.
- **Campaign detail's module-wide "Overridden by X" made a catalogue edit read as an override** (task-262). Module 39 had one field overridden; a second field was then edited in the catalogue, and the screen still said the module was overridden by the manager. In the user's words: *"if I directly change a content in catalog (because I forgot to click override) the comment still says overridden by …"*.

**The hazard ADR-178 named is the one that occurred.** Its binding condition was *"as long as a manager not accidentally overwrites the catalog while thinking they just changed it in the campaign"*, and it answered that condition with disclosure — a passive reach count on screen before typing. In practice the disclosure did not stop it: a manager working inside a campaign assumes their edits are campaign-scoped, and approved catalogue content — published versions other campaigns will send — was **one blur away from change**. ADR-178 treated a catalogue edit's reach as the point of a catalogue rather than a hazard; that remains true, but reach should be *chosen*, and a default is by definition not chosen.

**This is a supersession rather than a dated addendum, deliberately.** The change is to ADR-178's Decision points 1–3, which the rules forbid rewriting in place, and an addendum that reversed the record's headline would leave a Decision section saying the opposite of what is in force. It is the second supersession in this repository, after [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] over ADR-001 on 2026-09-12. ADR-178 points 4–10 are not in question; they are restated below so this record can be read on its own, each citing ADR-178 as its origin.

## Decision

### What changes: ADR-178 points 1–3

**1. In the composer, typing in a catalogue-bound field writes an override for this module instance.**
The override is per field: typing in one field adds that field to the module instance's override, and every other field keeps showing the catalogue's value. A manager who does nothing special changes this campaign and nothing else.

**2. The catalogue is changed only through an explicit act on one field.**
Each catalogue-bound field offers **"Change in catalogue"**. Choosing it:

- opens **that one field** for a catalogue edit;
- shows **"used by N unsent campaigns" first**, before anything is typed (point 8 below);
- saves the edit to the content record;
- returns the field to its normal state afterwards, so the next keystroke in it is an override again.

The act is one edit to one field. Nothing stays switched on.

**3. The choice still lives in the field's state, never in an editor mode.**
This principle carries over from ADR-178 point 2 unchanged, and it is why the explicit act is per field. **A module-wide switch — "edit this module in the catalogue" — was considered and rejected because it is a mode a manager can forget is on**, which is the failure ADR-178 rejected modes for: invisible state on a frequent action, failing silently.

### What carries over from ADR-178 points 4–10

**4. An overridden field is shown distinctly, with the catalogue value it covers visible** (ADR-178 point 4). [[ADR-041 — Override Precedence]] makes an override win until it is reset, so this is durable state that would otherwise be invisible to whoever opens the campaign next; the covered value is also what makes a reset legible. With override now the default this matters more, not less, because overridden fields will be common. Overridden state is legible **per field**: a surface that reports a module as overridden names which fields are, and a module with none says nothing about overrides (task-262).

**5. A module bound to a decision slot is never overridden, and this is enforced** (ADR-178 point 5). A `ContentOverrideDB` row whose module instance has a non-null `decision_slot_id` is refused at the service layer; an override on a slot de-personalises it, as [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]] implies. The override-or-catalogue fork in points 1–3 therefore exists only for catalogue-bound modules.

**6. Reset works per field and per module, the module reset is confirmed, and anyone who may edit the variant may reset** (ADR-178 point 6). Resetting a field removes its key from `field_overrides`; resetting the module deactivates the row. Reset is a state change, not a delete, and stays attributable through the audit log ([[ADR-153 — Audit and Accountability]]).

**7. An override is scoped to one module instance, and duplicating a variant carries its active overrides** (ADR-178 point 7). The configuration/measurement split inside the row stands: `field_overrides`, `system_content_record_id`, `reason` and `active` copy; `outcome_delta`, `send_instance_id` and `reverted_at` do not; `overridden_by` becomes the person duplicating. Only active rows copy.

**8. The reach of a catalogue edit is a passive count of *unsent* campaigns, with the list on demand and no owner names** (ADR-178 point 8). What changes is where it is attached: **it belongs to the explicit catalogue act in point 2 and is shown before the edit is made**, rather than sitting on every field as the cost of a default. Unsent, because sent campaigns are snapshotted and immune. No owner names, because the composer reports scope, not people.

**9. A reason for an override is optional, offered as presets with free text behind "Other"** (ADR-178 point 9). ADR-178 left the vocabulary open; it was chosen on 2026-10-03 ([[Campaign Write Surface - final design pass]] D6): **"Shorter for this send", "Different tone for this audience", "Out of date for this campaign", "Legal or compliance"**, plus Other. They are stored as text in the existing `reason` column.

**10. `outcome_delta` never appears in the composer** (ADR-178 point 10). Override history and its maturity signal live on their own screen.

### Unaffected and attached to the catalogue act: publish state

**11. A send uses the record's latest published version, so a catalogue edit is shown as unpublished with a one-click Publish** ([[Campaign Write Surface - final design pass]] D5, user decision 2026-10-03). The editor says *"changed since version N was published — sends still use version N"* beside the field, and does not publish on every save, because with autosave that would turn versions into edit history rather than releases. This decision is unchanged by the flip; it now follows the explicit catalogue act rather than the default path.

## Consequences

### Positive

- **Approved catalogue content can no longer be changed by accident from the composer.** Both 2026-10-03 findings were catalogue writes the manager did not intend; with override as the default, the worst outcome of an unthinking keystroke is a local, visible, resettable change to one campaign.
- **A catalogue edit is now always a choice made with its reach in view.** Point 8's count arrives at the moment the manager has said they want to change the record, which is when "should I be careful?" is actually being asked.
- **The default and the manager's assumption agree.** A manager working inside a campaign assumes their edits are campaign-scoped; the system now does what they assume.
- **No mode is introduced.** The explicit act is per field and ends itself, so there is no state to forget, and ADR-178's field-state principle survives the reversal intact.
- **Publish state stays a separate, deliberate step.** A catalogue edit made through point 2 still does not reach a send until published, so there are two explicit acts between a composer and a change to what other campaigns send.

### Negative

- **A genuine typo now takes one more click to fix everywhere.** The manager must choose "Change in catalogue" rather than simply typing; if they do not, the typo is fixed in this campaign only and stays in the catalogue for the next one.
- **ADR-178's trajectory argument is given up deliberately.** A catalogue default produced no debt when a manager was not thinking about it; an override default does, because an override that should have been a catalogue fix leaves the catalogue wrong. That debt is accepted as the price of protecting approved content.
- **Overrides will be more common, so the override history and its maturity signal rise.** A higher override rate after this change reflects the new default, not dissatisfaction with catalogue content, and must not be read as the latter. ADR-178's reading — a falling rate means automation is trusted — still holds as a trend within one default, not across the change.
- **Overridden fields become the ordinary state of a composed campaign**, so point 4's distinct presentation has to stay calm enough to be seen often without becoming noise.
- **Built code and notes describe the old default.** The editor (`frontend/src/screens/CatalogueModule.tsx`, `CatalogueFields`), the design pass's D5 wording and the task-258 notes assume catalogue-first and must change with this record (task-260).

## Notes

- **The rule task-261 exposed survives the flip.** Whichever act is explicit, a pending draft in a field must go where the button says, not where focus last was: choosing "Change in catalogue" with unsaved typing in the field must send that typing to the catalogue only, and nothing to the override. With save on blur this is the shape of bug the explicit act has to be built against, not one the new default removes.
- **Version tokens apply to both writes.** The override write and the content-record write each carry the optional `If-Match` token ([[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]] point 2; task-110, task-256, task-257), so a stale save on either path is a 409 shown on the field rather than a silent overwrite.
- **ADR-178's Negative "creating an override is two actions rather than one" is inverted, not removed**: it is now the catalogue edit that costs the extra action, which is the point.
- **The ADR-040 addendum ADR-178 owed changes in part.** ADR-178 argued against [[ADR-040 — Introduce Override Layer]]'s reasoning that editing the catalogue directly *"would create unintended global changes"*, answering reach with disclosure rather than avoidance. This record moves back toward ADR-040 on that point. The parts of the owed addendum that come from points 5 and 6 — no override on slot-bound modules, reset at two granularities as a state flip — still narrow ADR-040 and [[ADR-041 — Override Precedence]] and are still owed. This record does not write it.
- **No playbook decision-log entry existed for this decision when this record was written.** The source is the user's statement of 2026-10-03 and task-260; `docs/playbook-strategy.md` §5 should gain an entry, and its 2026-10-03 slice-6 status does not contradict anything here.

## Related ADRs

### Supersedes
- [[ADR-178 — Scope of the Correction, Not Location of the Manager]]

### Depends On
- [[ADR-040 — Introduce Override Layer]]
- [[ADR-041 — Override Precedence]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
- [[ADR-153 — Audit and Accountability]]
- [[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]]
