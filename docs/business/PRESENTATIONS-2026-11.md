# The November 2026 presentations — what has to be ready

Decided by the user on 2026-10-11. **This is the working focus now.**
`BETA-SCOPE.md` (2026-08-22) is dated: it defined beta as publishing the
playbook and repo with every launch gate green, and it treated the website
and any own install as later. It stays as the record of that scope.

## Who and why

- **Two agencies and one potential client's use case**, in November 2026.
- **The system need not be final.** It has to show *how it actually works*:
  a real flow, end to end, that looks finished on the screens it uses.
- The talks also test the positioning: agencies are the audience the
  positioning rules name (`POSITIONING.md`, rule 1).

## What has to be ready

### For both audiences

| What | Task |
|---|---|
| The real flow in the React client: create content, categorise, build a campaign, test send, real send, the signal coming back | task-67 (widened), with task-58's results section |
| Images: upload and picker | task-112 |
| An initial set of MJML content blocks, and two brand profiles (marketing, transactional), so example emails look good | task-371 |
| Salutations (informal and formal) | task-365 |
| The category graph | task-359 |
| Users, roles and integration keys in Settings | task-358 |
| AI subject suggestion in React, then: (1) draft and categorise content, (2) translate content, (3) prepare a variant from a topic | task-367, task-368, task-369, task-370, with task-100 and the decision task-125 |
| Realistic demo content, and a demo reset with believable results | task-71 |
| A conventional, coherent design on the demo React screens; no bespoke-brand prerequisite | task-372 |
| Neutral author-led reference identity and README, replacing the former working name | task-377 |
| A decision on double opt-in (at least the decision) | task-324 |
| How journeys work: the answer to give | task-373 |
| A rough sketch: how an installation and an implementation go | task-374 |

### For the agencies

| What | Task |
|---|---|
| Licensing options | task-313 |

### For the own project (before any install)

| What | Task |
|---|---|
| Positioning statement and playbook strategy — important, and first | task-375 |
| Name: reopened on 2026-10-11, after positioning a naming round | task-376 (details in the confidential naming record) |
| Only after those: the own install | task-347 stays parked |

## Later: the own project as the first adopter

Not started now, but logged so it is visible what it takes. The own website
(a separate repository, likely Next.js) would run on its own install of
the platform, single-tenant by design: one install per company, brands
inside it. It is the live proof and the first real installation.

1. **Install:** run the reference deployment (task-347): container or
   install script, health checks, backup and restore, the step-by-step
   guide. Real system mail for sign-in codes (task-123, task-76). The
   sending domain (SPF, DKIM, DMARC, the public webhook URL) — no task
   yet. A supply-chain check (task-238). Sends fired by an integration run
   inside the HTTP request (task-363).
2. **Signup from the website:** double opt-in's entry point (task-324),
   abuse protection for a public form (rate limits, bot check, CORS — no
   task yet), the preference centre (task-348), and an integration guide
   for a website, a CRM and n8n (no task yet; task-119 scopes it).
3. **Real people's data:** deleting a person (task-136 decides the policy;
   nothing builds it yet), free-text consent notes from a CRM (task-246),
   the stance on open tracking (task-353), the suppression model (task-135).
4. **Push for a mobile app:** no real push provider exists, outbound or
   inbound (task-59 is the inbound half). Email first, push after.

## Decisions only the user can make, before November

1. Double opt-in: a public endpoint, the CRM, or both (task-324).
2. AI suggestions alongside decision slots (task-125).
3. Licensing options (task-313).
4. Neutral working title decided 2026-10-12: **Omnichannel Orchestration Reference**, introduced by Diede Slembrouck with “Building a communication system you control.” task-377 applies it to `product.json`, the README and current identity assets before the presentations. Final brand/clearance remains task-376.
5. Whether the demo runs on a laptop or a hosted instance — a hosted one
   would be the first run of the install (task-347), which stays parked
   until positioning and naming are settled.
