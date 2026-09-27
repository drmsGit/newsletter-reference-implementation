---
id: TASK-79
title: >-
  Dev-data pseudonymization guard — a Mode-C safety property, not only a privacy
  one.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 203200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** **Dev-data pseudonymization guard — a Mode-C safety property, not only a privacy one.** Decided 2026-07-31 (AI-layer interview, Cluster 4 / Q20b). **Problem:** the standard industry habit is copying production data into a "dev" environment — the user reports every company he has worked in or for ran exactly that *pseudo*-dev setup, which forces permanent caution inside the environment that exists so people *don't* have to be cautious. Under Mode C (AI-assisted development — **including marketers vibecoding**, not just developers) that habit also silently violates [[ADR-144 — AI Data and Model Governance]], since an assistant reading the dev DB is reading real recipient PII. **Design:** (1) **Deterministic pseudonymization, not hashing** — stable fake-but-realistic values (same input → same output) so joins, dedup and per-recipient logic still work; a hash would protect the data and simultaneously destroy the reason to have a dev environment. (2) **Schema-declared PII fields, not content sniffing** — the models already know which fields are personal, and ADR-144's per-task PII filter needs the same metadata, so **one declaration serves two consumers**; free-text/JSON sniffing is a documented best-effort *extension*, not v1. (3) **Exempt-domain allowlist** (e.g. `PII_EXEMPT_DOMAINS`) — addresses at the company's own domains stay real so provider testing and marketer campaign tests still work; **must accept multiple domains** (different brands, external agencies). Chosen over a third `dev → testable → prod` environment, which costs extra infrastructure and merely *relocates* the risk; the allowlist caps AI blast radius at **your own employees instead of your customers**. (4) **Non-routable addresses for everyone else** — this also closes the gap that environment separation *cannot* contain outbound email (Q19): with no deliverable customer addresses in DEV, a stray real send reaches nobody. (5) **Loud DEV startup assertion** that fails on unpseudonymized data **and reports what it exempted** — a widened allowlist must be visible, never silent; no wildcards. **Change-effort requirement:** declaration lives on the models (written once, untouched at deploy time), **policy is environment configuration**, so dev→prod is a config difference rather than a file edit (the user's Condor experience: moving many files between environments reliably produces typos and omissions). Composes with the existing layers: mock provider as DEV default → recipient cap → exempt-domain allowlist → assertion. Cross-references the parked **Security chapter** (key storage, GDPR/ISO, SSO, roles). Source: user, 2026-07-31 (AI-layer interview, Cluster 4).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 234, section "Features", position 32 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
