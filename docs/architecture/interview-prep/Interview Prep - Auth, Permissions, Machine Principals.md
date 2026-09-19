---
type: interview-prep
status: open
topic:
  - architecture
  - review
  - auth
  - security
created: 2026-09-18
modified: 2026-09-18
source:
  - interview-prep-baseline-2026-09-18
depends_on:
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-151 — Authentication and Sessions]]"
  - "[[ADR-152 — Secret and Credential Handling]]"
  - "[[ADR-153 — Audit and Accountability]]"
  - "[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]"
---

# Interview Prep — Auth, Permissions, Machine Principals

Generated 2026-09-18 via `/interview-prep-baseline`, for `backend/app/auth/` and the guards wired in `backend/main.py`. **This cluster has never been reviewed** — it did not exist at the 2026-07-04 baseline. Companion module page: [[auth]].

Already logged, deliberately not raised here: unattended machine sending was a refusal rather than a queue when these questions were written. **Superseded 2026-09-19** — the ADR-142 §4 approval surface shipped (`backend/app/approvals/`), point 5 became a queue, and the check order in `enforce_api_policy` was reordered with it, because a flag that hands out a held request is a "not yet" rather than a "may not": left in the old order, an integration holding no `sends.execute` grant could have minted a pending send for a person to approve. See ADR-166's build-note 3.

Check off each item once discussed, and record the outcome in **Resolution**.

## Auth & access control

- [ ] **Q1.** The policy table matches route templates with a bare `startswith`, first match wins. Why a prefix table rather than per-route declarations, and what does prefix matching cost?
    **A:** `WRITE_POLICY` (`policy.py:52-145`) buys two things decorators cannot: the whole policy is legible in one file, and `required_permission` returns `UNMAPPED` for an unclassified write, so forgetting fails closed and loudly instead of shipping an unguarded endpoint. The cost is that **order is semantics**: six narrow/broad pairs are correct only because of line order, and a broad prefix inserted above a narrow one silently downgrades it with no test failing. `("/ui/brand", VIEW)` at `:57` is already a live prefix collision with `/ui/brands`, safe today only because brand CRUD lives in `auth_router`, which is not wrapped in `enforce_policy`. The table also has no method granularity — POST and DELETE on `/ui/content` both resolve to `content.manage`, and every GET short-circuits to `VIEW`, which is why three admin read pages need explicit `require_permission` guards.

- [ ] **Q2.** Permissions are grants only, with no DENY, and multiple roles union. Why not model denies, and where does the union get dangerous?
    **A:** `permissions_for` (`service.py:819-866`) just collects rows, so the union falls out of the model rather than being a resolution rule. The genuine danger is not role conflict, it is the **`brand_id=None` overload**: the same function means "union across every brand this principal holds" when given no brand. `_permitted` therefore refuses a brand-scoped permission outright when the request has no working brand rather than calling through with `None`, because passing it would let an Admin on brand A act as one on brand B. One default argument is the difference between correct and fail-open. Would a typed `Scope` value (`AllBrands` vs `Brand(id)`) be safer than an optional int meaning two different things?

- [ ] **Q3.** Every role implies `view`, but an integration is not granted it. Defend the asymmetry — and what does it do to machine GETs?
    **A:** For a machine, write-without-read is the ordinary case — n8n fires a send and reads nothing — and implying `view` would hand every integration the recipient list, one of the exposures ADR-166 exists to prevent. The consequence to probe: on the machine plane every GET resolves to `VIEW` (`policy.py:155`), so an integration granted `recipients.manage` can POST a recipient and gets a 403 reading one back. Granting `view` to fix that is all-or-nothing and platform-level, so it reopens exactly the exposure the asymmetry protects. Is the real answer that reads on the machine plane need their own scoped keys rather than falling through to `view`?

- [ ] **Q4.** `hash_secret` is a bare unsalted sha256 — defensible for a 32-byte credential secret, but it also hashes the six-digit login code. Is that the same argument?
    **A:** The credential case is well argued (`integrations.py:38-48`): no dictionary of 32 random bytes, and a KDF would sit on the hot path of every machine request. But `hash_secret` (`service.py:61-62`) is the single primitive for four things — session tokens, credential secrets, rate-limit identifiers, and `login_codes.code_hash`, which has 10^6 of entropy and no salt, so a database reader can precompute the whole space and identical codes collide across users. The defences are elsewhere and are real: 5 attempts with the code burned, a 10-minute TTL, supersession of outstanding codes, and anyone reading `login_codes` can read `auth_sessions` anyway. Still the sharpest version: **the one input that genuinely fits the KDF rationale is the one that does not get it**, and `csrf_token_for` had to be manually domain-separated precisely because one primitive serves all these roles.

- [ ] **Q5.** The login form closes the response oracle. Does it close the timing one?
    **A:** The response discipline is thorough — one unconditional 303 for every outcome, throttling before the user lookup specifically so the path cannot diverge, refused requests not recorded, and the tri-state `CodeDelivery` so a broken provider never returns a live code. But `request_login_code` runs inline at `router.py:93`, and for a known address it supersedes old codes, inserts a row, commits, then calls the provider **synchronously** through `deliver_code` — an outbound HTTPS call — while an unknown address returns after one SELECT. With a real provider that is a multi-hundred-millisecond difference in the 303's latency: **the response oracle is closed and a timing oracle stands in its place**, which is the exact substitution the comment at `router.py:77-79` says it was avoiding. Would queuing the send, or a fixed response-time floor, complete ADR-151 §2?

- [ ] **Q6.** `record_auth_failure` aggregates per `(key_id, client, hour)` to avoid handing an attacker a write primitive. Does the bucket key achieve that, and who reads the table?
    **A:** Three things to press on (`integrations.py:201-232`). First, `key_id` in the bucket key is **attacker-supplied** — straight off the `Authorization` header, only truncated to 64 chars — so a caller who varies the key per request still creates one row per attempt, which is the growth the aggregation was meant to prevent; it only helps an attacker who politely reuses one key. Unlike the rate-limit counters, which are pruned on write, nothing prunes this table. Second, the read-then-increment is **not atomic** and there is no unique constraint on `(key_id, client_hash, window_start)` in `db_models.py:302-338`, so concurrent failures on Postgres produce duplicate buckets and an undercount. Third, and most awkward: **nothing in the repo reads this table** — no lockout, no alerting, no admin view — so it is currently write-only evidence.

- [ ] **Q7.** Every request resolves the session four or five times, and each resolution writes and commits. Is the sliding idle timeout worth that?
    **A:** `user_for_token` (`service.py:767-792`) enforces both expiries then writes `last_seen_at` and commits. It is called from `attach_current_user`, again inside `current_brand_summary` → `resolve_session_brand`, a third time for the `switchable` count, a fourth for `brand_options` when the switcher renders, and a fifth from `enforce_policy`. That is four or five `SELECT`+`UPDATE`+`COMMIT` cycles against the same `auth_sessions` row per page view, on Postgres, from two different sessions — so a user with several tabs open serialises on that row's lock. The related design point is defensible on its own terms: the session's `brand_id` is a cache revalidated against the grant table every resolution, so a revoked grant stops taking effect immediately. Could both properties be kept by resolving once into `request.state` and writing `last_seen_at` only when it has moved by more than a minute?

- [ ] **Q8.** Twelve tables via `create_all` and no Alembic. What is the actual migration story, and what is already un-migratable?
    **A:** `create_all` creates what does not exist and alters nothing. The startup re-sync in `ensure_builtin_roles` is the substitute for data migrations and works for adding a permission key to a non-customised preset role — but it **skips any role with `is_customised` set**, so a company that edited Manager never receives the new key. Removing or renaming a key orphans rows in both `role_permissions` and `integration_grants` with nothing to sweep them. Flipping a permission's membership in `BRAND_SCOPED` is a behaviour migration with no schema change at all: every existing integration call without `X-Brand` starts failing. The honest framing: this is a reference implementation trading migration tooling for readability — worth saying out loud which of the above you would fix first if it became a product.
