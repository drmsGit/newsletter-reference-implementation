---
type: adr
status: accepted
topic:
  - architecture
  - overrides
  - content
  - decision
  - frontend
created: 2026-09-27
source:
  - "[[Variant Editor - design interview]] Cluster 3, questions 3.1–3.9, and Cluster 2 question 2.6, resolved 2026-09-26"
depends_on:
  - "[[ADR-013 — Content Reference Instead of Content Copy]]"
  - "[[ADR-040 — Introduce Override Layer]]"
  - "[[ADR-041 — Override Precedence]]"
  - "[[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]"
  - "[[ADR-086 — Decision Slots Fail Gracefully]]"
  - "[[ADR-153 — Audit and Accountability]]"
---

## Status
Accepted

## Context

A manager composing a campaign sees a typo in a headline and fixes it. The keystroke can land in the content record or in the override layer, and nothing in the record set said which. [[ADR-040 — Introduce Override Layer]] establishes that both destinations exist and [[ADR-041 — Override Precedence]] establishes which one wins at render time; neither says where an edit made *from inside the composer* goes by default, or how a manager chooses. That gap is what the variant editor interview was written for, and it is the one question in it that no screen sketch could answer.

**The premise that settles it was established a cluster earlier, in question 1.8, and it is a statement about the product rather than about the screen.** An override is an everyday tool — *"unfortunately — the longer a company uses the platform the better they like working with ai and automation so override will be less and less needed"*. Three things follow. The override path must be **fast**, because it is the common case. *"Unfortunately"* is a **design target**: the user wants overrides to become less necessary as automation earns trust. And therefore **override frequency is a maturity signal** — a falling rate means the automation is trusted, a rising one means something is drifting. That reading measures the product rather than a campaign, and it is the first thing in this repository that gives `outcome_delta` a reason to exist beyond curiosity.

**Frequency and deliberateness are in real tension, and this record resolves it rather than splitting the difference.** ADR-040 frames an override as a deliberate, logged deviation. Deliberate and frequent are not contradictory, but a UI tuned for one is usually wrong for the other, and every mechanism below is chosen to keep the act explicit without making it slow.

**Blast radius was put as the tiebreaker and rejected, and the rejection generalises.** By blast radius the default should be the override: a wrong override is local and resettable, while a wrong catalogue edit reaches every composed-but-unsent campaign using that record, including ones somebody else owns. It was rejected because **a catalogue edit being visible to other campaigns is the point of a catalogue, not a hazard.** The hazard is not reach; it is *silence* about reach, which is what the usage count in point 8 answers. Locally-safe defaults were rejected on the same ground from the other side: an override that should have been a catalogue fix is **debt** — the typo stays in the catalogue, the next campaign meets it again, and the override rate rises. Defaulting to the locally-safe option would quietly manufacture the metric the product wants falling.

**Two mechanisms for expressing the choice were rejected before the field-state mechanism was adopted.** A **mode** was rejected as invisible state on a frequent action: an editor a manager is *in* override mode without noticing fails silently — they believe they are fixing one campaign, they have changed the catalogue, and nothing says so. A **dialog on save** was rejected because it taxes the most frequent action in the composer, which is the one thing question 1.8's premise forbids.

**The user attached a binding condition to the mechanism, and it points the opposite way from the obvious risk.** The condition was *"as long as a manager not accidentally overwrites the catalog while thinking they just changed it in the campaign"*. Making the override state visible is the easy half; the danger named here is the reverse — a manager working inside a campaign naturally assuming their edits are campaign-scoped, and silently changing the catalogue by typing in a normal field. **So the catalogue state must announce itself too, and announce its reach.** That is why point 8 is part of this decision rather than a later refinement of it.

**Two pieces of built code contradict what follows, and both are named here so the record is not read as describing the system as it stands.** `ContentOverrideDB`'s own docstring (`backend/app/overrides/db_models.py:24`) names the forbidden case as the intended one — field overrides exist for *"a consistent headline across the personalized picks"* — and `resolve_module_variables` applies `field_overrides` **after** slot resolution, so the capability works today. Point 5 reverses that intent. And `backend/app/campaigns/duplication.py:147` groups content overrides with resolutions, snapshots, send instances and content versions as *"a record of something that happened, and a copy has no history — reproducing them would fabricate decisions, publications and sends."* Point 7 reverses that: the rationale is sound and is applied to the wrong unit.

**A worry raised against module-instance scope was dissolved by the field model rather than accepted.** The same content record appearing in two modules of one variant looked like a trap — fix the hero's headline and the listing below still shows the old one, inside one email where a reader sees both. It is not a trap, because a full-width hero takes `headline_long` and a 50:50 module takes `headline_medium`: **they do not share a field**, so there is nothing to propagate and the two are *meant* to differ. The concern was an artefact of imagining one shared `headline`, which the size vocabulary recorded in [[ADR-177 — A Field Is Defined Once, Required Per Module]] had already removed.

## Decision

**1. An edit made while composing lands in the content record by default. The question is the scope of the correction, not the location of the manager.**
*"Content record, typo is wrong everywhere."* The question a person answers instantly, and that no inspection can answer for them, is *"is this wrong everywhere, or different here?"* A typo is wrong everywhere; *"shorter copy for this send"* is different here. **Where the manager happens to be standing when they notice is not evidence of either.** This honours the original requirement literally — a manager does not switch tabs to fix the catalogue, they fix it from the composer.

**2. The choice lives in the field's state, never in the editor's mode.**
A normal field shows the catalogue value, and typing in it edits the content record. **"Override here"** is an explicit act that converts *that field* into a visibly different input, with the catalogue value still shown beneath it; from then on, typing writes the override. No mode to be in, no dialog on save, and the state is legible at a glance rather than remembered.

**3. The catalogue is therefore the default.**
A field is normal until somebody converts it. The default is the one a manager gets without choosing, which is why it matters that it is also the one point 1's trajectory wants: a catalogue default produces no debt when a manager is not thinking about it.

**4. An overridden field is shown distinctly, with the value it covers visible.**
[[ADR-041 — Override Precedence]] makes an override win *"until it is deleted or reset"*, so this is durable state that would otherwise be invisible — a manager opening the campaign next month sees a headline with no way to know it is not the catalogue's. Showing the covered value is also what makes reset meaningful, since a manager can see what reverting would restore. The distinct field state is the whole of the UI requirement; no additional warning is needed anywhere.

**5. A module bound to a decision slot may never be overridden, and this is enforced rather than conventional.**
*"Decision slots shouldn't get override. It's personalized, so pinning a headline or body text would 'de-personalize' it and if you allow 3 results this would mean 3 times the same overridden content."* An override on a slot defeats the purpose of the slot, and once `max_results` does anything it produces several personalised picks wearing one pinned headline. **A `ContentOverrideDB` row whose module instance has a non-null `decision_slot_id` is refused** at the service layer. An override attaches to a module bound to a content record and to nothing else, so the edit-versus-override fork exists only for catalogue-bound modules.

**6. Reset works at two granularities, and anyone who may edit the variant may reset.**
`ContentOverrideDB` holds one active row per module instance, guarded by a partial unique index, carrying a `field_overrides` dict of many fields — so the granularities do not line up one-to-one with point 2's per-field state.

- **Reset one field** removes that key from the dict; if the dict empties, the row deactivates.
- **Reset the module** flips `active` to `False` wholesale — *"drop everything I changed here"*. This one is easy to fire by accident, so a confirmation is warranted where one on a single field would not be.

Reset is a state change and not a delete; nothing is destroyed, which is what makes an override history screen possible. **Anyone who can edit the variant may reset.** `overridden_by` is NOT NULL, so a reset stays attributable without being restricted — restricting it to the author recreates the holiday problem the composer's advisory lock was shaped to avoid.

**7. An override is scoped to one module instance, and duplicating a variant carries its active overrides.**
Module-instance scope is correct and needs no propagation rule, for the reason in Context. What changes is duplication. **An override is dual-natured**: a record of what happened *and* live configuration that `get_active_content_override` reads on every render. Dropping it on duplication means the copy **renders differently from its original**, which is precisely wrong for the duplicate-to-repeat workflow. **The line belongs inside the row, not around it:**

| Copies — configuration | Does not copy — measurement and attribution |
|---|---|
| `field_overrides` | `outcome_delta` — it measures a send that happened |
| `system_content_record_id` | `send_instance_id` — likewise |
| `reason` | `reverted_at` — the copy has not been reset |
| `active = True` | `overridden_by` — becomes the person duplicating |

Only rows that are already **active** copy; a reset row is purely history, and reproducing it would fabricate exactly what `duplication.py`'s docstring warns about. `overridden_by` becomes the duplicator rather than the original author, because carrying the original name forward attributes to them an act they did not perform in a campaign they may not know exists — the same fabrication, arriving through the one field the docstring did not consider.

**8. Editing a catalogue value in the composer shows a passive count of *unsent* campaigns affected, clickable to a list, with no owner names.**
Passive rather than on first keystroke or on save, because the reach is then on screen *before* a manager types and editing can never be a revelation — which is the exact failure mode the condition in Context names. A notice on keystroke or a dialog on save both arrive after the manager has committed, and a dialog would tax the default path with a confirmation on every typo fix.

The count is of **unsent** usages, not of usages. Sent campaigns are snapshotted and immune, so a raw *"used in 12 campaigns"* overstates the blast radius, and a number a manager learns to distrust is worse than no number. Count first, list on demand: a number answers *"should I be careful?"*, which is asked every time; the list answers *"careful about what?"*, which is not.

**Owner names are excluded.** Naming them would mean resolving an actor identifier to a person on a composer screen, and [[ADR-153 — Audit and Accountability]] point 5 deliberately stores internal identifiers rather than contact details. **The composer reports scope, not people** — who is affected is the approval inbox's question and the audit log's, on surfaces built to answer it.

**9. A reason for an override is optional, offered as presets with free text behind "other".**
Nothing is required; a manager may override and say nothing, which keeps the optional-everywhere rule intact. What changes is the *shape* of the answer when one is given, and the motive is **instrumentation, not accountability**: a falling override rate does not say what to fix, and a free-text box that is empty most of the time produces nothing analysable. A preset is one click rather than typing, so it does not tax the everyday path, and it is machine-readable, so the trend becomes analysable rather than anecdotal. `reason` is `String(1000), nullable=True` and already exists; a preset is a value in that column.

**10. `outcome_delta` never appears in the composer.**
*"It must stay a focused tool."* The composer already carries the field state, the catalogue reach count, the reason presets and the slot summary. A historical performance indicator is how a focused tool becomes a dashboard. Override history — including the maturity signal — lives on its own screen, and when a comparison between overridden and unoverridden content is built, it gets a monitoring screen rather than leaking back into the editor.

## Consequences

### Positive

- **The default now serves the trajectory the product is aiming at.** A manager who never thinks about where a keystroke goes fixes the catalogue, so the override rate measures genuine campaign-specific intent rather than accumulated unfixed typos — which is the only condition under which point 1's maturity signal means anything.
- **The state a manager is in is on screen rather than in their head.** Point 2 removes the entire class of failure where somebody edits the wrong thing and nothing tells them, and point 4 keeps it removed a month later when they reopen the campaign.
- **The cost of the catalogue default is paid in visibility rather than in caution.** Point 8 puts reach on screen before the first keystroke, so the answer to *"is this edit bigger than it looks?"* is available at the moment it is asked and never arrives as a surprise afterwards.
- **A duplicate renders like its original.** Point 7 fixes a live defect in the duplicate-to-repeat workflow, and it does so by drawing the configuration/history line inside the row, which leaves `duplication.py`'s rationale intact everywhere else it applies.
- **Personalisation cannot be silently defeated.** Point 5 makes the constraint structural, so the `max_results` work cannot be undermined by a capability that exists and currently works.
- **Reset is attributable without being owned.** Point 6 gets accountability from `overridden_by` and availability from letting anyone reset, rather than trading one for the other.

### Negative

- **Creating an override is two actions rather than one** — convert the field, then type. Accepted knowingly, mitigated by making the conversion a keystroke, and paid once per field rather than once per edit.
- **A manager can change a colleague's unsent campaign knowing only that four campaigns are affected, not whose.** This is the accepted cost of excluding owner names, and the compensating surfaces are the approval inbox and the audit log, neither of which the composer replaces.
- **A fixed reason vocabulary is always slightly wrong**, and presets invite people to pick the nearest option rather than the true one, producing data that looks better than it is. The "other" escape hatch limits this and does not remove it.
- **Point 5 removes a capability that works today**, so any adopter relying on a pinned field across personalised picks loses it, and the record's own docstring has to be corrected along with the code.
- **The strongest available lever for reducing overrides is deliberately not pulled.** Feedback at the point of decision would be the most direct way to make a manager reconsider, and it is refused so the composer stays a focused tool — the reduction has to come from the history screen and from the catalogue default instead.
- **Point 5 must be implemented before or with `max_results`, which is a sequencing constraint this record imposes on work it does not own.** The prohibition is correct today and merely tidy; once a slot returns several records it is the difference between personalisation and a pinned headline repeated. The constraint precedes the feature that makes its race routine. The rest of this record can trail implementation safely.
- **The unsent-usage count is a query that does not exist.** It is one join — module instances to variants to campaigns, filtered to unsent — and cheap for a single record, but it is new work on the default path rather than on the exceptional one.

## Notes

- **This narrows [[ADR-040 — Introduce Override Layer]] and [[ADR-041 — Override Precedence]] without contradicting either, and a dated addendum is owed on ADR-040.** ADR-040's Context reasons that *"editing the catalog directly … would create unintended global changes"*; this record accepts the reach and answers it with disclosure rather than avoidance, adds that the override layer does not extend to slot-bound modules at all, and settles ADR-040's own Negative that *"preview and usage visibility"* becomes more important. ADR-041's precedence rule is untouched — an override still wins until reset — and what this record adds is that reset has two granularities and is a state flip rather than a deletion, which is a refinement of that record's *"deleted or reset"* wording. **The addendum text is reported with this record rather than applied here**, per the rule that a new record does not edit an accepted one.
- **This is not a supersession and no ADR's status changes.** This repository has had exactly one supersession ever — [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] over ADR-001, on 2026-09-12 — and this is deliberately not a second. Both records being narrowed remain in force as written.
- **Point 5's *human beats system* reading sits on a different axis from [[ADR-176 — A Negative Decision Outranks a Positive One]] and is deliberately not folded into it.** ADR-176 is about which of two conflicting instructions wins when one of them refuses; point 5 is about a capability that may not be exercised at all, because exercising it defeats the feature it attaches to. The addendum owed to ADR-176 concerns a different question from the same interview, and is not this record's business.
- **Point 5 is what [[ADR-086 — Decision Slots Fail Gracefully]] and [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]] imply and never stated.** A slot that may be hidden per recipient cannot coherently carry a field pinned for everyone, and the optional heading a slot-bound module may now carry is conditional on the slot resolving for exactly ADR-086's reason.
- **The preset vocabulary is explicitly not settled here.** The sketch offered during the interview — *too long · wrong tone · factually wrong · campaign-specific · other* — is a starting point for the build and not a decision, and it should be revisited once there is real volume rather than guessed at more precisely now. Whether the column stores prose or a short constrained code is a schema question that follows from wanting the analysis to be cheap, and is left to the build.
- **`outcome_delta` is further from working than point 10 needs it to be, and that is a finding rather than a decision.** `record_outcome_delta` (`backend/app/overrides/service.py:221`) exists with a route and careful merge semantics, and only the router calls it — nothing in the insight or engagement layer computes a value. The deeper gap is that a *delta* presupposes a baseline, and the baseline is the unoverridden version that **was not sent**. Measuring it needs a holdout, a counterfactual or an A/B between overridden and unoverridden content, and none of the three exists or is specified. Point 10 is stable rather than provisional because the monitoring screen is decided now, for whenever that design arrives.
- **`docs/playbook-strategy.md` carries the 2026-09-27 decision-log entry behind this record**, under *Variant Editor Design Interview (ADR-177) — interview closed*, which states the two-part answer, the rejected blast-radius argument and both code reversals. Nothing here departs from it.

## Related ADRs

### Depends On
- [[ADR-013 — Content Reference Instead of Content Copy]]
- [[ADR-040 — Introduce Override Layer]]
- [[ADR-041 — Override Precedence]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
- [[ADR-086 — Decision Slots Fail Gracefully]]
- [[ADR-153 — Audit and Accountability]]
