---
type: interview-prep
status: open
topic:
  - architecture
  - review
  - baseline
created: 2026-07-04
modified: 2026-07-04
source:
  - claude-baseline-review-2026-07-04
depends_on:
  - "[[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]"
  - "[[ADR-060 — Rendering as Independent Layer]]"
  - "[[ADR-061 — Snapshot Based Final Rendering]]"
  - "[[ADR-062 — Snapshot Stores Final Render State]]"
  - "[[ADR-063 — Rendering Parity Over Rendering Implementation]]"
  - "[[ADR-131 — Email Module Templates Use MJML as Source Format]]"
---

# Interview Prep — Snapshots, Rendering, Email Modules

Baseline review generated 2026-07-04. Check off each item once discussed, and record the decision made in **Resolution**.

## Snapshots

- [ ] **Q1.** `create_snapshot_for_variant` builds `render_context` twice, discarding the first — dead code or a real issue?
    **A:** Harmless dead code (a throwaway dict immediately overwritten) — signals incremental evolution without cleanup, likely a leftover from before `build_render_context` was introduced. `snapshots/service.py:96-138`.
    **Resolution:**

- [ ] **Q2.** Is the ADR-drift-report's [[ADR-062 — Snapshot Stores Final Render State]] finding (snapshot doesn't store resolved render state) still accurate?
    **A:** No — stale. Commit 431c053 (one day after the drift report) added `render_context` with module/content/decision resolution. Overrides and merge-context data are still absent, so partial drift remains — worth re-running the drift report.
    **Resolution:**

- [ ] **Q3.** `build_render_context` and `render_variant_html` independently re-derive resolution state — what if they disagree?
    **A:** No shared transaction or lock — a concurrent decision-engine change between the two calls can make the stored `render_context` describe different content than the HTML actually baked into the snapshot file. Narrow race window, worth a decision on whether to derive both from one resolution pass.
    **Resolution:**

- [ ] **Q4.** What was the actual root cause behind commit 40bbe63's snapshot storage-path fix?
    **A:** A relative path (`../storage/snapshots`) resolved against the process's launch-time working directory, not the module's location — non-deterministic depending on where uvicorn/pytest was started from. Fixed by anchoring on `Path(__file__)`.
    **Resolution:**

- [ ] **Q5.** `recipient_id` is optional, and per-recipient snapshots still only store module/content resolution, not a Merge Context (firstname, language substitutions, etc.) — confirmed gap?
    **A:** Yes — matches the known open item on Merge Context (see project notes / [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]). A per-recipient snapshot can tell you *which content* was shown but not what merge-field values were substituted.
    **Resolution:**

- [ ] **Q6.** No uniqueness/idempotency key on snapshot creation — what happens on repeated calls for the same variant/recipient?
    **A:** Unbounded accumulation of near-duplicate snapshots — consistent with "immutable append-only history" intent (ADR-061) but with no lifecycle/cleanup story, and no TTL or delete endpoint exists.
    **Resolution:**

## Rendering

- [ ] **Q1.** Rendering re-queries and re-renders from scratch on every call, with no caching — correct given the snapshot is the frozen artifact?
    **A:** Yes, by design — rendering is meant to be a stateless, idempotent live projection ([[ADR-060 — Rendering as Independent Layer]]); caching only matters if preview traffic scales up meaningfully.
    **Resolution:**

- [ ] **Q2.** CSS inlining re-reads and re-inlines `brand.css` from disk on every single render — what's the cost at per-recipient send scale?
    **A:** No caching (`_load_brand_css` has no `lru_cache`) — becomes O(recipients) redundant full CSS-inlining passes if `render_variant_html` is ever called per-recipient, which ADR-005's recipient-specific artifact path anticipates. Easy, low-risk optimization left on the table.
    **Resolution:**

- [ ] **Q3.** Walk through the actual root cause of commit 40bbe63's "empty content in snapshot HTML preview" bug.
    **A:** Two combined bugs: the snapshot storage-path issue above, plus `resolve_renderable_content`'s live-record fallback returning only `{"title","body"}` while CMS templates (e.g. `single_stack`) expect `headline_medium`/`body_medium` — content without a pinned version rendered with empty headline/body. Fixed by adding hardcoded field aliases, not a schema-level fix.
    **Resolution:**

- [ ] **Q4.** The alias fix hardcodes exactly two field names — what happens if a new template introduces a different variable name (e.g. `headline_short`)?
    **A:** Reproduces the identical bug silently (empty string, no error) — the underlying schema mismatch between `ContentRecordDB` (`title`/`body`) and `ContentVersionDB.content` (arbitrary keys) is still unresolved; the fix only patches the two currently-shipped template field names.
    **Resolution:**

- [ ] **Q5.** Does `resolve_content_for_module`'s decision-slot lookup guarantee the same content across two calls for the same recipient?
    **A:** No — orders by `created_at.desc()` and takes the first match, with no version pinning at the resolution level. Preview and snapshot can diverge non-deterministically if a new `DecisionResolutionDB` row is inserted between calls (e.g. decision engine reruns).
    **Resolution:**

- [ ] **Q6.** Jinja's `Environment()` has autoescaping off — is CMS body content safe from injection into the rendered email HTML?
    **A:** Template *source* (the `.html` module files) is trusted; user-supplied CMS content is rendered unescaped into the output. Worth an explicit decision on whether this is intentional (email HTML often needs raw markup in body fields) or should be locked down.
    **Resolution:**

## Email Modules

- [ ] **Q1.** [[ADR-131 — Email Module Templates Use MJML as Source Format]] mandates MJML source compiled by a frontend layer — is that implemented?
    **A:** No — 100% of shipped templates (`hero`, `cta`, `single_stack`, `img_left`, `img_right`) use raw HTML, the ADR's own stated "escape hatch," and the ADR was accepted the same day as the commit that built the opposite of what it describes. Not yet reflected in the drift report (which predates ADR-131).
    **Resolution:**

- [ ] **Q2.** `_REGISTRY` is built once at import time — what happens if a manifest/template file changes while the server runs?
    **A:** Nothing refreshes it — template *HTML* re-reads fresh from disk on every render call, but the *manifest* (variables, cms flag, label) is frozen until restart. Inconsistent freshness between the two halves of the same registry. `email_modules/registry.py`.
    **Resolution:**

- [ ] **Q3.** Manifest/template pairing is filename-convention-based, with only a warning logged on mismatch rather than a startup failure — right tradeoff?
    **A:** Favors availability (one broken template silently drops out of the registry) over strictness — but a genuinely malformed JSON file has no try/except around `json.loads()` and would crash the *entire app* at import, contradicting that same graceful-degradation intent elsewhere in the same function.
    **Resolution:**

- [ ] **Q4.** The "no mapping layer, exact variable name match" convention — has this already caused a production-visible bug?
    **A:** Yes — directly caused the commit 40bbe63 empty-content bug (Rendering Q3/Q4 above). The convention is elegant (zero Python for new templates) but fragile against any content source whose schema doesn't match a template's variable names.
    **Resolution:**

- [ ] **Q5.** `get_template_html` renders arbitrary Jinja2 from files with no sandboxing — what's the trust boundary?
    **A:** Acceptable if `storage/email_modules/` stays deploy-time/CI-controlled like source code (current assumption); would become an SSTI risk if ever exposed to a lower-trust "upload your own template" feature. Worth stating explicitly as a non-goal if that's the intent.
    **Resolution:**

---
## Related
- [[MOC - Interview Prep Baseline]]
- [[MOC - Rendering Architecture]]
