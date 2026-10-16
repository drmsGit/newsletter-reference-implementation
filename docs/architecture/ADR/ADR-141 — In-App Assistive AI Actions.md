---
type: adr
status: accepted
topic:
  - architecture
  - ai
  - governance
  - content
created: 2026-07-31
modified: 2026-10-16
source:
  - "AI Layer design interview (interview-prep, 2026-07-27 – 31), Cluster 2"
depends_on:
  - "[[ADR-140 — AI Capability Layer]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
  - "[[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]"
  - "[[ADR-080 — Human-governed Taxonomy Before AI Selection]]"
  - "[[ADR-081 — AI Ranks Within Governed Candidate Sets]]"
  - "[[ADR-082 — AI May Recommend but Not Publish]]"
  - "[[ADR-131 — Email Module Templates Use MJML as Source Format]]"
---

## Status
Accepted

## Context

ADR-140 established the AI capability layer and ADR-144 its cross-cutting model /
PII / cost governance. **Mode A** is the first and most concrete mode: **in-app
assistive actions** a marketer triggers by a button (as opposed to Mode B's
autonomous workflows and Mode C's dev-time assistance). This ADR fixes the
task-plugin contract, the first actions to build, the approval UX, and the rule
that keeps AI-generated content from ever bypassing content governance or
exploding the approval surface.

## Decision

**1. The task-plugin contract (the dev-owned scaffold).**
A Mode-A task *file* declares:
- **name / id**;
- **inputs** — platform-gathered, filtered by the PII policy of ADR-144 (default:
  IDs / signals / content, no raw PII);
- **output type** — subject/preheader, tag list, content-suggestions-with-reasons,
  draft record, …;
- **where it lands** — which record it writes;
- **references** to the frontend-owned **prompt id**, the **model** (ADR-144), the
  **guards / PII policy** (ADR-140 / ADR-144), and the **approval mode** (ADR-140,
  per-task auto-apply vs require-approval).

It is technical wiring plus pointers. Everything a marketer touches — the prompt,
the guards — is *referenced*, not embedded (ADR-140, point 4).

**A task's input arrives in three layers, not two.** ADR-140 split "dev scaffold"
from "manager-owned prompt"; a third layer is needed at *runtime*:

| Layer | Owner | Contains | Changes |
|---|---|---|---|
| **Task file** | Dev | goal → where the result lands (e.g. "put the suggestion in a new variant") | Rarely |
| **Settings prompt** | Manager, versioned | the general prompt: what shape to return (copy, images, header + content ids with layout key) | Occasionally, published like content |
| **Runtime input** | Manager, ad hoc | the *specific* target/goal typed when clicking the button | Every invocation |

**Anti-proliferation rule:** a minor, ad-hoc variation in intent is **runtime
input**, not a reason to create a new task file + prompt setting. New task files
are for genuinely new output types or landing places — not for "the same task,
different goal this time." Without this rule the task registry grows one entry per
phrasing.

**2. Build concrete first, then extract the registry.**
Wire **2–3 tasks directly**, then extract the plugin registry — exactly how the
decision strategies grew. The contract (point 1) is already designed, so the
extraction is light.

**3. First three actions, built in order 2 → 1 → 3.**
1. **Subject / preheader** — easiest (it is the email's own content). Suggest a few
   subject/preheader combos; the manager approves. Showcases merge-variable PII
   (ADR-005 / ADR-144). Offers **two** accept paths: **"use suggestion"** and
   **"test suggestions in A/B setup"** — *writing* a second subject line and
   *testing* it are two different frictions, and Mode A should remove both. (The
   A/B component itself is a separate POC feature, tracked in `docs/backlog.md`.)
   **Watch item:** the **preheader may become irrelevant** as mail providers replace
   it with AI-generated summaries — confirm before investing further in it.
2. **Auto-tag** — harder on the *output* side: tags must be routed to the right
   places, under the human-governed taxonomy propose-govern loop (ADR-080).
3. **Content-suggestion-with-reasons** — most important and most complex; AI ranks
   within governed candidate sets and shows its reasons (ADR-081), and may
   recommend but not publish (ADR-082).

Good enough for the POC / MVP package. First model integrations for testing =
**Claude (Anthropic API)** + **ChatGPT (OpenAI)**, to prove the adapter across two
providers; the EU-model worked example (ADR-144) is the additional documented one.
API keys live in `.env`, added by the operator.

**4. One consistent accept/reject component in a dedicated approval UI.**
A single **accept/reject component**, reused across tasks, lives in a dedicated
**AI-suggestions / approval-inbox UI**: it shows the output(s) + reason,
accept/reject per item, pick-one for options, and logs either way (ADR-140 audit).
**Optional notifications** (desktop push and/or email), configurable. This
dedicated UI is **the same approval surface Mode B autonomous workflows use**
([[ADR-142 — Autonomous Workflows and the Automation Boundary]]). **Watch item:** accept/reject is the slim default, but some
tasks may want a short **feedback/iteration flow** ("make it punchier" →
regenerate) — logged as a need to revisit, not built yet.

**5. AI-generated content is an unpublished draft; personalisation stays with the
decision engine.**
AI-authored content is **direct-written as an unpublished draft** (ADR-140's
"reversible + audited"); going live is the **publish** step, governed by the
per-task manual/auto setting (ADR-140). A company may flip a trusted task to
**auto-publish** — graduated trust is the point of the layer.

**Architectural guard against the "80 records to approve" problem:** AI generates
a **bounded set of *shared* variants/drafts, never per-recipient content on the
fly**. Per-recipient personalisation stays with the **decision engine + merge
variables** (ADR-005), *not* generative AI. So the approval surface never explodes
and "always approve" stays practical, and per-recipient cost/risk is avoided.

**6. Cost visibility in the Mode-A UI.**
The AI UI shows **total cost/tokens against the cap**; the **per-run estimate is
dropped** from the UI (ADR-144, point 5 — open code if a company wants it). The
*enforcement* of the cap (configurable buffer, pre-call gate, role/permission
binding, partial results still shown) is the cross-cutting rule in ADR-144, not
re-decided here.

## Consequences

### Positive
- A uniform task contract means new Mode-A actions are wiring + pointers, not
  bespoke plumbing.
- Content governance is never bypassed: AI output is a draft, publishing is the
  governed step, and taxonomy/candidate governance (ADR-080/081/082) is reused.
- The "shared bounded variants, not per-recipient generation" guard keeps approval
  and cost bounded and keeps personalisation where it belongs (decision engine).
- One approval component + inbox serves every task now and Mode B later.
- Two-provider testing (Claude + ChatGPT) proves the model adapter early.

### Negative
- Three tasks is a deliberately small first surface; broader Mode-A coverage is
  later work.
- Accept/reject may prove too thin for some tasks (the logged feedback-flow watch
  item); if so, a richer iteration UX is a follow-up.
- Auto-publish trades safety for speed; a company that flips it too early on a
  weak task can ship weaker content — mitigated by graduated trust and audit.

## Notes

- **Order recap:** actions built 2 → 1 → 3 (auto-tag's output routing is the real
  complexity; subject/preheader is the easiest first win; content-suggestion is the
  most valuable but most complex).
- **Reuse, don't re-decide:** subject/preheader and content-suggestion operate on
  MJML module content (ADR-131); auto-tag and content-suggestion reuse the decision
  layer's AI-governance ADRs (ADR-080/081/082) rather than inventing new governance.
- **Status.** Decided in the design interview; implementation is the first AI build.
  Accepted as a design decision, not as shipped code.

## Addendum 2026-10-16 — The content draft task: a record drafted from a pasted source, and its categories proposed

Prompted by the final-design pass of task-368 ("AI drafts a content record from
a source and proposes its categories"), decided by the user on 2026-10-16, one
question at a time. Points 1–6 stand. This addendum adds one task under point
1's contract.

**Why it is a new task file.** Point 1's anti-proliferation rule allows a new
task file only for a new output type or landing place. This task is both: its
output type is "draft record", already named in point 1's list, and it lands on
a content record, which no earlier task writes. Its id is `content_draft`.

**1. Where it runs.** On a content record's own page, for a record that already
exists: a person created it with a title. The run belongs to that record (its
target is the content record), so a proposal is read back after a reload and the
audit names the record.

**2. What it reads.** Text the manager pastes or types, such as an article or a
brief. The server never fetches a web address for this task. Fetching a URL
server-side is undecided; no ADR covers it, and it needs its own decision. The
source is capped at 12,000 characters, and the box says so, so that one paste
cannot consume the budget. The pre-call gate of
[[ADR-144 — AI Data and Model Governance]] point 5 still applies. The source is
sent to the model provider and is not stored on the run. Only the model's output
is stored ([[ADR-140 — AI Capability Layer]] point 5).

**3. Personal data.** ADR-144 point 4 keeps raw personal data away from the model
by default. The panel tells the manager to paste content, not anyone's personal
details, because the text goes to the model provider. There is no pattern
detection: a press release's contact address would trip it. Personalisation stays
with dictionary entries
([[ADR-199 — Inline Personalisation Is a Brand's Expression Dictionary, Substituted After Escaping]];
ADR-144 addendum 2026-10-16). Drafted text goes through the ordinary record save
and its checks.

**4. Which fields.** Every text field (text and rich text) of the channels the
manager ticks. The fields are read from the field definitions (`fields.json`,
[[ADR-177 — A Field Is Defined Once, Required Per Module]]), and their labels and
notes go to the model as guidance, so a new text field is drafted without code.
Links, images and image descriptions are never drafted: the model cannot see an
image or know the right address. A link the model writes into rich text is
reduced to its label.

**5. Taking the fields.** The panel lists each drafted field with its text,
ticked. A field that already has text shows both versions, unticked. "Use ticked
fields" saves them in one ordinary edit, and the audit entry names the run. This
does not publish the record or mark it ready.

**6. Categories.** Proposals come from the existing categories only
([[ADR-080 — Human-governed Taxonomy Before AI Selection]]). The vocabulary is
global ([[ADR-150 — Tenancy and Access Model]], addendum 2026-09-15). Each
proposal carries a whole-number score from 1 to 10 (ADR-080 addendum 2026-10-04),
which the manager can change before taking it, and the model's one-line reason
(point 4: reasons are shown). A category already on the record shows its current
and proposed score, unticked. A name the model invents that is not in the
vocabulary is dropped, and the panel says so. "Assign ticked" makes them ordinary
assignments, and the audit names the run.

**7. No approval step.** The task has no held form (ADR-140 addendum of the same
date), so point 4's approval inbox has nothing to hold. Point 5 holds: the record
stays unpublished. The difference is that the model's text reaches the record
only when a person takes it, not by direct write. Publishing, readiness
([[ADR-174 — Channel Readiness Is Asserted, Not Computed]]) and machine ready
([[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]])
stay separate human acts.

**Consequences.**

- **Positive.** A new text field is drafted without code. The source is not kept.
  Nothing reaches the record's fields, its categories or any recipient without a
  person's act, and every taken field or category names the run that proposed it.
- **Negative.** Without a URL fetch, the manager copies the text in. Nothing
  detects personal data in the paste; the panel's instruction is the only guard.
  Links and images stay the manager's work.

Nothing here changes the Decision section above.

## Related ADRs

### Depends On
- [[ADR-140 — AI Capability Layer]]
- [[ADR-144 — AI Data and Model Governance]]
- [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]
- [[ADR-080 — Human-governed Taxonomy Before AI Selection]]
- [[ADR-081 — AI Ranks Within Governed Candidate Sets]]
- [[ADR-082 — AI May Recommend but Not Publish]]
- [[ADR-131 — Email Module Templates Use MJML as Source Format]]
