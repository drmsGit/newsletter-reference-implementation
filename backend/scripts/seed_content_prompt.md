# Demo content prompt — Grathaus (for ChatGPT or any external model)

**Why an external model.** The demo content feeds the AI features (subject
suggestion, draft, translation, variant from a topic). Content written by the
model under test makes those features look better than they are — its prose is
already easy for it to summarise. So the content is written elsewhere, from the
prompts below (task-71; the reasoning of the earlier travel version of this file).

**The company** (task-71 interview, 2026-10-17). *Grathaus* is a fictional
mid-sized outdoor company in southern Germany:

- **Grathaus Outdoor** — three stores (München, Augsburg, Rosenheim) and an
  online shop: gear, trail guides, offers, store events. Brand key `outdoor`.
- **Grathaus Touren** — the same company's guided tours and courses (hut
  weekends, climbing and ski-touring courses). Brand key `touren`.

One installation, one company, two brands of its own. German first; a few
records also in English.

## How to use

1. Run the **batches** below one by one in ChatGPT (paste the shared rules,
   then the batch). Save each answer as
   `backend/scripts/demo/content/batch-<N>.csv`.
2. Run the **English batch** with eight rows you choose from batches 1–6, and
   save it as `backend/scripts/demo/content/english.csv`. Each English record is
   linked to the German one with the same brand and `button_url` (ADR-200), so
   keep the link unchanged.
3. Run the **editions batch** and save it as `backend/scripts/demo/content/editions.csv`.
4. Generate the **images** from the list at the end, square, and save each as
   `backend/scripts/demo/images/<key>.jpg`.
5. Reset the dev database to the demo: `./venv/bin/python scripts/demo_reset.py --yes`
   (from `backend/`). It reports anything it could not use.

Content records are not personal data, so realistic content does not conflict
with ADR-143; only recipient data must be pseudonymised.

---

## Shared rules (paste these first, every time)

````
You are the editor of the customer newsletter of Grathaus, a fictional
mid-sized outdoor company in southern Germany. It has two brands:
- "Grathaus Outdoor": three stores (München, Augsburg, Rosenheim) and an online
  shop selling outdoor gear, plus trail guides, offers and store events.
- "Grathaus Touren": the same company's guided tours and courses.

Write content records as CSV, in GERMAN unless told otherwise.

FORMAT — exactly these columns, in this order, with a header row:

brand,language,title,description,headline_hero,button_label_hero,headline_medium,body_medium,body_long,button_label,button_url,image,image_alt,push_title,push_body,categories

Rules per column:
- brand            — "outdoor" or "touren", as the batch says.
- language         — "de" (the English batch says "en").
- title            — the record's internal name, max 120 characters. Usually the headline.
- description      — one sentence, max 300 characters: what the piece covers.
- headline_hero    — a SHORT headline for the large top block, max 40 characters.
- button_label_hero — 2–3 words for the large block's button.
- headline_medium  — the headline in a normal block, max 70 characters.
- body_medium      — 50–90 words. The short text. See QUALITY.
- body_long        — 160–260 words. The long text of the same piece, for a full
                     article block. Paragraphs separated by a blank line. You may
                     mark a few words **bold**. No links in the text.
- button_label     — 2–4 words, action-oriented ("Zur Route", "Kurs buchen").
- button_url       — https://www.grathaus.example/<slug> for outdoor,
                     https://touren.grathaus.example/<slug> for touren.
                     <slug>: lowercase, hyphens, no umlauts (ae, oe, ue, ss).
- image            — ONE key from the IMAGE KEYS list below, the one that fits best.
                     Keys are shared: several records may use the same image.
- image_alt        — a short literal description of what that image shows,
                     in the record's language.
- push_title       — a push notification title, max 40 characters.
- push_body        — the push text, max 110 characters, one sentence.
- categories       — pipe-separated Name:Score pairs, e.g. Hüttentouren:9|Naturerlebnis:5
                     Score 1–10: how strongly the piece belongs to that category.
                     Exactly ONE primary category (8–10) and one to three secondary
                     ones (3–7). Prefer the most specific subcategory as primary.

CATEGORIES — use ONLY these names, spelled exactly like this:
Wandern, Tagestouren, Hüttentouren, Weitwandern, Klettersteige, Familienwandern,
Klettern, Halle & Bouldern, Alpinklettern,
Wintersport, Skitouren, Schneeschuh, Langlauf, Lawinenkunde,
Radfahren, Gravel & Trekking, Mountainbike,
Camping & Trekking, Biwak,
Familie & Kinder,
Naturerlebnis, Tierbeobachtung,
Sicherheit & Wissen, Erste Hilfe,
Nachhaltigkeit, Reparieren & Second Hand

IMAGE KEYS — use ONLY these:
wanderweg_herbst, huette_morgen, gipfelkreuz_nebel, weitwanderweg_wiese,
rucksack_packen, wanderschuhe_pfad, klettersteig_leiter, familie_bachlauf,
kletterhalle_griffe, boulderblock_matte, alpinwand_seil, karabiner_gurt,
skitour_aufstieg, schneeschuh_spur, langlauf_loipe, lawinensuche_lvs,
winterhuette_licht, gravel_feldweg, mtb_singletrail, radtaschen_bruecke,
zelt_see_abend, biwak_sterne, kocher_tasse, kinder_wald, picknick_alm,
hirsch_lichtung, murmeltier_fels, vogel_fernglas, erstehilfe_set,
karte_kompass, reparatur_werkbank, secondhand_regal, laden_innenraum,
vortrag_abend, testtag_parkplatz, fuehrung_gruppe, kurs_knoten,
huettenabend_tisch, gletscher_seilschaft, herbstlaub_bank

KINDS OF RECORD — mix them in every batch:
- Guide (about 40%): a route, a skill, a how-to. Real regions and places are
  welcome (Allgäu, Karwendel, Wetterstein, Fränkische Schweiz, Bayerischer Wald,
  Chiemgau, Berchtesgadener Land, Sächsische Schweiz, Schwarzwald), with
  distances, heights in metres, walking times, seasons, hut opening months.
- Gear (about 40%): a product or a product group, with a price in euros in the
  text. NO real manufacturer or product names: describe the item, or use the
  shop's own label "Grathaus Basis".
- Offer or event (about 20%): a sale, a repair day, a talk, a test day, in one of
  the three stores, with a date in the season and a time.

QUALITY — this is the whole point:
- Write like a real editor, not like marketing copy. Concrete beats enthusiastic.
- Every record has at least two specific, checkable-sounding details: a place, a
  height, a distance, a price, a time, a month, a local quirk.
- No filler openers ("Entdecke die Magie…", "Ob Anfänger oder Profi…").
- No exclamation marks. Address the reader as "Sie" (formal), sparingly.
- Vary sentence length. Dry or slightly opinionated is fine.
- Every record has a different angle. No near-duplicates within or across batches.
- No placeholders such as {{name}} or [Name].

OUTPUT — raw CSV only, no commentary before or after. Quote every field with
straight double quotes ("). Escape a double quote inside a field by doubling it.
````

## The batches (25 records each)

Paste the shared rules, then one of these.

````
BATCH 1 — brand "outdoor". 25 records with a primary category among:
Tagestouren, Hüttentouren, Weitwandern, Klettersteige, Familienwandern
(or Wandern itself for general hiking topics). Every one of those six is the
primary category of at least three records.
````

````
BATCH 2 — brand "outdoor". 25 records with a primary category among:
Halle & Bouldern, Alpinklettern, Klettersteige, Klettern,
Sicherheit & Wissen, Erste Hilfe. Every one of those is the primary category of
at least three records.
````

````
BATCH 3 — brand "outdoor". 25 records with a primary category among:
Skitouren, Schneeschuh, Langlauf, Lawinenkunde, Wintersport. Every one of those
is the primary category of at least four records. Season: December to March.
````

````
BATCH 4 — brand "outdoor". 25 records with a primary category among:
Gravel & Trekking, Mountainbike, Radfahren, Camping & Trekking, Biwak. Every one
of those is the primary category of at least four records.
````

````
BATCH 5 — brand "outdoor". 25 records with a primary category among:
Familie & Kinder, Familienwandern, Naturerlebnis, Tierbeobachtung,
Nachhaltigkeit, Reparieren & Second Hand. Every one of those is the primary
category of at least three records.
````

````
BATCH 6 — brand "touren". 25 records: the guided tours and courses of Grathaus
Touren (hut weekends, via ferrata introductions, climbing courses, ski-touring
and avalanche courses, snowshoe evenings, family nature days, wildlife walks).
Each record names the dates, the meeting point, the group size, the level and
the price per person. Primary categories spread across the whole list; at least
twelve different primary categories in the batch. The "Gear" kind does not
apply here: use "Guide" for tour descriptions and "Offer or event" for courses
with dates.
````

## The English batch

````
ENGLISH BATCH — below are eight records from the earlier batches. Translate each
into English, keeping every column. Set language to "en". Keep brand, button_url,
image and categories exactly as they are (do not translate category names or
image keys). Keep prices in euros and heights in metres. Same quality rules.

<paste the header row and eight rows here>
````

Pick a mix: four guides, two gear, two from Grathaus Touren.

## The editions batch

The demo has past newsletter editions with results. The seed picks each
edition's records by category; ChatGPT writes only the words around them.

````
EDITIONS — write CSV with exactly these columns, in this order, with a header row:

kind,key,brand,subject,preheader,editorial

- kind      — "edition" for a newsletter edition, "transactional" for a service mail.
- key       — the key given below, unchanged.
- brand     — "outdoor" or "touren", as given.
- subject   — max 60 characters, German, no exclamation marks.
- preheader — max 90 characters, adds information, never repeats the subject.
- editorial — 50–90 words, German, the short introduction at the top of the mail.
              You may use **bold**. No links.
              For editions, you may start with the placeholder
              {{salutation_formal}} followed by a comma, on its own line — it is
              replaced by a salutation per reader. No other placeholders.

Rows to write:
edition, herbstauftakt, outdoor          — early September: autumn hiking, huts still open
edition, huettensaison_finale, outdoor   — early October: last hut weekends, layering
edition, winterstart, outdoor            — late November: first snow, ski-touring gear, avalanche course dates
edition, skitouren_einstieg, outdoor     — January: getting into ski touring safely
edition, familienherbst, outdoor         — mid October: family days outside, school holidays
edition, reparaturwoche, outdoor         — late October: repair week in all three stores, second hand
edition, kursprogramm_winter, touren     — November: the winter course programme
transactional, bestellbestaetigung, outdoor — order confirmation: thank the customer, say what happens next (packing, shipping in 1–2 working days, returns within 30 days)
transactional, buchungsbestaetigung, touren — booking confirmation for a tour or course: what to bring, the meeting point is in the booking, cancellation free until 14 days before

Quote every field with straight double quotes. Raw CSV only.
````

## The images

Square (1:1), **600 × 600**, JPEG (about 60–120 KB each, the set about 4 MB).
Every block shows the square in a 50% column of the 600 px email: about 300 px
on a desktop screen, and full phone width (about 340–390 px) when the columns
stack. 600 px is sharp on 2× screens in both; 300 px would look soft on most.
Image tools usually give 1024 px; shrink the folder on a Mac with:
`sips -Z 600 -s format jpeg -s formatOptions 80 backend/scripts/demo/images/*.jpg`

Photographic, natural light, the southern German Alps and foothills. **No text, no logos, no brand marks, no recognisable
faces** (people from behind, at a distance or cropped). Save each as
`backend/scripts/demo/images/<key>.jpg`.

Prefix every prompt with: *"A square, photographic image, natural light, no text,
no logos, no recognisable faces: "*

| Key | Prompt |
|---|---|
| wanderweg_herbst | a narrow hiking trail through a larch forest in autumn, golden needles on the path, mountains in soft haze |
| huette_morgen | a stone-and-wood mountain hut at dawn, first sun on the roof, a bench and two empty mugs outside |
| gipfelkreuz_nebel | a wooden summit cross above a sea of fog, early morning |
| weitwanderweg_wiese | a long-distance trail through an alpine meadow, a single hiker far away with a large backpack |
| rucksack_packen | a hiking backpack being packed on a wooden floor, rain jacket, map, water bottle, first-aid pouch |
| wanderschuhe_pfad | close-up of worn leather hiking boots on a rocky path |
| klettersteig_leiter | a via ferrata ladder and steel cable on a limestone wall, a climber's hands and harness from behind |
| familie_bachlauf | a parent and two children from behind, crossing a shallow mountain stream on stones |
| kletterhalle_griffe | colourful holds on an indoor climbing wall, a chalk bag in the foreground |
| boulderblock_matte | a bouldering block outdoors in a forest, crash pads below, chalk marks on the rock |
| alpinwand_seil | a rope team on a big limestone wall, seen from far away |
| karabiner_gurt | climbing harness, carabiners and a belay device on a coiled rope |
| skitour_aufstieg | ski tourers' track zigzagging up a snowy slope, two people from behind at a distance |
| schneeschuh_spur | snowshoe tracks in fresh snow through a quiet spruce forest |
| langlauf_loipe | groomed cross-country ski tracks across a wide snowy valley in sunshine |
| lawinensuche_lvs | an avalanche transceiver, probe and shovel laid out on snow |
| winterhuette_licht | a snowed-in mountain hut at blue hour, warm light in the windows |
| gravel_feldweg | a gravel bike on a farm track between fields, foothills behind, late summer |
| mtb_singletrail | a mountain bike on a forest singletrail with roots, motion blur |
| radtaschen_bruecke | a touring bike with panniers leaning on a wooden bridge over a river |
| zelt_see_abend | a small tent by a mountain lake at sunset, reflections on the water |
| biwak_sterne | a bivouac bag on a ridge under a starry sky |
| kocher_tasse | a camping stove boiling water, a metal mug, steam in cold morning air |
| kinder_wald | children's small boots and a magnifying glass on moss in a forest, no faces |
| picknick_alm | a picnic blanket on an alpine pasture with bread, cheese and a thermos, cows far behind |
| hirsch_lichtung | a red deer stag in a forest clearing at dusk |
| murmeltier_fels | a marmot on a sunny rock in an alpine meadow |
| vogel_fernglas | binoculars on a wooden fence, a bird of prey circling far away |
| erstehilfe_set | an open first-aid kit on a rock, bandages, blister plasters, emergency blanket |
| karte_kompass | a paper hiking map and a compass on a tree stump |
| reparatur_werkbank | a workbench with an outdoor jacket being patched, thread, needles, a sewing machine |
| secondhand_regal | a shop shelf of used hiking boots and jackets with hand-written tags |
| laden_innenraum | the inside of a bright outdoor shop with wooden shelves, backpacks and jackets, no people |
| vortrag_abend | an evening talk in a shop, a projected mountain photo, rows of chairs seen from behind |
| testtag_parkplatz | a gear test day outside a shop, tents pitched, bikes on stands, people from behind |
| fuehrung_gruppe | a small guided hiking group from behind on a ridge path, the guide pointing ahead |
| kurs_knoten | hands tying a figure-eight knot on a climbing rope, close-up |
| huettenabend_tisch | a long wooden table inside a hut in the evening, candles, maps, mugs, no faces |
| gletscher_seilschaft | a rope team crossing a glacier, small figures, crevasses, blue ice |
| herbstlaub_bank | a wooden bench under a maple tree in autumn colours, mountains behind |

## Notes

- The importer matches categories **by name** against the categories the demo
  reset creates (the Grathaus tree, task-71). An unknown name is reported and
  skipped, never created: the vocabulary is governed (ADR-080).
- A score outside 1–10 skips that one assignment and is reported, never clamped.
- Brand keys, languages and image keys are checked the same way: an unknown
  value is reported, not guessed.
- The domain `grathaus.example` is reserved for examples; no link leads anywhere real.
