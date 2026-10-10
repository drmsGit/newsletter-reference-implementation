---
id: TASK-55
title: >-
  Write the reference deployment — the answer to "how do you do security access,
  where do you host, what servers".
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-10 20:57'
labels:
  - docs
dependencies: []
type: docs
ordinal: 200800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Docs] — NOT an ADR, and that is the decision. Scoped 2026-09-18 (user) while accepting [[ADR-152 — Secret and Credential Handling]].** **Write the reference deployment — the answer to "how do you do security access, where do you host, what servers".** The question comes up constantly in conversation and the playbook has no answer to point at. **It is deliberately not an ADR**: how an adopter populates the process environment is infrastructure, and [[ADR-152 — Secret and Credential Handling]] point 1 exists so the architecture never has to know. Writing it as an architecture decision would turn a hosting choice into a commitment and invite adopters to inherit ours instead of using what they already operate. **Shape:** one honest reference deployment that is actually run (a single box with a reverse proxy in front is a defensible answer and survives follow-up questions, which a stack we do not operate would not), plus a named seam for the two things larger adopters will ask about — an **API gateway** in front (TLS, rate limits, request limits, IP allowlists, WAF) and an **egress proxy** behind (destination allowlisting, one outbound log, and the strong version: the proxy injects the provider credential so the application holds no key at all). **The claim to make is the seam, not the product** — "the platform holds no secrets of its own and reads everything from the process environment, so inject them with whatever you already operate" is a stronger sentence to a security reviewer than a vendor name, and it is the same move the architecture makes everywhere else. Belongs in Phase 4 playbook production.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 158, section "Features", position 8 in that section (top = do next). The description is the original entry, verbatim.

2026-10-09 (interview-review triage): two items for the reference deployment. (1) PUBLIC_BASE_URL is a required setting, an https address on a domain the company owns; task-330 makes a real send refuse without it. (2) Business P2-G2: per-integration request budgets belong to the gateway in front of the app, keyed on the API key; inside the app only sends are bounded, by approval holds and the recipient cap. This task's gateway seam is where that lives.

2026-10-09 (business interview BF-CI1, decided by the user): a fork's CI checks that fork's code. Its owner (the company, or the agency by contract) runs the checks against the deployed version and acts on them; we maintain the reference, not forks. The reference deployment should say so, alongside where the weekly vulnerability check's results go.

2026-10-09 (BF-SUB1): PUBLIC_BASE_URL should be a domain the company owns, not an agency's host. Every mail already sent carries links to it for good, so keeping it reachable across host moves is the adopter's duty, and the reference deployment should say so.

2026-10-10, written (commit 9a98735): docs/reference-deployment.md, linked from the README. Decided with the user the same day: write it now, marked 'designed, not yet run', because installation and deployment stay deferred at the POC stage. Running it is parked as task-347.

The page covers:
- the shape: one box, a reverse proxy, the app process, PostgreSQL;
- traffic in and out, and how scheduled sends are triggered;
- every environment variable the code reads (names only, from os.environ in app, main.py and scripts), with what it is for;
- access and rate limits as built;
- the API-gateway seam (per-key request budgets, P2-G2) and the egress-proxy seam;
- what the adopter is responsible for: unsubscribe links (BF-SUB1, ADR-191 addendum), a fork's own checks (BF-CI1), required checks (ADR-190 addendum), backups, consent law (P2-E1);
- what is not covered yet.

Facts about the app were checked against the code. One gap was found and recorded rather than fixed: credential injection by an egress proxy would fail today, because the Resend adapter refuses an empty RESEND_API_KEY.

All wikilinks resolve. Full suite (1660) green, including the text guards. CI green on 9a98735.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The reference deployment is written: docs/reference-deployment.md answers 'how do you host this, secure access, what servers'. It covers one box with a reverse proxy and Postgres, every environment setting the app reads, access as built, the API-gateway and egress-proxy seams, and the adopter's responsibilities. It is plainly marked 'designed, not yet run' (decided 2026-10-10), so no positioning claim rests on it, and is deliberately not an ADR. Running it is parked as task-347. Verified against the code, with links resolving and green CI on 9a98735.
<!-- SECTION:FINAL_SUMMARY:END -->
