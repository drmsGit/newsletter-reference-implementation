---
type: adr
status: accepted
topic:
  - architecture
  - ai
  - governance
  - privacy
created: 2026-07-31
modified: 2026-10-11
source:
  - "AI Layer design interview (interview-prep, 2026-07-27 – 31), Cluster 5"
depends_on:
  - "[[ADR-140 — AI Capability Layer]]"
  - "[[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]"
  - "[[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]"
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
  - "[[ADR-101 — Provider Capabilities Are Explicit]]"
enables:
  - "[[ADR-141 — In-App Assistive AI Actions]]"
---

## Status
Accepted

## Context

ADR-140 established AI as a pluggable capability. Four concerns cut across *every*
AI capability — Mode A now, Modes B and C later — and belong in one place rather
than being re-decided per task: **which model** runs a task, **what data** the
model sees, **what it costs**, and **where a task's configuration lives**. This
ADR fixes those cross-cutting rules so individual task ADRs (starting with
ADR-141) inherit them.

A guiding constraint: we are building a reference architecture, **not offering
data-protection or legal advice**. Where a choice is a legal/compliance judgement
(model provider, data residency), the platform's job is to make the safe default
easy and the exposed choice explicit — not to make the call for the company.

## Decision

**1. The model is an adapter — `AIProvider`, mirroring the send adapter.**
Add or swap a model by a file, exactly as the outbound `DeliveryProvider`
(ADR-100/101) makes the ESP swappable. Ship **two worked examples — Claude and one
EU-hosted model** — so "a GDPR-friendly setup is possible" is *demonstrated*, not
merely claimed. (The Claude integration here is Claude-the-model via the Anthropic
API with its own key — distinct from Claude Code, the dev-time assistant of Mode
C.)

**2. Per-task model choice is the documented direction; the POC ships one model +
a guide.**
The POC uses one model plus a **"how to add and connect more models" guide** (the
same shape as the swap-send-provider guide). Per-task / expert-model selection
(a creative model for copy, a coding model for dev tasks, a cheap model for
workflow steps) is real and goes in the ADR as the **direction**, not the POC
build.

**3. No EU / residency warning flag.**
We are not data-protection experts and will not take on that liability. Provider
and data residency are the **company's call**; the platform defaults to data
minimisation (point 4) and stays out of the legal determination. We do not ship a
UI flag that purports to tell a company whether a given provider is
"GDPR-compliant."

**4. PII is a per-task setting, default "no raw PII to the model."**
By default the AI works on **IDs, signals, and content**, and personalises via
**merge variables** (`{{first_name}}`, reusing the merge context of ADR-005): the
platform fills the real value **locally at render**, so identities never leave the
system. A task may be **explicitly opted up** to see raw fields (e.g. an in-system
Mode-A task operating under a DPA) — that is the company's deliberate,
**logged** choice. Safe by construction; more exposure is always a deliberate act,
never a default. (This is the AI-facing expression of ADR-004.)

**5. Cost governance = a spend cap with a configurable, role-bound buffer,
enforced as a pre-call gate.**
A **spend cap is primary** — **warn first, then hard stop** — scoped **per
role/user**. Enforcement (detail carried from Cluster 2 / Q11b):
- Each task declares its own output ceiling (the model's `max_tokens`), so the
  platform can compute the task's **worst-case total** (`count_tokens(input)` +
  output ceiling) **before running**.
- The hard stop is a **pre-call gate**: the platform **refuses to start** any task
  whose worst-case wouldn't fit under the remaining cap. So a stop always lands
  *between* tasks, never mid-task — nothing is spent on a task that can't finish
  (no "paid, got nothing").
- If a running task hits its own output ceiling, the **partial result is still
  shown** (display ≠ commit), never silently discarded.
- The **buffer is configurable** (the company is filling in its token limit
  anyway) and **strictly bound to user role/permission**.
- There is **no provider "total budget" knob** — the worst-case ceiling is computed
  by us, which is more reliable than depending on a provider feature. (A *soft*,
  model-paced budget exists — `task_budget`, agentic-loop-only — noted as the
  Mode-B direction, not a stage-1 build.)
- The **per-run cost estimate is dropped from the UI** (a manager is unlikely to
  use it; it is open code for any company that wants it). The UI shows **total
  cost/tokens against the cap**.
- **Phase-1 MVP stops here.** An opt-in **overage** mode ("keep going, pay per
  token") and richer controls are a future **"AI extra package."**

**6. The task file is a firm contract for the scaffold; the prompt is config.**
The per-task file is a **firm contract for the technical scaffold** — inputs,
output type, where it writes — and it stays clean *precisely because* the messy,
domain-specific part (the prompt + guards) is lifted OUT of the file into
frontend-versioned settings (ADR-140, point 4). So: **firm contract for the
scaffold, config for the prompt.**

## Consequences

### Positive
- The model is swappable like the ESP; "GDPR-friendly is possible" is proven with a
  shipped EU example, not asserted.
- PII minimisation is the default and safe by construction; more exposure is a
  logged, deliberate opt-up.
- Spend can't overrun: the cap is enforced before a task starts, per role/user,
  and a near-limit stop never wastes an in-flight task.
- The platform takes no legal/compliance liability it isn't qualified to hold.
- Task files stay small and reviewable; prompt churn lives in versioned settings.

### Negative
- Merge-variable personalisation is less flexible than handing the model raw
  fields — a deliberate trade for privacy; tasks that genuinely need raw PII must
  opt up under a DPA.
- Per-task model selection is documented but not built in the POC, so early
  adopters run one model until they wire the guide.
- Default token weights, cap thresholds, and buffer sizes are judgement calls that
  need real usage to tune.
- "No residency flag" means a company must make its own provider/compliance call —
  intentional, but it is work the platform won't do for them.

## Notes

- **The second worked adapter is not a blocker — decided 2026-09-19.** §1 commits to *two* worked model
  examples so that "GDPR-friendly is possible" is demonstrated rather than claimed, and only one is
  built. The user's position, adopted: the **mechanism** is proven — an adapter is a dropped file behind
  an interface, and there is no reason to believe a second provider differs as long as it exposes an
  API. One will be tested; nothing waits on it.

  **What that does and does not settle, stated so the claim stays honest.** It settles the *engineering*
  question, which was never really in doubt after the Claude adapter shipped against a real ledger and a
  pre-call spend gate. It does not settle the *demonstration* — §1's two examples were about showing an
  EU-hosted option is real, not about proving a second adapter can be written. So the honest phrasing
  until one is connected is "the architecture admits an EU-hosted model and one has not been run", which
  is weaker than §1 intended and stronger than nothing.

- Applies to all three AI modes. Mode A ([[ADR-141 — In-App Assistive AI Actions]])
  is the first consumer; Mode B
  ([[ADR-142 — Autonomous Workflows and the Automation Boundary]]) and Mode C
  ([[ADR-143 — AI-Assisted Development Boundary]]) inherit the same model adapter,
  PII line, and cost cap.
- The cost-cap enforcement here is the governance rule; ADR-141 defines only the
  Mode-A **cost *visibility*** UI (total vs cap).
- **Status.** Decided in the design interview; the model adapter, EU worked
  example, and cap enforcement are phased with the Mode-A build. Accepted as a
  design decision, not as shipped code.

## Addendum 2026-10-09 — the AI budget is one company pot, it refills each month by default, and every run records who started it

Prompted by finding P2-H2 in [[business-interview-baseline]] ("The spend cap is a
lifetime budget; ADR-144 says per role/user"), decided by the user in the 2026-10-09
interview review and logged in the [[playbook-strategy]] decision log under
"2026-10-09 — Business findings decided one by one in the interview review". Point 5's
mechanism stands as written: warn first, then hard stop, enforced as a pre-call gate.
This addendum settles two things point 5 left loose: whose budget it is, and over what
period it is counted. The code facts below were checked on 2026-10-09.

**Point 5 says "per role/user", and a later record decided one pot without saying so
here.** Point 5 scopes the cap *"per role/user"*, and the third `### Positive` bullet
repeats it: *"the cap is enforced before a task starts, per role/user"*.
[[ADR-150 — Tenancy and Access Model]] decided otherwise in its 2026-09-15 addendum on
permission scope, where it explains why `ai.run` is platform-level: *"the budget is one
company-wide pot with one ledger and one bill"*. It also says *"This is not deferred
indecision"*: the platform must not assume how a company wants to share a budget across
brands. That addendum cites this record's §5 as the source of the pot, but this record
was never amended to point back. A reader of ADR-144 alone still finds a per-user cap.

**What the build does.** The build followed ADR-150, not the wording here, and it added
a property neither record decided: the budget never refills.

- `tokens_used` in `backend/app/ai/service.py:89-104` sums the tokens of every billable
  run in `ai_runs`. It has no time window and no filter by person or role. The pre-call
  gate measures what remains against that sum (`:196-199`).
- The cap itself is two token figures, `warn_tokens` and `hard_stop_tokens`
  (`get_ai_spend_cap`, `backend/app/settings/service.py:95`), with no period beside
  them.
- `AIRunDB` (`backend/app/ai/db_models.py:47-72`) records a run's task, prompt,
  provider, model, tokens, target and time. It does not record who started the run.

So the budget is a lifetime allowance. Once it is spent it never refills, and a company
that budgets monthly cannot say so. Spend also cannot be split by person afterwards,
because the column to split on was never written.

**The decision.**

**1. The budget is one company-wide pot.** This is ADR-150's 2026-09-15 decision, and
this record now points to it. Point 5's "per role/user" and the third `### Positive`
bullet are read accordingly: the cap is one budget for the whole company, and no person
or role has a budget of their own. Per-brand budgets stay where ADR-150 left them: a
playbook article for a company that needs them, not a build commitment.

**2. The pot resets each calendar month by default, and the period is a company
setting.** The company chooses the period, for example month, quarter or lifetime.
Month is the default. Lifetime, which is today's behaviour, stays available as one of
the choices. This is the split [[ADR-161 — Channel Execution Shapes]] point 8 states:
*"Numbers belong to the company, the mechanism to us, the same split already used for
retention periods and the AI spend cap."* Point 5 already gives the cap's figures to the
company. The period over which they are counted is the same kind of number, so it goes
to the company too. The mechanism stays ours: the pre-call gate counts the runs of the
current period instead of every run ever recorded, and is otherwise unchanged. Changing
the period is a settings write, so it falls under the rule that every settings write is
made by a person ([[ADR-150 — Tenancy and Access Model]], 2026-10-02 (second) addendum,
point 2).

**3. Every AI run records who triggered it: a person or an integration.** The actor is
written on the run, so the ledger can later be split by person, by integration or by
period. An integration is a principal of its own
([[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]), which is why it is
named beside a person. **No per-person budget is decided.** Recording the actor makes
one possible later; it does not introduce one.

**4. Decided now, built later.** Until the build lands, the cap stays a lifetime total
and runs carry no actor. The build is tracked as task-345.

**Left to the final-design pass.**

- Which time zone "calendar month" is counted in.
- What happens to a run that is in flight when the period resets.
- How existing runs, written before the actor was recorded, are shown.

**Options not taken.** Keeping the lifetime pot as the default was not adopted. It is
the behaviour P2-H2 found, and under it a company that budgets monthly cannot express
its budget at all. It remains available as one value of the period setting.

Waiting for task-75 was not adopted either. task-75, still open, would read the
remaining budget from the company's AI source instead of a local setting. It changes
where the "remaining" figure comes from, not how the local ledger counts. Its own entry
keeps the manual setting as the default and notes that the pre-call gate needs only a
"remaining" number. So the local ledger needs a period whether task-75 is built or not.
task-75 is related to this addendum and is not superseded by it.

**What it costs.**

- **Positive:** a company that budgets monthly can set its AI budget the way it plans
  it. The ledger can later be split by person or period, because the actor is recorded
  from the build on.
- **Negative:** one more setting to understand and configure. And a company that wants
  a lifetime cap, today's behaviour, no longer gets it by default; it has to choose it.

**Nothing in this record's Decision changes.** Point 5 stands as written. Its "per
role/user" is read as one company pot, as above, and so is the third `### Positive`
bullet. Point 5's statement that the buffer is *"strictly bound to user
role/permission"* is not reinterpreted here.

## Addendum 2026-10-11 — the AI budget period's final-design pass

Prompted by the final-design pass for task-345, which builds the 2026-10-09 addendum
above. The user decided its open questions on 2026-10-11, one question at a time. That
addendum left three things to this pass: which time zone a calendar month is counted
in, what happens to a run in flight when the period resets, and how runs written before
the actor was recorded are shown. This addendum answers all three. Point 5 and the
2026-10-09 addendum stand as written.

**The decision.**

**1. Periods start at midnight UTC.** A month, quarter or year begins on its 1st at
00:00 UTC, which is 01:00 or 02:00 in Germany. No company time-zone setting is added.
UTC is unambiguous and matches how every timestamp is already stored, and a few hours
at the edge of a month rarely matter for a token budget. The settings screen says that
periods start at midnight UTC.

**2. A run counts in the period it is recorded in.** A run is recorded when the model
answers. So a run that starts before the reset and finishes after it counts in the new
period. The pre-call gate checked it against the old period's remaining budget before
it started, so at worst one run's tokens land in the new month. Nothing new is stored.

**Settled in the same pass.** These follow from the 2026-10-09 addendum and the records
it cites. They are stated here so the build reads them in one place.

- **The period setting.** It is one of month (the default), quarter, year or lifetime.
  Lifetime is the behaviour before this build. Changing it is a person's settings write
  under `settings.manage`, and it is audited.
- **The actor on a run.** Every new AI run records who triggered it: a person (user
  id), an integration (integration id), or `system` with no id, when a sweep or
  scheduled job runs it with no request behind it. These are the actor kinds of
  [[ADR-153 — Audit and Accountability]]; `system` is the `ACTOR_SYSTEM` its 2026-10-01
  addendum added. The 2026-10-09 addendum named a person or an integration; `system`
  covers a run that has neither.
- **Runs recorded before the build.** They have no actor and are shown as "not
  recorded". They cannot be attributed afterwards.
- **The buffer.** Point 5's buffer, *"strictly bound to user role/permission"*, is
  still not reinterpreted. It stays outside this build.

**What it costs.**

- **Positive:** a company that budgets monthly sees the cap refill on the 1st. Spend
  can be split by person or integration from the build on.
- **Negative:** the reset is at midnight UTC, not local midnight. Runs recorded before
  the build cannot be attributed. A company that wants a lifetime cap must now choose
  it explicitly.

**Nothing in this record's Decision changes.** Point 5 stands as written and is read as
the 2026-10-09 addendum reads it.

## Related ADRs

### Depends On
- [[ADR-140 — AI Capability Layer]]
- [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]
- [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
- [[ADR-101 — Provider Capabilities Are Explicit]]

### Enables
- [[ADR-141 — In-App Assistive AI Actions]]
