---
type: adr
status: accepted
topic:
  - architecture
  - content
  - decision
  - ai
  - language
created: 2026-10-17
modified: 2026-10-17
source:
  - "task-369 final-design pass (\"AI translates a content record into another language\"), decided by the user 2026-10-17, one question at a time"
  - "Business decision P2-F2, one variant per language (docs/playbook-strategy.md §5, 2026-10-09)"
depends_on:
  - "[[ADR-012 — Content Records Represent Communication Units]]"
  - "[[ADR-128 — Version Content for Auditability and Restoration]]"
  - "[[ADR-081 — AI Ranks Within Governed Candidate Sets]]"
  - "[[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]]"
  - "[[ADR-199 — Inline Personalisation Is a Brand's Expression Dictionary, Substituted After Escaping]]"
  - "[[ADR-174 — Channel Readiness Is Asserted, Not Computed]]"
  - "[[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]]"
  - "[[ADR-140 — AI Capability Layer]]"
  - "[[ADR-141 — In-App Assistive AI Actions]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
  - "[[ADR-082 — AI May Recommend but Not Publish]]"
  - "[[ADR-182 — A Click Credits Content Only When the Link Names It]]"
  - "[[ADR-013 — Content Reference Instead of Content Copy]]"
---

## Status
Accepted

## Context

**The request is queue task-369, raised by the user on 2026-10-11 for the November presentations:** "translate content". A manager asks for a content record in another language; the AI drafts the translated fields and a person reviews them. The 2026-10-11 entry of the decision log (`docs/playbook-strategy.md` §5) lists "AI that drafts, categorises and translates content" among the demo items. The task named four design questions: where a translation lives, which fields are translated, how a translation stays honest when the original changes, and its budget and prompt ([[ADR-144 — AI Data and Model Governance]]). The user decided them on 2026-10-17 in the task's final-design pass, one question at a time.

**No content record has a language today** (verified 2026-10-17). `ContentRecordDB` (`backend/app/content/db_models.py:6`) has no language field. A message gets its language only from its brand profile:

- **One brand profile per language, and the profile records its language** ([[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] point 6).
- **A message's language is its brand profile's language, frozen with the snapshot** ([[ADR-199 — Inline Personalisation Is a Brand's Expression Dictionary, Substituted After Escaping]] point 4).

**The business decision behind multilingual sending is P2-F2, "one variant per language"** (decision log, 2026-10-09). Each language is its own variant, sent to an audience filtered by the recipient's language. That is today's tools and no new layer. *"A language axis on content is a later idea, if the pattern proves too laborious."*

**A slot's candidate set does not look at language.** The governed candidate set of [[ADR-081 — AI Ranks Within Governed Candidate Sets]] is built in `candidate_query` (`backend/app/decision/strategies/base.py:209`). It filters on brand, status, machine ready, channel readiness and the slot module's required fields ([[ADR-174 — Channel Readiness Is Asserted, Not Computed]], addenda of 2026-10-05). It has no language filter. Once translations exist, a German variant's slot could pick the English original.

**A record is one reusable communication unit** ([[ADR-012 — Content Records Represent Communication Units]]), and **a record is identity while a version is historical state** ([[ADR-128 — Version Content for Auditability and Restoration]]).

**Options not taken, with the reason given.**

- *A language version inside the same record* was the other shape task-369 named. It was not taken. It is the language axis on content that P2-F2 leaves for later. A translation as its own record leaves versions, snapshots and reconstruction unchanged.

**No supersession.** No Accepted Decision section is changed. Point 2 narrows the candidate set of [[ADR-081 — AI Ranks Within Governed Candidate Sets]] by one more condition, as the addenda of [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] and [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]] did before it. The AI task's lack of an approval step is recorded in [[ADR-140 — AI Capability Layer]]'s addendum of 2026-10-17.

## Decision

### A record's language

**1. A content record may have a language.**

- **It is chosen on the record from the languages of its brand's profiles, or left not set.**
- **Records that exist today stay not set.**
- **Not set means the record carries no language claim.** It stays eligible in every language.
- **This keeps P2-F2.** A language is a label on a record, not a language axis inside one.
- **A record's language is locked while it is linked.** An original with translations, and every translation, keeps its language. The choice is shown but not offered, with the reason. A record with no translations may change its language freely.

### Which records a slot may pick

**2. A decision slot picks only records in its variant's message language, or records with no language set.**

- **The message language is the variant's brand profile's language** ([[ADR-199 — Inline Personalisation Is a Brand's Expression Dictionary, Substituted After Escaping]] point 4).
- **A fixed pick is chosen by a person and is not restricted.**

### A translation

**3. A translation is a new record in the same brand, linked to the record it was translated from.**

- **The record it was translated from is its original.** The translation has the target language set.
- **At most one translation per original per language.**
- **Only an original is translated.** A translation is not translated again into a third record, so the links stay one level deep.
- **Translating needs the original's own language set first.**
- **The target is one of the brand's profile languages other than the original's.**

**4. What a translation holds.**

- **The model translates the original's filled title, description, text and rich-text fields, and image descriptions (alt text).**
- **Links and images are copied unchanged.**
- **Personalisation placeholders (`{{...}}`, [[ADR-199 — Inline Personalisation Is a Brand's Expression Dictionary, Substituted After Escaping]]) are kept verbatim.** Their per-language cases live in the dictionary.
- **The original's categories and scores are copied.**
- **The new record starts unpublished, not ready for any channel and not machine ready** ([[ADR-174 — Channel Readiness Is Asserted, Not Computed]]; [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]], addendum of 2026-10-05). Publishing and readiness stay a person's acts.
- **Its page opens saying it was translated by AI from the original** and should be reviewed before publishing.

### Staying honest

**5. A translation shows when its original has changed, and nothing is overwritten by itself.**

- **The translation keeps the original's text it was translated from.**
- **When the original's text fields differ from that text, the translation's page says the original changed since it was translated** and offers **Translate again**.
- **Translate again is a fresh translation of the changed original, shown as a proposal.** A person takes it field by field with ticks, as with the content draft ([[ADR-141 — In-App Assistive AI Actions]], addendum of 2026-10-16).
- **Honesty is kept per field.** Each translation run keeps the original's text it translated (the record's own content, not recipient data — [[ADR-144 — AI Data and Model Governance]] point 4). Taking a field from a run records that run's original text for that field, so the field is up to date exactly when the original's text for it has not changed since. The page names the fields whose original changed.
- **The original's page lists its translations.**

**6. Deleting an original leaves its translations standing, unlinked.**

### The AI task

**7. No approval step.** The translation task has no held form ([[ADR-140 — AI Capability Layer]], addendum of 2026-10-16, and its addendum of 2026-10-17).

**8. Spend follows [[ADR-144 — AI Data and Model Governance]].**

- **One model call per translation, with a declared output ceiling** (point 5).
- **The input is the record's own content, not recipient data** (point 4).

## Consequences

### Positive

- **It fits one variant per language.** Versions, snapshots and reconstruction do not change.
- **Slots stop mixing languages.** A German variant's slot no longer picks an English record that carries a language.
- **A stale translation is visible.** Its page says when the original changed, and Translate again offers the change as a proposal.
- **Existing records are unaffected.** They stay not set and eligible in every language.

### Negative

- **Categories and scores are copied, so they can drift apart** between an original and its translation. Signal and click credit are per record ([[ADR-182 — A Click Credits Content Only When the Link Names It]]), so an original and its translation collect them separately.
- **A brand must create a profile in a language before content can be marked or translated into it.**
- **A fixed pick in the wrong language is not caught.** The composer's language warning is still open in [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]].
- **Slots stay language-blind for records not set.** A record with no language is eligible in every language, whatever language its text is in.
- **Changing a translated original's language means deleting its translations first** (point 1's lock). No other way to unlink them is decided. Point 6 unlinks translations only when the original itself is deleted, and then leaves them standing.

## Notes

- **Point 2 narrows ADR-081's candidate set.** It adds one condition to the governed candidate set of [[ADR-081 — AI Ranks Within Governed Candidate Sets]]. [[ADR-174 — Channel Readiness Is Asserted, Not Computed]]'s second addendum of 2026-10-05, point 3, put the earlier candidate conditions in `candidate_query` so that every strategy and the read-only candidate count draw on the same set. Where this condition lands is the build's.
- **Why point 1 locks a linked record's language.** It prevents an original quietly becoming the language of its own translation.
- **Why point 5 keeps honesty per field.** A whole-record timestamp also moves on edits that do not touch text (readiness, machine ready), and would leave a freshly re-translated record marked as changed. Per field, partly taking a new translation is shown truthfully.
- **How this stands to ADR-013.** [[ADR-013 — Content Reference Instead of Content Copy]] governs composition: a campaign references content records instead of copying them into builder state. A translation is a record of its own, not composition state, so it does not touch that rule. Its addendum of 2026-09-16 meant to keep the provenance of a cross-brand copy in the audit log rather than in a column. Here the link to the original is part of the record, because points 3, 5 and 6 read it.
- **Alt text, against the content draft.** The content draft task never drafts image descriptions, because the model cannot see an image ([[ADR-141 — In-App Assistive AI Actions]], addendum of 2026-10-16, point 4). The translation task translates alt text that already exists, so that reason does not arise. Alt text takes no personalisation entries ([[ADR-199 — Inline Personalisation Is a Brand's Expression Dictionary, Substituted After Escaping]], addendum of 2026-10-16, point 1).
- **What point 4's verbatim placeholders mean under ADR-199.** A placeholder copied into a translation resolves from the dictionary's cases in the message language. If an entry has no text in that language, a send whose own texts use it is refused, and a recipient whose slot pick uses it is excluded (ADR-199 point 12 and its addendum of 2026-10-16, point 2).
- **Point 4 is ADR-141 point 5's case.** AI-authored content is written as an unpublished draft, and going live is the person's publish step ([[ADR-141 — In-App Assistive AI Actions]] point 5; [[ADR-082 — AI May Recommend but Not Publish]]).
- **Not decided here, and not put to the user.**
  - **A record whose language no longer matches any of its brand's profiles,** for example after that profile is deleted. The current default, which the build follows: the record keeps its language and shows it; slots match it only in a variant whose profile has that language; nothing else happens.
- **The decision log.** `docs/playbook-strategy.md` §5 has no entry for the 2026-10-17 session. This record keeps P2-F2 (2026-10-09) as written. The reasoning comes from the user's decisions in task-369's final-design pass.

## Related ADRs

### Depends On
- [[ADR-012 — Content Records Represent Communication Units]] — a record is one reusable communication unit; a translation is a record of its own.
- [[ADR-128 — Version Content for Auditability and Restoration]] — record is identity, version is historical state; neither changes.
- [[ADR-081 — AI Ranks Within Governed Candidate Sets]] — the governed candidate set that point 2 narrows by the message language.
- [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] — one profile per language (point 6); a record's languages are its brand's profile languages; the composer warning still open.
- [[ADR-199 — Inline Personalisation Is a Brand's Expression Dictionary, Substituted After Escaping]] — the message language (point 4) and the placeholders a translation keeps verbatim.
- [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] — a translation starts not ready for any channel; candidate conditions live in the shared candidate set.
- [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]] — a translation starts not machine ready (addendum of 2026-10-05).
- [[ADR-140 — AI Capability Layer]] — no held form for the translation task (addenda of 2026-10-16 and 2026-10-17).
- [[ADR-141 — In-App Assistive AI Actions]] — Translate again is taken with ticks, as the content draft; AI output is an unpublished draft (point 5).
- [[ADR-144 — AI Data and Model Governance]] — one model call with a declared output ceiling (point 5); no recipient data in the input (point 4), which also covers the original's text a run keeps.
- [[ADR-082 — AI May Recommend but Not Publish]] — the translation does not publish itself.
- [[ADR-182 — A Click Credits Content Only When the Link Names It]] — click credit is per record, so an original and its translation collect it separately.
- [[ADR-013 — Content Reference Instead of Content Copy]] — governs composition, not a translation record (Notes).
