---
id: TASK-194
title: >-
  Any address containing `+` can never sign in once a real provider is
  configured.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 505800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P1.** **Any address containing `+` can never sign in once a real provider is configured.** `auth/router.py:79` and `:107-112` interpolate the address into a query string unescaped, while the sibling parameter on the same line *is* escaped: `url=f"/ui/login/verify?email={address}&next={quote(target, safe='')}"`. Starlette decodes `+` in a query value as a space, so `name+tag@example.com` arrives at `verify_form` as `name tag@example.com`, pre-fills the mangled value, and `verify_login_code` (`service.py:317`) finds no user — reporting *"That code is not valid or has expired"*, the wrong diagnosis, which is what makes it expensive to find. **Fix (2 loc):** `quote(address, safe='')` in both places; `quote` is already imported at `router.py:13`. **Risk: none.** **Why review missed it:** the dev path never takes this redirect — `dev_code_visible()` is true whenever `SYSTEM_MAIL_PROVIDER` is unset, the shipped default, and that branch renders inline instead. The bug exists only in deployments that have a real provider, i.e. the ones that matter. Sub-addressing is common in this product's operator population — the maintainer's own address uses it. Not covered by tests; `test_auth.py` calls the service directly and never goes through the router. Source: code-slimmer sweep 2026-08-21, Cluster 6 A2. **DONE 2026-09-13.** `quote(..., safe='')` on the address in **both** redirects — the entry named two sites and fixing only the first would have left the address intact until the user's first typo, then mangled it for every attempt after. Covered at the layer the bug actually lives at: the test reads the value the verify form will **post back**, not the redirect's Location header, because the defect is in what Starlette hands the *next* request. Both escapes were mutation-checked independently. The entry's "not covered by tests; `test_auth.py` calls the service directly and never goes through the router" was exactly right, and is the same gap that let the CSRF guard be switched off without failing anything.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 619, section "Done", position 58 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
