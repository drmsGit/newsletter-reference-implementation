---
type: adr
status: proposed
topic:
  - architecture
  - channels
  - rendering
  - snapshot
  - templates
created: 2026-09-01
modified: 2026-09-01
source:
  - "Omni-Channel design interview (interview-prep, closed 2026-09-01), Cluster 3 / Q11–Q15"
depends_on:
  - "[[ADR-060 — Rendering as Independent Layer]]"
  - "[[ADR-062 — Snapshot Stores Final Render State]]"
  - "[[ADR-063 — Rendering Parity Over Rendering Implementation]]"
  - "[[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]"
  - "[[ADR-160 — Channel Model and Composition]]"
enables:
  - "[[ADR-161 — Channel Execution Shapes]]"
---

## Status
Proposed

## Context

Rendering is where the email assumption is most deeply set. `render_variant_html()` returns HTML; the snapshot schema says so in its column names — `html_storage_type`, `html_location`, `html_size`; `VariantDB.subject` and `VariantDB.preheader` are first-class columns; and the module registry is named and shaped for MJML, in `email_modules`. `render_context` is already neutral, and [[ADR-060 — Rendering as Independent Layer]] already places rendering behind a boundary, so the seams exist.

[[ADR-160 — Channel Model and Composition]] made channel a contract at authoring time and put the authoring contract in module manifests. This record settles what a renderer *is* across channels, what it returns, and where channel fields live — with the constraint that whatever comes out has to serve a push field dict, a letter PDF, a social creative and an email body, and has to be the thing a provider request can be traced back to.

## Decision

**1. The variant holds no channel fields at all. Subject and preheader become module fields, declared in a manifest.**
Subject and preheader are simply *fields of an email*, so they move into the composition: a `header` module for email whose manifest declares them, at position 0 — exactly as push's single module declares `title` / `body` / `image` / `link`. Nothing on `VariantDB` is channel-shaped.

Both offered alternatives were rejected for the same reason. **Channel-typed JSON on the variant** and a **per-channel side table** are each a *second* place where channel fields live, beside the manifests, and the failure mode is the familiar one where one gets updated and the other does not.

Three things it buys. **Overrides work unchanged** — the override layer edits module fields, so a personalised subject line comes free instead of needing its own mechanism, which it cannot have today because subject is not a module field ([[ADR-040 — Introduce Override Layer]]). **Mode A generalises without a special case** — "suggest subject & preheader" currently reaches into variant columns; as module fields, one task shape covers a push title or a letter salutation ([[ADR-141 — In-App Assistive AI Actions]]). And there is **no third pattern** to keep in step.

**2. The renderer contract is `render(composition, merge_context)`, receiving fully resolved content.**
Decision slots are resolved, overrides applied and content versions pinned *before* the renderer sees anything — **it formats, it never decides**. That keeps editorial and personalisation logic in the decision layer where it stays explainable, matches the finding that a push renderer fills fields and has no layout job, and is [[ADR-060 — Rendering as Independent Layer]] taken seriously.

**3. Rendering returns a set of artifacts, each with a role, plus a package hash over the set.**
The return type is the crux: email returns HTML, push a field dict, letter a PDF, social creative fields plus media — so the contract cannot be `-> str`. It returns **`Artifact`** values carrying media type, payload, size and a **content hash from the start**, and it returns a **collection** of them with roles such as `body_html`, `body_text`, `address_manifest`, `creative_image` — push returns one, email two, letter a PDF plus its address manifest.

**Email already needs this today**, which is what settles it: `multipart/alternative` — an HTML body *and* a plain-text alternative — is twenty-year-old standard practice whose absence spam filters penalise. "One artifact per execution" was a constraint being lived with, not a simplification chosen. **The hash covers the set, not a member**: hashing only the HTML would leave the plain-text part unverified, and the two will eventually diverge.

The hash is not decoration. It is the immutable per-delivery package a provider request can be traced back to, so that *"snapshot reviewed"* actually proves *"content sent"* — the gap the code review's P1-04 finding names, and the two-artifact framing it recommends (an approval snapshot, and an immutable per-delivery package). This is also where the `html_*` → `artifact_*` + media-type rename lands, and it is [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] landing where it always pointed: that record already separates snapshot state from the recipient delivery artifact, and this gives the second half a shape.

**4. The renderer registry is keyed by channel, auto-registering — one renderer per channel, not per provider.**
Auto-registration follows the `decision/strategies/` idiom and the "drop a file" standard set in [[ADR-160 — Channel Model and Composition]]. The artifact belongs to the **channel**; the provider merely transmits it. A push artifact is the same whether FCM or OneSignal carries it, which keeps the capability split of [[ADR-161 — Channel Execution Shapes]] intact and means swapping vendor never changes what gets rendered.

For email, MJML compilation stays in the frontend layer per [[ADR-131 — Email Module Templates Use MJML as Source Format]]: the email renderer assembles already-compiled module HTML and inlines CSS. It does not gain a compiler.

**5. Module manifests gain both a channel directory and a channel declaration, with a startup assertion when they disagree.**
Directory per channel (`modules/email/`, `modules/push/`) **and** the channel declared in the manifest; the loader fails at startup if they contradict each other.

**Namespace**, because name collisions are real — "hero" is natural in email, letter and social, and flat organisation just re-implements namespacing inside filenames. It also makes "drop a file" literal and keeps a designer working on email from scrolling past push modules. **Declaration**, because a manifest read on its own should say what it is for; location-only makes the file meaningless outside its directory, which bites in review, in docs and in error messages. **The assertion matters more than either**: a misfiled manifest would otherwise surface as a manager being offered a module that cannot render. Same fail-closed idiom as unmapped write routes and the webhook secret.

The renames that follow: `app/email_modules/` → `app/modules/`, `storage/email_modules/` → `storage/modules/email/`, with the registry loading per channel. [[ADR-131 — Email Module Templates Use MJML as Source Format]] stays intact — MJML remains the *email* module format, not the module system's format.

**6. Composition is not an email peculiarity; push is the exception.**
The question of whether any channel but email actually needs modules checks out in the opposite direction, which strengthens point 5. A **letter is genuinely compositional** — salutation, body sections, offer block, footer; a printed piece resembles a newsletter — and **carousel social ads** are several ordered cards each with image, headline and link. Only push is flat. Channel-neutral wording plus per-channel splitting is therefore the scalable choice, and the `max_modules` channel fact already spans the range — push declares 1, email and letter unbounded — with no special-casing.

**7. Rendering parity was never a cross-channel claim, so the cross-channel parity question dissolves.**
[[ADR-063 — Rendering Parity Over Rendering Implementation]] was reread rather than assumed: its parity is between **preview, final rendering and snapshot** — three *render contexts of one thing* — permitting browser-friendly markup in the builder and nested tables in the final email so long as they represent the same intended output. That is a **within-channel** guarantee and it generalises unchanged: for push, a mock notification card in the UI versus a JSON payload; for letter, an on-screen preview versus a print-ready PDF. Cross-channel sameness was not lost here, it was rejected in [[ADR-160 — Channel Model and Composition]] — per-channel variants exist precisely because a social ad is not a squeezed newsletter — so "parity between an email and a letter" was never a goal.

What improves and what does not is worth stating rather than overclaiming. The point 3 content hash makes the **snapshot ↔ sent** half checkable for the first time. **Preview ↔ final stays a testing concern**, because ADR-063 deliberately permits different implementations there, so those artifacts differ by design and their hashes will not match.

## Consequences

### Positive
- There is exactly one place channel fields are declared — the module manifest — so there is no second declaration to drift out of step.
- A personalised subject line becomes an ordinary override, with no mechanism of its own.
- Mode A suggestion tasks generalise across channels without per-channel special cases.
- The renderer cannot make editorial choices, because everything is resolved before it is called; explainability stays in the decision layer.
- The content hash turns "the reviewed snapshot is what went out" from an assumption into a check, closing the traceability half of code-review finding P1-04.
- `multipart/alternative` becomes expressible, which it was not under a single-artifact model — a present-day email deficiency fixed by a change made for other channels.
- A misfiled module manifest fails at startup rather than at a manager's fingertips.
- Swapping a provider never changes what is rendered.

### Negative
- **Two columns move into module data.** `VariantDB.subject` and `VariantDB.preheader` require a migration, and the send path reads `variant.subject` directly today — the same code P1-04 already says needs rework.
- **"What is the subject of this variant" becomes a lookup rather than a column**, which matters for list views and sorting.
- **Every renderer returns a collection even when it has one thing to give**, and every consumer handles a set.
- Directory-plus-declaration is deliberate redundancy: the same fact is stated twice and kept honest by an assertion, rather than stated once.
- The renames touch code paths (`app/email_modules/`, `storage/email_modules/`) and the snapshot schema's `html_*` columns, so this is a migration, not an addition.
- The content hash does **not** verify preview against final output. That parity remains a testing obligation, and saying otherwise would overclaim.

## Notes

- **Amendments other records need, none of them made here.** [[ADR-063 — Rendering Parity Over Rendering Implementation]] needs **wording only** — "the same intended newsletter output" becomes "the same intended channel artifact" — which is an amendment, explicitly not a superseding decision. [[ADR-062 — Snapshot Stores Final Render State]] needs its wording generalised from a single final render to a **package** of role-tagged artifacts with a hash over the set. Both are the dated-addendum pattern; neither Decision section changes.
- [[ADR-131 — Email Module Templates Use MJML as Source Format]] needs **no** amendment. The renames are to code paths, not to its decision: MJML remains the email module source format and compilation stays in the frontend layer.
- The renderer contract is written in two steps in the source interview — a single `Artifact` return, then widened to a set with a package hash. Point 3 records the settled form.

## Related ADRs

### Depends On
- [[ADR-060 — Rendering as Independent Layer]]
- [[ADR-062 — Snapshot Stores Final Render State]]
- [[ADR-063 — Rendering Parity Over Rendering Implementation]]
- [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]
- [[ADR-160 — Channel Model and Composition]]

### Enables
- [[ADR-161 — Channel Execution Shapes]]

### Referenced By
- [[ADR-040 — Introduce Override Layer]]
- [[ADR-041 — Override Precedence]]
- [[ADR-051 — Delivery Package Includes More Than HTML]]
- [[ADR-061 — Snapshot Based Final Rendering]]
- [[ADR-102 — Rendering Prepares Tracking Metadata]]
- [[ADR-128 — Version Content for Auditability and Restoration]]
- [[ADR-131 — Email Module Templates Use MJML as Source Format]]
- [[ADR-141 — In-App Assistive AI Actions]]
