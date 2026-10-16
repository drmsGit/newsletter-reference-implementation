---
type: adr
status: accepted
topic:
  - architecture
  - ai
  - governance
created: 2026-07-31
modified: 2026-10-16
source:
  - "AI Layer design interview (interview-prep, 2026-07-27 – 31), Cluster 1"
depends_on:
  - "[[ADR-003 — Human-Guided Marketing, AI-Optimized Delivery]]"
  - "[[ADR-040 — Introduce Override Layer]]"
  - "[[ADR-041 — Override Precedence]]"
  - "[[ADR-080 — Human-governed Taxonomy Before AI Selection]]"
  - "[[ADR-082 — AI May Recommend but Not Publish]]"
  - "[[ADR-085 — Decision Resolution Should Be Optionally Explainable]]"
enables:
  - "[[ADR-141 — In-App Assistive AI Actions]]"
  - "[[ADR-142 — Autonomous Workflows and the Automation Boundary]]"
  - "[[ADR-143 — AI-Assisted Development Boundary]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
---

## Status
Accepted

## Context

ADR-003 set the philosophy — human-guided marketing, AI-optimized delivery; **AI
proposes, human governs**. ADR-080/081/082 already govern AI *inside the decision
layer* (a human-governed taxonomy, AI ranks only within governed candidate sets,
AI may recommend but not publish). But those are point solutions. The product now
needs a **general way to add AI capabilities across the whole system** — subject
lines, tagging, content suggestions today; autonomous workflows and dev-time
assistance later — without each one re-inventing trust, audit, prompt ownership,
and governance.

Two failure modes to avoid:

- **AI in the architecture core.** Baking a model into the core makes it
  un-swappable and couples the reference architecture to a vendor — the opposite
  of the provider-adapter stance (ADR-100/101) the rest of the system takes.
- **"Everything is a pending proposal."** Routing every AI action through the
  override/approval layer forces the system to evaluate *all* campaigns rather
  than the one source it acted on — a real token and performance cost — and buries
  managers in approvals. A trust layer does not have to mean an approval queue for
  everything.

A third reality: a company may want **no AI at all** (e.g. a client whose new CDP
already contains AI and who wants none in this architecture). The layer must be
fully optional, per capability.

## Decision

**1. AI is a pluggable capability behind existing seams — never the core.**
AI capabilities plug in through the two patterns the system already uses: the
**provider-adapter** pattern (as `DeliveryProvider`, ADR-100) and the
**plugin-registry** pattern (as the decision-strategy registry). A model is added
by a file, not by editing the core. A company that never enables AI loses nothing
structural — the platform is complete without it.

**2. The trust guarantee is "reversible + audited + a human can interfere" — not
"everything is a pending proposal."**
**Direct write is the default.** Trust comes from the fact that AI actions are
reversible (via the Override Layer, ADR-040/041), fully audited (point 5), and
interruptible by a human at any time — *not* from making every action wait in a
queue. This reframes what "trust layer" means for this architecture: govern the
blast radius, not every keystroke.

**3. Approval is a per-task setting, not one global rule.**
Each task declares its approval behaviour — **auto-apply** vs **require-approval**
— chosen by the task's risk and implementation, not a system-wide switch.
Auto-apply is the default; approval-gating is opt-in per company/task. This gives
**graduated trust**: a company can start a task approval-first and flip it to
auto once it trusts the output.

**4. Prompts are frontend-editable and content-style versioned — the manager owns
them.**
A dev cannot meaningfully *evaluate* a marketing/BI prompt, so "manager writes it,
dev implements it blind" is backwards. Structure:
- **One (minimal) file per AI task = the dev-owned technical *scaffold*** — what it
  reads, the output shape, where the result lands (the firm contract, ADR-144).
- **The prompt + guards live in frontend settings** — manager-owned, versioned and
  published like content. The scaffold *references* them; it never embeds them.

**5. Every AI action is audited with the standard fields plus the prompt-version
id.**
Log inputs / model / output / timestamp / approver-if-gated, **plus the published
prompt-version id** used. Because the live prompt lives in the DB (point 4), the
version id is what makes a decision reproducible — no need to copy the full prompt
text into every row; the id resolves it. (Same event-sourced, re-derivable spirit
as ADR-132 and the explainability of ADR-085.)

**6. Guardrails are a company-editable "DON'T EVER" file plus per-prompt guards —
not a fixed "not-AI" list.**
Companies want full AI capability and add their own limits; a hard-coded list of
things AI may never touch is the wrong shape. Instead, a **global,
company-editable "DON'T EVER" guardrail file** holds negative constraints, and
each prompt carries its own guards in settings. These guardrails also protect
against a bad or unsafe prompt edit (point 4).

**7. A global kill switch always exists; enablement is granular and the company's
call.**
Because the system is open-source, a company that doesn't want AI simply doesn't
enable/implement it — and *how much* AI, per capability, is their decision. On top
of that, a **global kill switch always exists** for emergencies (data breach, a
model behaving unexpectedly).

## Consequences

### Positive
- AI is swappable and optional; the reference architecture stays vendor-neutral
  and complete without it.
- Trust is enforced by reversibility + audit + human interruption, so the default
  path (direct write) is fast and doesn't drown managers in approvals.
- Prompt ownership sits with the people who have the domain expertise; devs own
  only the technical scaffold.
- Every AI action is reproducible from its prompt-version id.
- A company can dial AI from "none" to "fully auto per task" without code changes.

### Negative
- Two moving parts per task (dev scaffold + frontend prompt/guards) instead of one
  — a small coordination cost, deliberately taken to put prompts where the
  expertise is.
- "Reversible + audited" shifts responsibility onto the audit trail and the
  override layer being correct; if either is weak, the trust guarantee weakens.
- A company-editable "DON'T EVER" file is only as good as what the company writes
  in it.

## Notes

- **Three modes.** This foundational layer is shared by all three AI modes:
  **A** — in-app assistive button actions ([[ADR-141 — In-App Assistive AI Actions]]);
  **B** — autonomous workflows / the automation boundary
  ([[ADR-142 — Autonomous Workflows and the Automation Boundary]], mostly n8n);
  **C** — AI-assisted development, never prod
  ([[ADR-143 — AI-Assisted Development Boundary]]). Cross-cutting data,
  model, cost, and PII governance is [[ADR-144 — AI Data and Model Governance]].
- **Client stance.** For a company that wants no AI in its architecture, the honest
  answer is that AI still helps through *different approaches* (recommendations,
  the feedback loop) — but whether to enable any of it stays entirely their choice
  (point 7). This ADR makes "off" a first-class configuration, not a fork.
- **Status.** Decided in the design interview; implementation is phased (Mode A
  first — see ADR-141). Marked accepted as a design decision, not as shipped code.

## Addendum 2026-10-08 — The three modes are named by what they do

Prompted by task-97, and decided by the user in chat on 2026-10-08, one
question at a time. Points 1–7 stand. This addendum changes what the three modes
in Notes are called, not what they are or what they may do.

**What was found.** The Notes above name the three modes by letter: **A**
([[ADR-141 — In-App Assistive AI Actions]]), **B**
([[ADR-142 — Autonomous Workflows and the Automation Boundary]]) and **C**
([[ADR-143 — AI-Assisted Development Boundary]]). The roadmap in
`docs/playbook-strategy.md` independently uses Phase 4A / 4B / 4C, where 4A is
the playbook's chapter structure and voice. The two sets share nothing but the
letters. On 2026-08-07 the user concluded that Phase 4A was finished because
the subject-line feature, which is Mode A, was; that misread cost a planning
session. A reader of the published material would meet both vocabularies too.
On 2026-10-08 the mode letters appeared in 12 ADRs, in the Decision section of
9 of them, and also in the playbook, queue tasks, business docs, two MOCs and
backend code comments.

**1. The modes are named by function.**

- **Assistive** — was Mode A, [[ADR-141 — In-App Assistive AI Actions]]:
  in-app actions a person asks for and accepts.
- **Autonomous** — was Mode B,
  [[ADR-142 — Autonomous Workflows and the Automation Boundary]]: workflows
  that act without a person in the loop, inside the automation boundary.
- **Development** — was Mode C, [[ADR-143 — AI-Assisted Development Boundary]]:
  AI-assisted work on the codebase itself.

The ADR titles already said this. The letters were the trap.

**2. Dated records keep the letters, and this addendum is the key.** This is
the user's rule of 2026-10-05 for the product rename
(`docs/business/decisions/naming-brand-tarrow.md`, its 2026-10-05 entry; the
`DATED` list in `backend/scripts/rename_product.py`): ADRs, interview prep,
business decisions, the queue, the playbook and other records of a date keep
the wording they were written with. An Accepted ADR's Decision is never edited
either. A reader who meets "Mode A", "Mode B" or "Mode C" in an ADR or any
other dated record looks it up here.

**3. Living files use the function names, and a test keeps it so.** Code
comments and docstrings, the living business docs in `docs/business/`
(BRIEF, ASSUMPTIONS, BETA-SCOPE) and the MOCs say Assistive, Autonomous and
Development. A test, `backend/tests/test_mode_names.py`, keeps the letters out
of living files. It is built from the pieces of the product rename's
living-file scan: the same tracked files (`rename_product.tracked`), the same
`DATED` list (`rename_product.is_dated`), the same text suffixes and the same
stripping of ADR links. So "living file" means the same thing for both
renames. It does not call `rename_product.retired_name_hits` itself, because
that function matches whole words and would miss a spelling like
"Mode-A-vs-decision-slot". The test has its own pattern,
`\bModes?[ -][ABC](?![a-zA-Z])`. It catches "Mode A", "Mode-A", "Mode A/B/C"
and "Modes A and B", but not "Mode Boundary" or a lower-case "mode". Three more
files are records of a date, so they join the `DATED` list and keep their
letters: the interview log (`docs/business-interview.md`), the weekly summary
(`docs/weekly-summary.md`) and the code-slimmer report
(`docs/architecture/code-slimmer-report.md`).

**Rejected.** Rewriting the letters in all ADRs, the playbook and open tasks
was rejected: for a single rename it would break both the rule that an Accepted
ADR's Decision is never edited and the 2026-10-05 rule that dated records keep
their wording. Renaming the roadmap's Phase 4A / 4B / 4C instead was rejected
too: the playbook is a dated record as well, and the mode letters would stay
ambiguous.

**Consequences.**

- **Positive.** New material cannot collide with the roadmap's phase letters.
  A reader has one place to translate the letters.
- **Negative.** For as long as the ADRs exist, a reader meets two vocabularies
  and needs this key. The guard test fails a living file that quotes "Mode A",
  even when it is quoting an ADR on purpose: the file must be reworded, or it
  is a dated record and belongs on the `DATED` list.

Built the same day, under task-97: the three files joined `DATED`, living files
were reworded, and the guard test runs in the suite. Nothing here changes the
Decision section above.

## Addendum 2026-10-16 — A task may have no held form

Prompted by the final-design pass of task-368 ("AI drafts a content record from
a source and proposes its categories"), decided by the user on 2026-10-16, one
question at a time. Point 3 stands for every task whose output can be held. This
addendum covers a task whose output cannot.

**What was found.** Point 3 assumes that any task's output can be held for an
approver. The content draft task ([[ADR-141 — In-App Assistive AI Actions]],
addendum of the same date) has nothing to hold. Its output only ever appears in
a panel where a person takes it themselves, and taking it is that person's act.

**1. A task may declare that it has no held form.** The task declaration says
so. Settings shows that statement in place of the auto-apply / require-approval
switch, and the server refuses `require_approval` for that task, with a reason.
Every existing task keeps the switch; the subject/preheader task still honours
it.

**2. `content_draft` is the first such task.** Building a held form for it later
is a new decision, not a setting.

**Why.** The user chose not to build an approval path for drafts. A draft never
publishes and never reaches recipients without further human acts: publishing,
readiness ([[ADR-174 — Channel Readiness Is Asserted, Not Computed]]) and machine
ready ([[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]]).
A second approval layer in front of those would add clicks, not safety. This is
the reasoning of the Context above, which rejects routing every AI action
through approval.

**Consequences.**

- **Positive.** Settings no longer offers a switch that could not do anything
  for such a task, and the server cannot be told otherwise.
- **Negative.** A company that wants every AI output approved cannot have that
  for drafts without a new decision. For drafts, the guarantee rests on the
  human acts that follow and on the audit of point 5.

Nothing here changes the Decision section above. Point 3 stands as written.

## Related ADRs

### Depends On
- [[ADR-003 — Human-Guided Marketing, AI-Optimized Delivery]]
- [[ADR-040 — Introduce Override Layer]]
- [[ADR-041 — Override Precedence]]
- [[ADR-080 — Human-governed Taxonomy Before AI Selection]]
- [[ADR-082 — AI May Recommend but Not Publish]]
- [[ADR-085 — Decision Resolution Should Be Optionally Explainable]]

### Enables
- [[ADR-141 — In-App Assistive AI Actions]]
- [[ADR-142 — Autonomous Workflows and the Automation Boundary]]
- [[ADR-143 — AI-Assisted Development Boundary]]
- [[ADR-144 — AI Data and Model Governance]]
