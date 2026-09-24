---
type: adr
status: accepted
topic:
  - architecture
  - audience
  - consent
  - delivery
created: 2026-09-24
source:
  - "Manager Workflow design interview (interview-prep, Cluster 4 Q2–Q4 and Cluster 5 Q2, closed 2026-09-24)"
depends_on:
  - "[[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]"
  - "[[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]"
  - "[[ADR-142 — Autonomous Workflows and the Automation Boundary]]"
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
  - "[[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]]"
---

## Status
Accepted

## Context

`resolve_audience` (`backend/app/audience/service.py:514`) implements `((∪ include) − (∪ exclude)) ∪ pins`, and its docstring records the precedence rule that produces that order, **decided 2026-07-26**: *"a manual pin is a deliberate override and is always included — exclude blocks shape the rule-driven audience but never remove a hand-pinned recipient."* The consent floor is named there as the single exception, and hard suppression is placed on that floor rather than in a regular exclude block so that it stays hard against pins too. The reasoning was coherent: a person who hand-picks a recipient has said something more specific than a rule, and the more specific statement wins.

That rule is now reversed, and the reversal is not a correction of a mistake — it is a change of which way the safety points. A manager who writes an exclusion segment has also said something specific, and what they said is *not these people, because of reason X*. When the two statements collide, the one that keeps mail from going out is the one that costs less to obey wrongly.

**There is no ADR to supersede, and that is precisely why this decision needs one.** The 2026-07-26 rule lives in a docstring and four documentation pages — `[[Flow - Audience resolution]]`, `[[audience]]`, `[[MOC - System Overview]]` and `docs/backlog.md` — plus the Jinja router and `audience_group_detail.html`, whose section heading reads *"Manually added — always included"*. It never reached the architecture record set, so nothing here has to be marked `Superseded by`. A rule that shaped the send path for two months and could only be found by reading a function body is the case this record set exists for, and reversing it into another docstring would repeat the original error rather than correct it.

**The blast radius was measured rather than assumed.** The tests that assert anything about pins assert them against the **consent floor** — `backend/tests/test_consent_gates.py:298-309` and `backend/tests/test_brand_scoping.py:881` — and that behaviour is unchanged by this record. No test was found asserting that a pin survives an *exclude block*. The reversal therefore costs less in test churn than the number of prose documents carrying the old rule suggests, and the documents are where the real work is.

**Two further findings from the same interview belong in this record rather than in one of their own**, because each is load-bearing for the first and would be unreadable apart from it. The `freeze` resolution mode is what would let an exclusion segment be written and then ignored, so removing it is what makes the precedence change mean anything in practice. And `resolve_audience` defaults `channel` to email, which the docstring itself records as having once made a push send unplannable — the audience resolved to nobody and the planner reported "0 consenting recipients" — which is the same class of error as a precedence rule nobody could see: a convenience for the service that silently becomes a lie on screen.

## Decision

**1. An exclusion segment removes a hand-pinned recipient. The resolution order changes.**
`resolve_audience` resolves `((∪ include) ∪ pins) − (∪ exclude)`, and then applies the consent floor exactly as before. Pins join the rule-driven set rather than being unioned back in after the subtraction, so an exclude block reaches them.

The 2026-07-26 rule is reversed in full on this point and in nothing else. **The consent and suppression floor is untouched and stays absolute** — it was never a question of precedence between two people's intentions, it is a legal gate, and the half of the old docstring that places hard suppression there survives intact.

**2. The principle, which is this record's title because it generalises well past audiences: a negative decision outranks a positive one.**
In the user's words: *"a manager who decides that this is the group that shouldn't get it, because of reason X → they shouldn't get it as safety; Shouldn't get it by human beats Should get it by system/human."*

The asymmetry is the argument. **Wrongly including costs more than wrongly omitting.** A person who should have received a mail and did not is a missed opportunity, visible to nobody and recoverable by sending again; a person who should not have received it and did cannot be un-sent, may have been excluded for a reason the sender is not free to second-guess, and is the failure that reaches a supervisory authority rather than a retrospective. Where two instructions conflict and one of them is *no*, the architecture takes the *no* — not because the person saying it is more senior or more recent, but because the error it protects against is the irreversible one.

This is stated as a principle rather than as a property of `resolve_audience` deliberately. Wherever this platform later has to choose between a signal that admits somebody and a signal that refuses them — a followup condition, a suppression interface, a decision-layer eligibility check — the refusal wins, and that is settled here rather than re-argued each time.

**3. There are two kinds of exclusion, and the model does not distinguish them.**
An **exclusion segment** is an attribute, a topic, an interest or a temporary reason. It is editorial and operational: *not the people who already bought this*, *not the B2B list this time*. A **blocklist or suppression entry** is a legal and data-protection matter, and it is not a judgement anybody is invited to revisit.

Both are `kind="exclude"` on an `AudienceRuleBlockDB` today, and this record does not add a second kind. **The distinction is stated here and is not expressible in the schema**, which is an honest description of the state rather than a deferral dressed as one: point 1 gives both kinds the same power over a pin, so nothing currently depends on telling them apart, and inventing a block kind now would pre-empt the suppression data model that [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7 explicitly leaves open. What the distinction governs is what a person may reasonably *undo*, and until there is a block kind, that is a rule people hold rather than one the system enforces.

**4. Sends always re-resolve their audience. The `freeze` mode is removed.**
A send goes to whoever qualifies at the moment it goes out, not to whoever qualified when it was planned. Consent and exclusions are therefore current at the only moment that matters, by construction rather than by configuration, and there is one fewer mode for a manager to understand and for a caller to get wrong.

**The current default is backwards relative to this.** `prepare_send_from_audience` takes `audience_resolution_mode: str = "freeze"` (`backend/app/delivery/service.py:202`) and `SendInstanceDB.audience_resolution_mode` defaults to `"freeze"` as well, so the mode that should never be used is the one a caller gets by saying nothing. `reconcile_executions_to_audience` becomes the always-path rather than the exception it was written as.

**Whether the column is dropped or merely always set is an implementation choice and is not decided here.** Removing it is a hand-written migration in a repository with no Alembic; keeping it is a setting nobody sets. Both satisfy this decision, and choosing between them is a build question rather than an architectural one.

**5. A resolved audience count is meaningless without a channel, and a client always passes one.**
Consent is keyed `(recipient, brand, channel, purpose)` ([[ADR-163 — Per-Channel Consent and Addressability]] point 1), so one group resolves to a different set of people per channel. There is no channel-less number, and no screen may show one.

`resolve_audience(db, group_id, channel=DEFAULT_CHANNEL)` keeps its email default, deliberately, for the service's own convenience where an email audience is being previewed. **That default is a trap for any caller displaying a number, and under this decision a defaulted channel on screen is always wrong.** The channel comes from the variant when a send is being planned; where a manager opens a group with no variant in hand, the screen asks or shows each registered channel, which is a presentation choice this record leaves open. What is settled is that a bare count is not one of the options.

## Consequences

### Positive

- **[[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]] gets stronger rather than weaker.** Its Decision point 3 dissolves one of the three things that looked like a branch by observing that *"skip this step if they have already bought"* is the step's own audience predicate re-resolved at send time, *"which `audience_resolution_mode = "rerun"` already does"*, and its Positive counts `rerun` resolution among the things *"reused as they stand"*. Point 4 removes the choice, so what ADR-169 assumed of a configured send is now true of every send — a conditional argument becomes an unconditional one, with no change to that record.
- **Point 1 is meaningful in practice only because of point 4, and together they close the gap that made exclusion advisory.** An exclusion segment written after a send was planned now removes the recipient, because the rules are re-run at the moment of sending. Under `freeze` the precedence change would have been true of the resolution function and false of the send, which is the worst available combination: a rule that reads as a safety and is not one.
- **The safe direction is the default rather than an option.** A manager who never learns what resolution modes are gets the lawful behaviour, and an adopter who copies this architecture cannot misconfigure their way into mailing people who opted out between planning and sending. That is the same property [[ADR-163 — Per-Channel Consent and Addressability]] bought at the send-time gate, arriving one layer earlier.
- **A principle now exists where three separate cases would otherwise have been argued one at a time.** Exclusion versus pin, suppression versus a website form's push, a followup condition that both admits and refuses — point 2 answers all three the same way, and a future case that wants the opposite answer has something concrete to be wrong about.
- **The reversal is cheap in code and expensive only in prose**, which is the direction worth having. One set operation changes; the test suite's assertions about pins are about the consent floor and stay green.

### Negative

- **"Force add" no longer means force, and the name now contradicts the behaviour.** The phrase is the user's own and it is what the interview called load-bearing; it is also what a manager reads on `audience_group_detail.html`, under a heading that says *"Manually added — always included"*. Every one of those surfaces now promises something the resolver will not honour. Renaming is not optional cleanup here — a control that says *force* and can be overruled is how a manager discovers the precedence rule from a send that reached fewer people than expected.
- **The editorial-versus-legal distinction is stated in point 3 and cannot be expressed in the model**, so it is a rule people hold rather than one the system keeps. Two blocks that mean entirely different things are the same row with the same `kind`, and nothing stops a temporary editorial exclusion being read as a compliance measure or, worse, the reverse. This will stay true until a block kind exists, and the cost of it not existing is paid by whoever has to explain why somebody was excluded.
- **There is no longer any way to say "yes, really, this person".** The pin *was* that mechanism, and point 1 takes the capability away rather than relocating it. That is the intended trade and it is not free: a genuine case — a recipient an exclusion segment catches by accident, who has asked for exactly this mail — is now answerable only by editing the exclusion rule, which changes the audience for everybody. It also matters to [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7, whose three-tier precedence names the pin as the *"explicit, logged act"* that overrides soft suppression; see the Notes.
- **The number a manager reviewed is not necessarily the number that receives.** The audience re-resolves after approval, so a send review screen that shows a precise figure is showing an *as of now* figure that the send will recompute. Saying so is the honest version; presenting a count the system cannot honour is how a review screen becomes a thing managers stop reading.
- **Every document carrying the old rule must be corrected, or it will be read as current.** `backend/app/audience/service.py`'s docstring and inline comment, `[[Flow - Audience resolution]]` step 4, `[[audience]]`, `[[MOC - System Overview]]`, `docs/backlog.md`, the Jinja router and the template each state the 2026-07-26 precedence as fact. Documentation that disagrees with the code is worse than none, and the failure mode is specific: somebody reads *a pin is always included*, relies on it, and is wrong in the direction that sends mail.
- **Re-resolution is now paid on every send rather than on the sends that asked for it.** The consent subquery's cost grows with a recipient's history depth — [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]] already books this per step for cycles — and removing `freeze` removes the only way an adopter had to not pay it. Judged correct, because the thing being bought is lawfulness, but it is a cost and not a saving.

## Notes

- **This is not a supersession and no ADR's status changes.** The rule reversed here was recorded on 2026-07-26 in `resolve_audience`'s docstring and repeated across four documentation pages, the Jinja router and a template. It appears in no ADR's Decision section, so there is nothing to mark `Superseded by ADR-176`. This repository has had exactly one supersession ever — [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] over ADR-001, on 2026-09-12 — and this is deliberately not a second.
- **[[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7 names the mechanism point 1 takes away, and the conflict is real rather than verbal.** §7 makes recipient-level suppression *"soft and overridable by an explicit, logged act"* and identifies that act as *"the existing **pin** mechanism (`resolve_audience`'s `… ∪ pins`), now callable from outside"* — a website form firing *"this recipient must get the masterclass mail"* is its worked example. After point 1 a pin no longer overrides anything that is expressed as an exclude block. **§7 survives only if its soft-suppression tier is not an `AudienceRuleBlockDB` exclude block**, which is exactly the block kind point 3 says does not exist. §7 leaves the data model open by name, so nothing is broken today; what is now constrained is the answer, and the record that settles that data model must not reach for `kind="exclude"`.
- **[[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]] is not contradicted by point 4, despite its title.** Its Decision is about how an audience is *specified* — audience references, audience queries, explicit recipient lists — and says nothing about freezing or re-running one. The collision is in the word "mode", which `audience_resolution_mode` borrowed for an unrelated axis. Recorded because a reader who checks the title and not the Decision will conclude this record reverses that one, and it does not.
- **The Jinja router already describes the new order, in a comment, over code that does the old one.** `backend/app/frontend/router.py:3629-3631` explains the group detail count as *"rule blocks ∪ pins − excludes, consent-gated"*, which is point 1's formula and not what `resolve_audience` did when that line was written. It becomes correct on the day the resolver changes. Worth noting as a warning rather than as a convenience: two places stated the precedence and they did not agree, and nothing caught it.
- **Cluster 4 question 3 is what makes point 1 visible at the moment it matters**, and it is a return-shape change rather than new logic. `resolve_audience` already computes `include_ids`, `exclude_ids`, the pin set and the consent-dropped set, and returns only the final list. A manager who force-added four people and sees *− exclusion segments* learns that their add was overruled; a bare count cannot show that, which is why that gap and this decision belong to the same build. It also bears on [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]: the arithmetic is derived and stays derived, and nothing here asks for resolution results to become durable.
- **No decision-log entry in `docs/playbook-strategy.md` stands behind this record yet.** Its log ends at 2026-09-19 — *"The approval surface shipped, and a person may use the JSON API"* — and the Manager Workflow interview's five clusters closed on 2026-09-21 through 2026-09-24 with no entry written. The source for this decision is the interview document and `docs/backlog.md`'s entry, both cited above; the playbook entry is owed and is logged as such rather than invented here.

## Related ADRs

### Depends On
- [[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]
- [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]]
- [[ADR-142 — Autonomous Workflows and the Automation Boundary]]
- [[ADR-163 — Per-Channel Consent and Addressability]]
- [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]]
