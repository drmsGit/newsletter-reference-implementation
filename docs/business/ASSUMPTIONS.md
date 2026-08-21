# Assumptions

Triaged: **blocking** (resolve before proceeding) / **self-resolving** (names
what resolves it) / **non-blocking**.

**Seed file.** These are the assumptions carried forward from the two review
passes already run (`docs/business-interview-baseline.md`,
`docs/business-interview.md`) and the decision log. A full sweep has not been
run against `docs/business/` since these files were created — run the
`assumption-scanner` agent to extend it.

## Blocking

| Assumption | Carried by | What would resolve it |
|---|---|---|
| Agencies and freelancers are the economic buyer, not the end customer | `playbook-strategy.md` §2 | Real evidence beyond the one agency that expressed interest — a paid workshop or a signed engagement |
| The teachability axis is worth more than the production-speed axis to this buyer | `business-interview.md` 2026-07-12 | The positioning gate itself; a market test of the published playbook |
| Adopters will accept "one worked example per seam" rather than expecting connectors | provider-plugin-strategy decision | First real adopter's reaction to the mock provider plus Resend |

## Self-resolving

| Assumption | Resolved by |
|---|---|
| The structure absorbs new channels cheaply (~80% already channel-neutral) | The omni-channel interview — deferred 2026-08-12 |
| Per-recipient LLM selection stays the wrong tool as model prices fall | The Needs-ADR item on what "AI" means in the decision layer |
| Personalization data shape works against a real CRM | An example CRM integration PoC (open sub-question G1) |
| The automation layer is years out and safe to defer | ADR-142's worked examples once Mode B is built (open item I1) |

## Non-blocking

| Assumption | Note |
|---|---|
| MJML is worth its learning cost | Confirmed deliberately; low module churn, re-anchored on source ownership rather than authoring speed |
| Mittelstand buyers want graduated trust, not full autonomy | Load-bearing for the override layer, and consistent across every review pass |
| A €199 starter package is the right entry price | Untested, but nothing depends on it yet |

## Rules
- An item resolved in `docs/playbook-strategy.md` §5 or in
  `docs/business/decisions/` is deleted from here, not marked done — the
  decision log is the record.
- Blocking items get a resolution path, never just a flag.
