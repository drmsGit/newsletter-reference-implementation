---
id: TASK-71
title: >-
  Rework seed/demo content into realistic material — prerequisite for testing
  Mode A.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:57'
updated_date: '2026-10-17 13:43'
labels:
  - backend
dependencies: []
type: feature
ordinal: 201050
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** **Rework seed/demo content into realistic material — prerequisite for testing Mode A.** Surfaced 2026-07-31 (user). Today's seed content records are placeholders along the lines of *"this is content about X"* — fine for exercising plumbing, **useless for evaluating an AI feature**: a subject-line or content-suggestion task fed placeholder text produces generic output, so a test would be a **false negative** (concluding the feature doesn't work when the input simply carries no signal). Needs: real headlines and body text, realistic length, and enough **category variety** that personalization differences are visible between recipients. Keep the existing outdoor / hiking / wildlife theme so the demo narrative stays coherent. **Two payoffs:** it unblocks meaningful Mode-A testing *and* it is what a prospect actually sees in a demo (same "realistic volumes matter when presenting" argument as the pagination item). **No conflict with [[ADR-143 — AI-Assisted Development Boundary]]:** content records are not personal data — it is *recipient* data that must be pseudonymized, not editorial content. Source: user, 2026-07-31 (raised as a blocker before the Mode A build).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. backend/scripts/demo_reset.py (needs --yes; refuses the test database), the work in backend/app/demo/. 2. Keep: users, roles, grants, sessions and sign-in codes, Settings (app_config, ai_prompts), integrations with keys and grants, the audit log, schema_migrations. Empty: every other table, the asset files, every brand but the default (renamed Grathaus Outdoor, key unchanged) and Grathaus Touren (added; the default brand admins get admin there). 3. Brand profiles: Outdoor marketing de (default), marketing en, transactional de; Touren marketing de, transactional de; legal details on grathaus.example. The dictionary from the starters. The category tree as approved. 4. Import backend/scripts/demo/content/batch-*.csv (brand, language, all fields, push fields, image keys, scores) and the English batch, linked to their German originals by the same brand and button_url (ADR-200); images from backend/scripts/demo/images uploaded per brand with alt texts; records published, ready for email (and push where they have push text), machine ready. Missing files are reported, not faked. 5. 1,000 fictional recipients (mostly de, some en; genders and missing names so both salutations show), consent and addresses, push for a share, interests. 6. The editions from editions.csv: each sent through the real path with the mock provider to a segment of at most 200 that fits it, then dated back; opens, clicks on what each delivery carried, and one unsubscribe; signals from the clicks. 7. Ready-to-demo campaigns: an empty email variant for Prepare from a topic, a draft edition, a push for a store event, the two transactional mails. 8. task-381 in the same change. 9. ADR-197 addendum: a full demo reset deletes assets. 10. Tests on the parts and one full run on a throwaway database; the dev database only with the user's go-ahead.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 218, section "Features", position 24 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08 queue cleanup (backlog-sequencer run 3, verified by hand): partly done. Realistic content exists as backend/scripts/seed_content_chatgpt.csv with its importer, backend/scripts/import_content_csv.py, and seed_content_prompt.md. The demo seed itself still writes placeholder bodies, at backend/scripts/seed_demo_data.py:146 ("An editorial piece about ... issue N"). Mode A in this dated entry is now called Assistive (ADR-140 addendum 2026-10-08).

2026-10-11, the user set the November 2026 presentations as the focus (docs/business/PRESENTATIONS-2026-11.md). Also wanted: a demo reset that leaves believable results (deliveries, clicks, an unsubscribe), so the campaign's results section and the category graph have something to show.

From task-371 (2026-10-15): the two demo brand profiles (one marketing, one transactional) named in task-371's title are done here, with the realistic seed. The seed records need real square images from the library (ADR-198 point 2): today they hold relative /static/img paths that do not load in the preview or an email.

Interview 2026-10-17, one question at a time, to pick the topic that shows every use case: (1) An outdoor gear retailer with its own guides (keeps the outdoor/hiking theme): trail and trip guides as editorial records, gear and offers as records, seasons and activities as categories, order and booking mails for the transactional profile, in-store events for push. (2) One fully seeded brand plus a small second brand of the same company (e.g. its guided-tours arm) to show brand switching and isolation. Correction from the user: one installation per company, the brands are the company's own; agencies get access to a company's installation, they never run several clients in one platform. (3) German first, some English: the catalogue in German, a German and an English brand profile, a handful of records already translated (linked, ADR-200), recipients mostly de and some en. (4) Large: about 150 records, about 20 categories (some nested), about 1,000 recipients with interest profiles from past clicks, past editions sent with believable results and an unsubscribe. A live send on stage goes to a segment of at most 200 (the dev send cap stays 200). (5) The content is written by ChatGPT from a prompt I prepare (seed_content_prompt.md reasoning: the AI features are tested on prose they did not write); the user runs it in batches and drops the CSVs in the repo. (6) About 40 shared square images, generated by the user in ChatGPT from image prompts I write, uploaded by the seed into the brand library with alt texts (ADR-198). (7) One demo reset command: empties the dev data and seeds everything the same every time; task-381 (retired modules) done in the same reset; settings such as the AI prompts and provider kept.

2026-10-17: name Grathaus (Grathaus Outdoor, brand key outdoor; Grathaus Touren, brand key touren) and the category tree approved by the user: 9 main, 15 sub, three subs under two parents (Klettersteige under Wandern and Klettern, Familienwandern under Wandern and Familie & Kinder, Lawinenkunde under Wintersport and Sicherheit & Wissen); seasons, content kind and offers are not categories (ADR-175, facets). Kammweg was rejected as a name: it is a real long-distance trail with its own tourism association. The ChatGPT prompt is written (4f6747b, backend/scripts/seed_content_prompt.md): shared rules, six batches of 25, an English batch, an editions and transactional batch, 40 image prompts; files land in backend/scripts/demo/content and backend/scripts/demo/images. Next: the user runs the prompts; then the demo reset command and the importer extension (brand, language, image keys, push fields, editions).

2026-10-17: the reset command built (66a9515): backend/scripts/demo_reset.py and backend/app/demo/ (catalogue, people, editions, reset), the demo.reset audit action, ADR-197 addendum 2026-10-17. Decided in its design pass: keep people and settings (accounts, roles, grants, Settings, integrations, audit log); rename the default brand Grathaus Outdoor and add Grathaus Touren; send each past edition to its segment of at most 200 through the real path. Tested: 13 cases incl. one full run on the test database with generated CSVs (then the baseline restored); full suite green apart from the unrelated retired-name check. Found and fixed on the way: the guard first compared with the dev URL, which in tests is the test database; it now refuses any *_test* name and pytest or CI. task-381 moved to right after the first reset of the dev database (variants there may still hold the retired module until then). Not yet done: running it with the real batches and images, on the dev database (needs the user's go-ahead).

2026-10-17, the content arrived complete (158 rows, 9 edition word sets, 40 images at 600x600) and read with no problems. Ran demo_reset.py --yes on the dev database with Diede's go-ahead. Two defects found and fixed on the way (8973758): the reset stopped on a sign-in session whose working brand was a removed brand (now cleared, as the column allows), and every edition showed 0 delivered because the mock provider reports nothing (the reset now adds delivered and bounce events) and its dates were the reset's day (now the edition's). Left as the product's own: sent campaigns still say draft, because sending does not change a campaign's status; and back-dated sends show the note that unsubscribes before 2026-10-12 are not counted (UNSUBSCRIBES_COUNTED_SINCE, backend/app/campaigns/results.py:45), which is true of them.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The Grathaus demo: the content (158 records, 40 images, edition words) written with seed_content_prompt.md, and demo_reset.py, which empties the demo data and builds two brands, 1000 readers, five sent editions through the mock provider within the send cap, two drafts and the special cases (Prepare from a topic, push, two service mails, German and English). Run on the dev database on 2026-10-17 with the go-ahead. Verified by the reset tests (15, including a new one for a removed brand someone is signed in to), the full backend suite (2187 passed; the one known retired-name failure deselected), and a live look at the campaigns and their results in the browser pane.
<!-- SECTION:FINAL_SUMMARY:END -->
