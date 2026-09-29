---
id: TASK-219
title: >-
  storage/fields.json per ADR-177 — CONTENT_FIELD_GROUPS and the CSV importer's
  duplicate collapse into it
status: Done
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-09-28 20:44'
labels:
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 208400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The catalogue field set is defined once, centrally, and derived from rather than repeated. The interview settled three layers of field definition together:

| Lives where | Carries |
|---|---|
| `storage/fields.json` (**new, central**) | `concept`, `size`, `type`, `note`, `envelope` — what a field *is* |
| the module's own manifest (**unchanged, drop-in**) | which fields it uses, and `required` for each — a property of *(module, field)* |
| `ContentRecordDB.content` | the values, in one unvalidated JSON column, needing **no migration ever** |

The gaps, as each interview logged them:

| # | Gap | Where |
|---|---|---|
| 3 | Catalogue field set should derive from manifests | `content/service.py:101` |
| 10 | `fields.json` does not exist; `CONTENT_FIELD_GROUPS` and its duplicate collapse into it | `content/service.py:101`, `scripts/import_content_csv.py:33` |

And from the Manager Workflow interview: **Maintenance that falls out**, needing no ADR: `CONTENT_FIELD_GROUPS` reads from the manifests rather than repeating them, and the duplicate email field list in `backend/scripts/import_content_csv.py:33-41` goes with it.

Source: [[Variant Editor - design interview]] → What Cluster 1 produced, gap 3, and What Cluster 2 produced, gap 10 (Q2.8, 2.10, 2.4); [[Manager Workflow - design interview]] → What Cluster 2 produced.

**Decided:** [[ADR-177 — A Field Is Defined Once, Required Per Module]].

**Verified against the code 2026-09-27:** `storage/fields.json` does not exist. `CONTENT_FIELD_GROUPS` is hardcoded at `backend/app/content/service.py:101-108` (its own comment at `:95-100` calls the manifests its proper home), consumed at `:142,146` and referenced from `backend/app/content/models.py:38`. The same email keys are repeated as `CONTENT_KEYS` in `backend/scripts/import_content_csv.py:33-40`.

Related: task-118 (📋, the question this implements).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

**Final-design pass, 2026-09-28. Two decisions taken, one premise of mine corrected, one dependency ruled out.**

**The blocker was a hole in ADR-177 point 7.** It said `CONTENT_FIELD_GROUPS` collapses into `fields.json` without saying how the channel grouping survives — that table is `{channel: fields}` and the file is flat. It is not cosmetic: it is the PATCH merge authority, *a caller may only clear what it was offering*, so losing it means editing a record with push switched off erases the push copy. **Settled: `fields.json` declares `channel` per field.** Deriving it from which modules use the field was refused, because modules are filed per channel and that is reading the manifests for channel — the 2026-09-22 ruling. Declaring is not deriving. `PRESENCE_SIGNIFICANT_GROUPS` gets the same home. Written up as a dated addendum to ADR-177.

**A size is not a point on a length scale**, and the same addendum records it. `hero` proves it: the largest type in an email, usually over a background image, so it must be **shorter** than `headline_medium`, which sits in a 50:50 block. `short / medium / long` invites the wrong mental model — a size names a rendering context, and how much text that context wants is a property of the context, not of the name's position in a sequence.

**My 'inventing a title and brand per row' warning was wrong.** Measured: 8 hero instances — one already bound to a content record, five with `module_data` like `{'headline': 'Edition 2'}`, one with headline **and** text, one with nothing at all. `title` comes from the existing headline and `brand_id` from module → variant → campaign. **Nothing is invented.** The empty one needs nothing; it becomes an unbound cms module, which ADR-086 hides and task-201's check correctly ignores. **The migration must carry the instance that has `text`** rather than assume every hero is headline-only.

**The dependency that was almost created, and is not.** Hero's fields are `headline_hero` and `button_label_hero`; it **drops `text`**, and the editorial becomes a module of its own. Had hero kept a hand-typed body beside catalogue fields it would have been a **mixed module**, which needs VE-14 — `cms` is a boolean and the renderer branches on it — so M1 would have been blocked on the gap the interview called the one to look at twice. It is not. The button's URL stays the unsized `button_url`, per ADR-177 point 5.

**Order of operations.** (1) `ModuleVariableOut` exposes the full descriptor — independent, ships alone, unblocks composer work. (2) `fields.json` + the registry reading it. (3) `CONTENT_FIELD_GROUPS` and the CSV importer's `CONTENT_KEYS` read from it. (4) `GET /content/fields`, which **does not exist**. (5) the `richtext` type replacing `_RICH_TEXT_FIELD` — task-222. (6) the hero rename, migration and flag flip, plus the new editorial module.

**Risks.** `merge_content_fields` is the dangerous one — its whole job is preventing silent data loss on PATCH, so pin *editing with push off does not erase push* **before** touching it. The CSV importer's `REQUIRED_COLUMNS` overlaps `CONTENT_KEYS`; collapsing one without the other leaves a half-duplicate. **Unverified:** whether any content record already carries a key no manifest declares — if so, a `fields.json` built from the manifests orphans it invisibly, which is the exact failure ADR-177 cites for derived keys. Check before writing the file, not after.

**Orphaned-key check, run 2026-09-28 before writing anything. Clean, and it found a free proof.**

**No orphans.** 161 content records carry 11 distinct keys, and **every one is declared by some manifest**. So a `fields.json` built from the manifests loses nothing — the failure ADR-177 cites for derived keys does not exist in this data. Check it again against a real adopter's database before assuming it generalises.

**Five variables are declared and never stored:** `subject`, `preheader`, `label`, `url`, `text`. Those are exactly the fields of the modules ADR-179 keeps `cms: false` — `header`, `cta`, and hero's doomed `text`. **The data already drew the line that record drew**, independently: fields belonging only to hand-typed modules have never been in the catalogue, because nothing ever put them there.

**The finding that changes the risk: `CONTENT_FIELD_GROUPS` is provably a duplicate, not approximately one.**

```
email  cms:true module fields  == CONTENT_FIELD_GROUPS['email']   exact match
push   cms:true module fields  == CONTENT_FIELD_GROUPS['push']    exact match
```

So the table is, identically, *the fields of `cms: true` modules grouped by channel*. Two consequences:

**(1) The catalogue's field set has a definition nobody had written down** — a field is a catalogue field when at least one `cms: true` module reads it. That is what `GET /content/fields` should expose, and it is a **narrower set than `fields.json`**, which must contain every declared variable including the static modules' — otherwise a manifest references a name with no definition, which is the fail-closed discovery error ADR-177's addendum describes. The ADR does not draw this distinction and the implementation must.

**(2) The riskiest step becomes verifiable instead of brave.** `merge_content_fields` exists to prevent silent data loss on PATCH, and the plan was to pin its behaviour before touching it. Better: after building `fields.json` with declared channels, assert that the derived `{channel: cms-true fields}` equals today's `CONTENT_FIELD_GROUPS` **exactly**. It does now, so any difference is a mistake in the new file rather than a judgement call — the collapse is provably lossless before the merge rule is touched at all.

**Expected change after ADR-179's hero flip:** `headline_hero` and `button_label_hero` join the email catalogue set, since hero becomes `cms: true`. That is the one intended difference, and the equality assertion above should be written to expect it rather than be surprised by it.

**Step 2 built 2026-09-28: `storage/fields.json` exists and the registry reads it. 669 tests passing, up from 666.** `CONTENT_FIELD_GROUPS` is untouched — this step only establishes the proof that makes touching it safe.

16 definitions, one per declared variable across both channels, each carrying `concept`, `channel`, `type` and — where they apply — `size`, `envelope`, `note`. `ModuleVariable` gains those five from the file; the manifest still supplies only `name` and `required`.

**The equality proof is now a test.** `test_the_declared_channel_reproduces_the_hardcoded_table_exactly` groups the `cms: true` modules' fields by their **declared** channel and asserts the result equals `CONTENT_FIELD_GROUPS` exactly. It does. So the collapse in step 3 can be made without touching `merge_content_fields` on faith, and any later difference is a mistake in the definition file rather than a judgement call. Mutation-verified: making the code fall back to the module's directory fails it.

**Fail-closed, and it costs one module rather than everything.** A manifest naming an undefined field raises `UndefinedFieldError` at discovery. `_discover` already draws this distinction — `MisfiledManifestError` is re-raised because a misfiled manifest offers a module on a channel that cannot render it, while everything else is swallowed with a warning because a typo costs that one module. An undefined field is the second kind. Mutation-verified.

**`fields.json` is strictly larger than the catalogue's field set**, and a test pins it: a `cms: false` module still names variables, so building the file from *what a content record can carry* would silently stop offering `header` and `cta`.

**A pre-existing test had to change, and the reason is the point.** `test_the_declaration_is_what_decides_not_a_hardcoded_name` plants a push manifest declaring an envelope field. It now has to plant the **definition** too, because that is what adding a field means under ADR-177 — otherwise the planted module is refused and the test passes for the wrong reason, proving that an undefined field is ignored rather than that a declared envelope changes the answer.

**Two things deliberately not done here.** The manifests still carry their inline `label`, read as a fallback so an unstripped manifest keeps working; stripping them belongs with the `note` split. And the six `note` values are carried verbatim from those labels — *'Preheader (inbox preview)'* is a label plus guidance, and separating them is a judgement rather than a migration.

**Still to do in M1:** steps 3 (collapse `CONTENT_FIELD_GROUPS` and the CSV importer's `CONTENT_KEYS`), 4 (`GET /content/fields`, which does not exist), 5 (`richtext` — task-222), 6 (the hero rename, migration and flag flip, plus the new editorial module).

**Step 3 done 2026-09-28: `CONTENT_FIELD_GROUPS` and the CSV importer's `CONTENT_KEYS` both collapsed. 670 tests passing, up from 669.**

`content_field_groups()` derives the map from the registry: the fields of `cms: true` modules, grouped by their **declared** channel. The old table's own docstring had asked for this — *when that list exists, this table should read from it rather than repeat it* — and ADR-177 made the list.

`CONTENT_KEYS` in `backend/scripts/import_content_csv.py` now reads the email group. It was a hand-kept copy of half the table, so a field added to the catalogue was **silently unimportable** until somebody remembered that file. `REQUIRED_COLUMNS` is deliberately left alone: it overlaps on two names but states which CSV *columns* are mandatory, which is a different claim from which keys get copied.

**The proof became a literal pin.** The equality test compared the derived groups against `CONTENT_FIELD_GROUPS`; with the table gone, comparing the function to itself would assert nothing, so the six email and four push names are now written out in the test. A change to `storage/fields.json` that moves a field between channels or flips a module's `cms` fails it — and the one expected change is noted in the test: `headline_hero` and `button_label_hero` join `email` when ADR-179's hero flip lands.

**A mutation run found that 'declared, never derived' was decoration.** Swapping the declared channel for the module's directory changed no result and failed no test, because the two agree by construction. That is the addendum's rule being unenforced — a later refactor could quietly go back to reading the directory. `test_the_declared_channel_wins_over_the_directory` now plants a field defined as `email` on a module sitting in `push/` and asserts the declared channel wins. Artificial on purpose: only a disagreement can show which source the code consults. The mutation now fails.

**Also caught:** including `cms: false` modules in the groups, and ignoring which groups a caller offered — the second breaks five tests, which is the guard against a PATCH erasing push copy doing its job.

**Process note:** I lost the step-2 registry work earlier by using `git checkout` to undo a mutation, against the standing rule never to `git checkout` a file with uncommitted work. Every mutation in this step restored from a `/tmp` copy.

**Step 4 done 2026-09-28: `GET /content/fields` exists. 675 tests passing, up from 670.**

Returns the fields a content record can carry, each with its definition — `concept`, `size`, `type`, `note`, `channel`, `envelope`.

**It returns a subset of `storage/fields.json`, not all of it, and ADR-177 point 7 is loose about this.** That point says the route *reads fields.json*; the file also defines the `cms: false` modules' variables — `subject`, `preheader`, `label`, `url`, `text` — and a content record carrying those would hold copy nothing ever reads, because a static module takes its values from `module_data`. So the route exposes the ten fields at least one `cms: true` module reads. Same rule as `content_field_groups()`, and the same one the hardcoded table encoded before either existed.

**`required` is absent on purpose** and a test pins its absence. It is a property of *(module, field)* — one module demands `body_medium` and another never mentions it — so the catalogue has no single truth to report, and reporting one would be reporting the wrong one. A client asking *must I fill this?* names a module and asks `GET /modules`.

**Declared before `/{content_id}`, which is correctness rather than style.** FastAPI matches in declaration order, so after it the path is read as a content id and answers 422. Mutation-verified by moving the route below its sibling.

**A test pins the route against the merge groups**, because they must describe one catalogue: if they drift, a client offers a field it may then not clear, which is how push copy gets erased from the other direction.

Mutation-verified: returning every definition rather than the catalogue subset fails, and so does declaring the route after `/{content_id}`.

**Remaining in M1:** step 5 (`richtext` — task-222) and step 6 (the hero rename, data migration and `cms` flip, plus the new editorial module). Step 6 is the only one that touches data.

**Step 6 done 2026-09-28. M1 complete. 681 tests passing.**

`hero` is `cms: true` and takes `headline_hero`, `button_label_hero` and the unsized `button_url`. It **drops `text`**, and a new `editorial` module carries body copy as `cms: false` — so editorial written for one send never becomes a single-use catalogue record, which is ADR-179 point 1's argument applied one module along. `text` was not orphaned by the drop; editorial took it.

**The migration is Python, not SQL, and that is a departure worth naming.** Every migration beside it is a `.sql` file. This one reads a JSON column, creates rows in another table and invents no values — expressing that as `module_data ->> 'headline'` inside a string would have been right once and unreviewable afterwards.

**Three cases, and only one was a migration.** Four heroes with `module_data` became content records carrying `headline_hero`, title from the headline and brand from module → variant → campaign. One of those also had `text`, and an `editorial` module was planted beside it rather than dropping the copy — losing it would have been the migration deciding the copy did not matter. One hero had neither and needed nothing.

**Three heroes were already bound, and were left alone deliberately.** Their records carry the catalogue's medium-size fields and no `headline_hero`. Copying `headline_medium` across was considered and rejected: a hero headline sits over a background image and must be short, a medium one need not be, so the guess ships a headline that does not fit and nobody is told. **Verified rather than asserted:** in preview the check reports `hero.headline_hero`; in send mode those records raise `UnpublishedContentError` first, so the send is refused by the publication gate before it is refused by name. Both refuse. Only the second names the field, and the migration's output says so.

**Idempotent, and proven by re-running** — a hero already carrying `headline_hero` is skipped, so a re-run after a partial apply finishes rather than duplicates.

**A bug the dry run could not have caught.** `--apply` died with `NoReferencedTableError`: `content_records.brand_id` points at `brands`, SQLAlchemy resolves that at **flush** time, and the dry run never flushes. The brand models are now imported for that side effect, with a comment saying why.

**The literal pin from step 3 did its job.** It failed the moment hero flipped, because `headline_hero` and `button_label_hero` joined the email group — exactly the change the test's own docstring predicted. Updated deliberately, which is what that test exists to force.

**Verified end to end:** a migrated hero renders its headline, the planted editorial renders its text, and the bound-but-headline-less variant reports the gap in preview.
<!-- SECTION:NOTES:END -->
