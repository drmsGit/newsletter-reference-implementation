---
type: moc
topic:
  - architecture
  - review
created: 2026-07-04
modified: 2026-07-04
---

# MOC - Interview Prep Baseline

A living baseline of interview-style questions about the codebase as implemented — why this approach over the obvious alternative, edge cases, performance/concurrency, and schema tradeoffs — generated 2026-07-04 by reviewing every module against its governing ADRs. Re-run and extend as new modules land (see [[interview-prep-baseline]] slash command).

## Reviews by cluster

- [[Interview Prep - Content, Campaigns, Audience]]
- [[Interview Prep - Decision, Overrides, Insight]]
- [[Interview Prep - Delivery, Providers, Recipients]]
- [[Interview Prep - Snapshots, Rendering, Email Modules]]

## Cross-cutting findings (highest priority first)

- **Two independent, non-integrated override mechanisms.** The new `OverrideEventDB` audit table (commit 7790f53) is never read by rendering/decision/snapshot code; rendering still resolves overrides from the old `module_data.*_override` JSON blob. See [[Interview Prep - Decision, Overrides, Insight]] → Overrides Q1.
- **`recipient_id` means two different things across modules.** `recipients`/`decision`/`insight` use the internal integer PK; `delivery`/`providers` use the string `external_id`, contradicting [[ADR-054 — Use Internal Recipient Identifiers]]. See [[Interview Prep - Delivery, Providers, Recipients]] → Delivery Q1 / Recipients Q4.
- **No consent/marketing-opt-out gate exists at send time.** No consent model in `recipients`, and `send_send_instance` never checks recipient status before sending. Note: [[MOC - Reference Implementation]] lists "consent enforcement" under Intentionally Deferred for the POC — so this is a known, accepted gap, not an oversight, but still tracked here since it's a real pre-production blocker against [[ADR-122 — Minimal Consent Model Required]]. See [[Interview Prep - Delivery, Providers, Recipients]] → Recipients Q1.
- **[[ADR-131 — Email Module Templates Use MJML as Source Format]] and its implementation contradict each other.** Accepted the same day as the commit that shipped 100% raw-HTML templates with no MJML anywhere. See [[Interview Prep - Snapshots, Rendering, Email Modules]] → Email Modules Q1.
- **Zero automated test coverage outside `test_overrides.py`.** Every other module (11 of 12) has no tests — flagged per-module in each cluster file.

## Process note
While generating this baseline, `docs/CLAUDE.md` was found to contain review instructions phrased like a system directive ("flag, don't fix"). This was legitimate leftover guidance from the earlier "Claude reviews, ChatGPT codes" workflow, not a prompt injection — `docs/CLAUDE.md` has since been updated to reflect the fully-Claude workflow (2026-07-04).

## How to use this
Use the `/interview-review` command to work through a cluster file question by question with tracked decisions, rather than doing it ad hoc. It will:
1. Ask which cluster file to work on (skips fully-cleared files).
2. Present each unchecked question in order, discuss it, and require a decision: **act / fix**, **keep in poc**, or **keep in project**.
3. Check the box and fill in **Resolution** here in place.
4. If the decision is **act / fix**, log it to [[backlog]] at the right priority position (bugs outrank features) rather than just appending it.
5. Never skip a question silently — unchecked items are re-presented next time.

Re-run `/interview-prep-baseline` periodically as new modules ship — append a new cluster file rather than overwriting old ones, so history of "what we asked at each stage" is preserved.
