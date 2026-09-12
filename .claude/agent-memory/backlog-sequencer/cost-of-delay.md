---
name: cost-of-delay
description: Rises / Flat / Decays classification of backlog items, 2026-09-12. Rises entries name why and who pays.
metadata:
  type: project
---

## Rises

| Item | Why it rises | Who pays the tax |
|---|---|---|
| Consent-events + addressability migration (ADR-163 §1/§2) | Every call site added against `consent_status` must be migrated; 10 files already | P0 fix, suppression model, provider contact sync, transactional sends, drift endpoint, React recipient screens |
| `SignalContributionDB.channel` (ADR-164 §9) | Contributions are append-only, decay-on-read. Rows written before the column exists can never be truthfully backfilled | Channel weights, any per-channel signal analysis, DWH export schema |
| Artifact rename + subject/preheader to module fields (ADR-162 §1/§3) | Two schemas diverge the longer they coexist; a bespoke subject-override built first is wasted work ADR-162 gives free | Mode-A work, snapshot build, snapshot atomicity fix, React variant screens |
| Gate 3 machine auth | A constraint before the feature that makes its race routine; every JSON route added meanwhile is one more to retrofit, and a second client built against an open API bakes it in | React SPA, Mode B, every new router |
| `app/database.py` engine-at-import | Every fix landed without a clean test runtime is hand-verified; the P0/P1 are exactly the ones needing regression tests | All six missing tests, beta DoD #4 |
| Auth enforcement default-on (Gate 4) | Fail-open default plus a growing route count; CSRF must cover all 43 frontend write routes at once | Every new UI route |
| Signal-weight editor no-op (+3 loc) | ADR-164 §10 extends this exact grid with channel weights | Channel weights, any settings-driven tuning |
| Click/open attribution guesses one primary content record | Mis-attributed contributions are append-only history; the corruption is permanent, and grows with every send | Signal layer, decision explainability, 3D |
| Missing DB uniqueness constraints (category assignment, content versioning) | Duplicates must be cleaned before a unique index can be added at all | Any later constraint work |
| Mode A/B/C vs Phase 4A/4B/4C rename (Docs) | Phase 4A/4C are about to write the playbook; publishing bakes the collision into the public artifact. Already cost one planning cycle | Playbook text, every future ADR reference |
| Pagination envelope | Each new list endpoint is one more retrofit, and the typed client is generated off the schema | React client, every data-heavy endpoint |

## Flat

P1 send-status aggregation; `+`-address `quote()` fix (2 loc); brand-scoped role
enforcement; webhook fail-closed when secret unset; `httpx2` typo; `Secure` cookie flag;
snapshot atomicity (but batch with the artifact rename); bulk-remove-by-criteria;
image upload/media picker; guaranteed placement; zero-content-module safety check;
provider choice on the campaign send flow; system-mail channel on its own domain;
dev-data pseudonymization guard; token-counting escape-hatch doc; extended-thinking
ceiling coupling; conversion signal sourcing; DWH export + local prune.

## Decays

- **Provider contact sync (Needs-ADR)** — its own text corrects the premise: the
  transactional `/emails` endpoint needs no pre-synced list. May delete itself.
- **A/B test component** — the architecture's own thesis is that personalization makes
  content-level A/B largely redundant over time.
- **Anti-bubble exploration** and **negative category-affinity** — both need real
  behavioral evidence that does not exist yet; building early means guessing the
  magnitude and then rebuilding.
- **"Most recipients matched" tiebreak variant** — an option alongside an existing
  working tiebreak.
- **Calendar-time vs activity-relative decay** — a named edge case (90-day holiday) with
  no observed instance.
- **Cost/token feedback before an AI decision batch** — predicated on per-recipient LLM
  selection, which the Mode-A build found to be the wrong tool, not merely expensive.
- **AI ledger double-scan** — LOW, n is small; the performance-notes doc may absorb it.
- **Progress indication + double-submit for AI tasks** — explicitly deferred to the React
  frontend; disappears if that frontend replaces the server-rendered POST.
- **Passkeys/WebAuthn** — on hold pending the user's own research; ADR-151 §6 already
  fixes the shape as additive.
- **"Publish all" button**, **DOI cold-start seeding** — convenience, no downstream.
- **11-broken-wikilink housekeeping** — see staleness-watchlist; the count is disputed.

## Scope-dependent (flips between BETA-SCOPE §1-4 and the §5 React addendum)
Pagination envelope; image upload/media picker; AI progress indication; category picker
(also stale, see watchlist); brand/theming web palette; per-task model selection;
shared approval inbox. Under §1-4 all are out; under §5 the first three become
frontend prerequisites.
