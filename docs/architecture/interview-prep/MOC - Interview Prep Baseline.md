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

**Status: the original 4 cluster files are fully reviewed and cleared** (Content/Campaigns/Audience, Decision/Overrides/Insight, Delivery/Providers/Recipients, Snapshots/Rendering/Email Modules) via `/interview-review`. Decisions logged to [[backlog]].

**2026-09-18 — three new cluster files, unreviewed.** A second `/interview-prep-baseline` run covered what shipped between 2026-08-20 and 2026-09-18 (112 commits): multi-brand, channel-on-variant and push, the 9→16 permission split, machine principals, and the audit log. None of that existed at the first baseline. The module pages these were composed from ([[auth]], [[brand]], [[channels]], [[audit]], [[ai]]) were written in the same pass — the folder had no page for any of them.

## Reviews by cluster

**Reviewed and cleared (2026-07 baseline)**
- [[Interview Prep - Content, Campaigns, Audience]] ✅
- [[Interview Prep - Decision, Overrides, Insight]] ✅
- [[Interview Prep - Delivery, Providers, Recipients]] ✅
- [[Interview Prep - Snapshots, Rendering, Email Modules]] ✅
- [[Interview Prep - AI]] ✅

**Open (2026-09-18 baseline)**
- [[Interview Prep - Auth, Permissions, Machine Principals]] ⬜ 8 questions
- [[Interview Prep - Brand Boundary]] ⬜ 8 questions
- [[Interview Prep - Channels, Audit]] ⬜ 9 + 5 questions

### Findings from the 2026-09-18 run that are defects, not questions
Surfaced while generating the above; they belong in [[backlog]] rather than in a review cycle.
- `delete_brand` blocks on 5 tables; **7** carry a NOT NULL brand FK. `consent_events` and `integration_grants` are missing, so deleting such a brand raises `IntegrityError` instead of the clean refusal (Brand Q7).
- `recipients.consent` is platform-level on the stated grounds that "recipients carry no brand" — but `consent_events.brand_id` has been NOT NULL since migrate_0008 (Brand Q3).
- The three JSON routers' PROVISIONAL comments claim the routers are unguarded; `enforce_api_policy` has guarded all twelve since 2026-09-18. Permission is checked against the declared `X-Brand`, the row lands in the default brand.
- Three comments still place subject/preheader on the variant; migration 0012 dropped those columns.
- `docs/backlog.md:35` still says brand-scoped roles are unenforced; `_permitted` enforces them and `test_brand_scoping.py:558` covers it.
- `/ui/graph` has no brand filter. ADR-150's addendum blocked it on the consent work, which has shipped.

## Cross-cutting findings (highest priority first) — resolution status

- **Two independent, non-integrated override mechanisms.** ✅ Resolved: act/fix, folded into one "design a coherent override strategy" [[backlog]] Feature (Campaigns Q3 + Overrides Q1), including renaming `OverrideEventDB` to reflect its real purpose as an outcome/audit log.
- **`recipient_id` means two different things across modules.** ✅ Resolved: act/fix, logged to [[backlog]] (switch `DeliveryExecutionDB.recipient_id` to a direct FK — confirmed this doesn't add CRM sync burden, per ADR-126).
- **No consent/marketing-opt-out gate exists at send time.** ✅ Resolved 2026-07-11 via `/business-review`: minimal CRM-synced `consent_status` field + sync-drift log, checked at audience-resolution time before decision/rendering run (not a CRM replacement). Driven by legal (GDPR processing scope) and cost (AI/token spend) reasons. See `docs/business-interview-baseline.md` §F1.
- **[[ADR-131 — Email Module Templates Use MJML as Source Format]] and its implementation contradict each other.** ✅ Resolved: keep in poc — raw HTML for the POC, MJML for the final project (already decided).
- **Zero automated test coverage outside `test_overrides.py`.** ⚠️ Not directly resolved during this review — no backlog item exists yet for building out test coverage generally. Worth a dedicated pass.

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
