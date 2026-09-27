---
id: TASK-75
title: >-
  Read the remaining AI budget from the company's AI source instead of a local
  setting.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 202800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — direction + documentation, not a POC build.** **Read the remaining AI budget from the company's AI source instead of a local setting.** Surfaced 2026-08-02 (`/interview-review`, AI Q6). Today the cap is two numbers an admin types into Settings, and prices live in a hand-maintained `MODEL_PRICING` table — fine for the POC, and the manual path should stay as the default. **The structural problem it hides:** a company's AI budget is *company-wide*, and this platform will not be the only system in the company consuming tokens. A locally-configured cap therefore governs one consumer of a shared pool, and will drift from reality the moment a second system draws on it. **Direction:** allow the remaining budget (and ideally current prices) to be **fetched from the company's AI/token source** — an API the deployment points at — with the local setting as the fallback. Two things fall out for free: the platform stops being the authority on prices, so the **stale-price risk disappears** rather than needing a freshness mechanism; and the pre-call gate keeps working unchanged, since it only needs a "remaining" number, not where it came from. **Deliverable is a how-to, not an integration** — same posture as the swap-send-provider guide: describe the seam and one worked example, do not ship a connector. Pairs with the per-feature model selection and count-tokens escape-hatch items; write the three together. Source: [[Interview Prep - AI]] → AI Layer Q6.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 226, section "Features", position 28 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
