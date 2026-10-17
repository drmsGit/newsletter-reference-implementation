---
type: adr
status: accepted
topic:
  - architecture
  - content
  - assets
  - rendering
  - brand
created: 2026-10-15
modified: 2026-10-17
source:
  - "task-112 design, five questions decided by the user 2026-09-27"
  - "task-112 scope and upload questions, decided by the user 2026-10-15, one question at a time"
  - "task-112 final-design pass, 2026-10-15 (technical shape, points 10–13)"
depends_on:
  - "[[ADR-101 — Provider Capabilities Are Explicit]]"
  - "[[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]"
  - "[[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]]"
  - "[[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]]"
  - "[[ADR-177 — A Field Is Defined Once, Required Per Module]]"
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-162 — Channel Rendering and Artifacts]]"
  - "[[ADR-154 — Erasure and Retention]]"
---

## Status
Accepted

## Context

**There is no asset or media management.** There is no asset table, no upload route and no picker (queue task-112).

- **An image is a typed string.** The content form takes `image_url` and `push_image_url` as plain form fields (`backend/app/frontend/router.py:2182` and `:2308`, verified 2026-10-15; task-112 cited `:2218` as of 2026-09-27).
- **`storage/fields.json` types them as `url`.** Its own header comment says so: "`type: url` on the image fields is honest about today: there is no asset subsystem, so an image is a URL somebody typed."
- **Three email modules render the string as it is.** `storage/modules/email/single_stack.html`, `img_left.html` and `img_right.html` write `<img src="{{ image_url }}" alt="{{ image_alt }}">`.
- **Brand profiles already have an `image` field type** (`FIELD_TYPES`, `backend/app/brand_profiles/structure.py:29`). The logo is one. Per [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] point 16 and its addendum of 2026-10-11 (fourth), point 3, it holds an https address until assets exist.

**The typed string is an inherited workaround, not a design.** The user, 2026-09-27: *"Image_url is a typed string in the client's project because of guards in Salesforce permissions. In our platform a manager must be able to upload and/or select an image."* [[ADR-177 — A Field Is Defined Once, Required Per Module]] Notes logged the gap the same way: storing an ID rather than a URL is the right shape, and the subsystem behind it does not exist.

**The design was settled in two sittings.**

- **2026-09-27: five questions, asked directly.** The user challenged a proposed five-cluster design document as over-scoped for *"just a few images"*, and was right. Points 1–5 below are those answers, as task-112 records them.
- **2026-10-15: four more, one question at a time.** These are points 6–9: scope, outside addresses, what may be uploaded, and the file-name template.
- **A final-design pass on 2026-10-15 then settled the technical shape.** These are points 10–13. They are attributed to that pass, not to the user.

**One note from 2026-09-27 no longer applies.** Task-112 asked for asset storage and snapshot storage to be answered together, so that one abstraction would serve both. [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] has since settled snapshot storage: the frame lives in the snapshot row, and no file is written (points 1 and 5). Assets are now the only stored files, so their storage is designed on its own.

**Options not taken.**

- *Signed or expiring image URLs.* An email sits in an inbox for months, and its images must still load.
- *Paths derived from the id or the name.* `/assets/1..9999` would walk every brand's library, including images from campaigns never sent.
- *A reach warning on replacement,* as content edits have. Point 2 gives the reason.
- *Hard deletion.* Point 4 gives the reason.
- *Folders and tags.* Search over generated names was judged enough: *"time will tell if something else will be needed"*.
- *SVG uploads.* Many mail clients do not show SVG, and an SVG can carry script (point 8).
- *Building a DAM.* A shop that uploads every product image reaches tens of thousands of images. The user: *"but they might skip the asset library and connect a media center anyway"*. That is an argument for the seam of point 10, not for a DAM.

## Decision

**The shape is asset records.** An image is a record in a library, and a field refers to the record, not to a path.

### Decided by the user, 2026-09-27

**1. Alt text lives on the asset, and a usage may override it.**

- **Alt text is written once, at upload.** That makes it far more likely to exist at all. The realistic failure is absent alt text, not wrong alt text. Filling it per usage means filling it every time.
- **A usage may override it,** because alt text should convey purpose in context.
- **Accepted cost:** `image_alt` stays in the manifests. It is usually empty, and then it inherits.

**2. Replacing an image is done in place, with no reach warning.**
Same asset, new file. The user: *"a change is a change because 'we can't send it as is', if it's a similar but different image managers will upload it as new image anyway."*

- **This is deliberately unlike a content-record edit.** A text edit is ambiguous (a typo, or campaign-specific?), which is why the variant-editor interview's question 3.7 asks for a reach count on it. Nobody replaces an image to make it different in one place.
- **So propagation is the intent,** and it needs no confirmation.

**3. Assets are served from an unguessable path, with no authentication.**

- **This is the only content the platform serves anonymously.** A mail client fetches an image days later, with no session and no cookie.
- **Not signed, not expiring.** The image must still load months later.
- **Not guessable.** An unguessable path protects everything except the image that was mailed. That image was public the moment it was sent.
- **The record stores its served path,** rather than deriving it from the id.

**4. Deleting an asset hides it from the picker. The file is served forever.**

- **Hard deletion would break every email already sent with that asset.** Those emails are in inboxes, and they fetch the image on open.
- **The user generalised this into a principle:** *"delete = hide from picker; similar as no deletion on content records or categories for example as those are woven into the affinity profiles (deleting would mean we can't interpret it)"*. The principle across tables is queue task-117's (needs-adr). This record applies it to assets only.
- **No usage query is needed for assets.** Point 2 removed the reach warning, and this point removes the deletion check.

**5. The picker is search only, made workable by generated file names.**

- **A search box and nothing else.** No folders, no tags.
- **Names are generated from a template at upload,** not typed. Upload date, pixel size and a running number are filled in automatically. The upload dialog asks only for the free-text name, and a product id where the template uses one.
- **The reasoning is the user's:** *"Companies will have some kind of structure for asset management, but maintaining it is the difficult part (especially if it comes to special characters) so we need some process in the back so 'search only' is actually possible."* A convention people must follow decays. A template the system applies does not.
- **The generated name and the served path are different things.** A predictable name must never become a predictable path (point 11).

### Decided by the user, 2026-10-15

**6. The picker serves content records and brand profiles. There is one library per brand.**

- **Content records:** their image fields.
- **Brand profiles:** their image fields, such as the logo ([[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]]).
- **Both pick from the same library,** the brand's own.

**7. An image field holds a library asset or an https address.**

- **Outside addresses stay allowed.** Some companies keep their images in a DAM or a CDN. This is the [[ADR-101 — Provider Capabilities Are Explicit]] seam: the built-in library is for ordinary volumes, and it is not a DAM.
- **Existing records with addresses keep working.**
- **Alt text inherits only from a library asset.** An outside address has no asset to inherit from, so its usage's alt field is used as it stands.

**8. What may be uploaded: JPEG, PNG, GIF and WebP, up to 5 MB.**

- **The type is recognised from the file's content,** not from its name.
- **No SVG.** Many mail clients do not show it, and it can carry script.

**9. The file-name template is a setup file per installation.**

- **It sits beside the other setup files,** like `storage/brand_profile.json`. Its exact file is decided at implementation.
- **It ships as `brand-yyyymmdd-#-WxH-name`:** the brand's permanent key, the upload date, a running number, the pixel width and height, and the typed name. A product id may be added to it. The brand key comes first so names stay unique across an installation once files leave the app (a backup, an export, a DAM); decided with the user on 2026-10-15, after the first draft of this record left it out.
- **A changed template affects new uploads only.** Existing names stay as they are.
- **It is not editable in Settings.** IT changes it in a deployment, as with the brand-profile setup file.

### Settled by the final-design pass, 2026-10-15

**10. Storage sits behind a declared seam.**

- **Today: a local-disk store, a folder per brand.** The location is set per installation (`ASSETS_DIR`, default `storage/assets/`, not tracked), and each brand's files sit in a folder named by its permanent key (`<ASSETS_DIR>/<brand key>/<token>`), so one brand's images can be backed up, moved or handed over on their own. Decided with the user on 2026-10-15; the first draft had divided files by token only. The brand key never changes (`rename_brand` in `backend/app/auth/service.py` keeps it, naming a per-brand asset path as the reason).
- **The interface is ready for object storage, or for an adopter's DAM,** behind the same declaration ([[ADR-101 — Provider Capabilities Are Explicit]]).
- **The pixel size is read from the file header.** No new image library is added.

**11. The served path is `/media/<token>`.**

- **The token is random, one per asset.** It is not derived from the id or the name, and it is stored on the asset record (point 3).
- **The generated name is searchable metadata only.** So a predictable name never becomes an enumerable path.
- **`/media/<token>` is served without a session,** by a router outside the API guard. The unsubscribe page is the precedent ([[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]], Notes).
- **Everything else about assets is behind the guard:** list, upload, replace, hide and alt text.
  - Reading needs `view`.
  - Writing needs `content.manage`. It is brand-scoped, because asset rows carry a brand ([[ADR-150 — Tenancy and Access Model]], addendum of 2026-09-15).
- **A replaced file keeps its token.** So emails already sent show the new image. That is the intent of point 2. Mail clients and image proxies may still show a cached copy of the old one.

**12. A field refers to an asset as `asset:<id>`, and rendering resolves it.**

- **Content image fields get a new field type, `image`, in `storage/fields.json`.** It replaces `url` for `image_url` and `push_image_url`.
- **Content and brand-profile image fields both store either `asset:<id>` or an https address** (point 7).
- **Resolution happens where content and profiles enter rendering.** So the live preview, the frame and the per-recipient picks all hold a plain absolute URL, built on `PUBLIC_BASE_URL`.
- **The frame keeps that URL.** The as-sent reconstruction stays exact ([[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] point 4).
- **Alt text is inherited at the same point.** An empty alt field paired with an image field takes the asset's alt text there (point 1).

**13. A hidden asset keeps resolving and serving.**
Only the picker leaves it out (point 4).

## Consequences

### Positive

- **A manager uploads or picks an image.** No one copies addresses by hand any more, which is what task-112 and the merged task-91 asked for.
- **Alt text is written once,** so it is far more likely to exist.
- **Fixing an image fixes it everywhere,** including in emails already sent.
- **No email already sent loses an image,** through deletion or through hiding.
- **The library cannot be walked.** A served path tells nothing about any other asset, and nothing about the brand's unsent images.
- **Companies with a DAM or a CDN are not forced into the library.** An https address still works, and the storage seam leaves room for their system.
- **The search stays usable without upkeep.** The system writes the names, so nobody has to keep a naming convention.
- **Sent emails stay provable.** The frame holds the URL that went out, and the reconstruction and its hash check are unchanged.
- **No new dependency.** Pixel size and file type come from the file header, so the locked dependency set of [[ADR-189 — Python Dependencies Are Locked With Hashes]] does not grow.

### Negative

- **A replaced image may show late, or not at all, in mail already sent.** Mail clients and image proxies may keep the old copy.
- **Files are kept forever.** The disk only grows. This is point 4's principle at work. Retention has to answer it with archiving, not deletion (task-117).
- **Erasing a personal image has no answer yet.** A photo of a person, once mailed, is served forever. [[ADR-154 — Erasure and Retention]] decides erasure for a person's records. It does not cover an image in a brand's library. That needs its own answer.
- **A reconstruction proves which address went out, not which image was behind it.** A replacement changes the file at the same address (point 11). That is the intent of point 2, but it means the frame records the address, not the pixels.
- **Every sent image depends on `PUBLIC_BASE_URL` staying reachable.** The address is fixed into the mail. This is the same adopter obligation that [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] records for unsubscribe links (addendum of 2026-10-09, point 2).
- **The library is not a DAM.** It has no folders, tags or renditions, and no resizing. An image is served as it was uploaded.
- **The name template is not editable in Settings.** Changing it needs a deployment.
- **A public route with no authentication is new attack surface.** Its only protection is the token's randomness.

## Notes

- **The field type is `image`, not `asset`.** [[ADR-177 — A Field Is Defined Once, Required Per Module]] point 3 lists `asset` among the field types. `storage/fields.json`'s header comment says the image fields "become `asset` when one exists". Here the type is `image`. That matches the brand-profile type of the same name, and an `asset` type would misdescribe a field that may also hold an outside address (point 7). ADR-177's Decision is not edited.
- **This widens [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] point 16, and does not supersede it.** Point 16 says that when assets land, the logo field "holds an asset id". Under point 7 it holds an asset or an https address. ADR-194's Decision is not edited.
- **The token follows the unsubscribe token's pattern** ([[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] point 2): random, stored, never expiring, no secret to configure. Its length is an implementation detail. ADR-191 uses 256 random bits for the same kind of credential.
- **Two permissions may meet on a brand profile.** Picking an asset into a profile field is a profile write (`brand_profiles.manage`, ADR-194, first addendum, point 9). Uploading into the library needs `content.manage` (point 11). Someone holding only the first can pick, but not upload. This follows from the two records; it was not discussed.
- **Push carries the resolved address too.** Push renders a field dict, not HTML ([[ADR-162 — Channel Rendering and Artifacts]]). So `push_image_url` must be resolved before the push artifact is built, as point 12 says.
- **In development, `PUBLIC_BASE_URL` falls back to `http://localhost:8000`.** Images in test mail then point at the developer's own machine. A real marketing send already refuses an unset or non-https base URL (task-330).
- **Settled in the build (2026-10-15), stated to the user rather than asked:**
  - the running number counts per brand, per upload day;
  - a replacement keeps the token and the typed name, and regenerates the date and pixel-size parts of the generated name;
  - an image field names its alt field with an `alt` key (`image_url` with `image_alt` in `storage/fields.json`, `logo` with `logo_alt` in `storage/brand_profile.json`), recorded in the ADR-177 and ADR-194 addenda of 2026-10-15;
  - an asset of another brand is refused on save and resolves to no image;
  - a hidden asset cannot be shown in the picker again yet;
  - asset writes are audited ([[ADR-153 — Audit and Accountability]]).
- **No decision-log entry.** `docs/playbook-strategy.md` §5 has no entry for this decision. Its only related line is the ADR-193 entry's "The logo is a web address for now, and an uploaded asset once asset management exists". The reasoning above comes from task-112 and task-117.

## Addendum 2026-10-15 — another brand's image is used by copying it, and the picker is a pop-in

Prompted by the first picker built for task-112 (commit `0fd3332`), reviewed with the user on 2026-10-15. Points 1 and 2 were decided with the user; point 3 is a pointer only. Nothing above changes this record's Decision section.

**1. Another brand's image may be used, by copying it into the working brand's library.**

- **The picker lists the images of every brand the person holds a grant on.** It has a brand choice, set to the working brand by default. `GET /assets/?brand=` answers 404 for a brand without a grant, exactly as for an absent one ([[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]] point 6).
- **Using another brand's image copies it** (`POST /assets/{id}/copy`). The copy is a new record in the working brand. It gets a new generated name with the working brand's key (point 9) and its own file in the working brand's folder (point 10).
- **So each brand's emails depend only on its own folder.** That is what point 10's folder per brand exists for: one brand's images can be backed up, moved or handed over alone.
- **A later replacement of the original does not reach the copy.** Point 2's propagation stops at the brand boundary.
- **This is the rule of [[ADR-013 — Content Reference Instead of Content Copy]]'s addendum of 2026-09-16, applied to images:** reference within a brand, copy across the boundary ([[ADR-150 — Tenancy and Access Model]]). The copy's audit entry names the asset it came from. That is where ADR-013's addendum puts a copy's provenance.
- **This amends the Notes build note "an asset of another brand is refused on save and resolves to no image".** That still holds for a stored reference. The way to use another brand's image is the copy.

**2. The picker is a pop-in, not part of the form.**
The user, on the first version: it was not structured, and a bare file input under the image meant "replace" without saying so. *"We need to keep a proper list view system with the brands in mind."*

- **In the form:** the image, its name and alt text, "Change image…" and "Remove".
- **The pop-in has three tabs:** Library, Upload new and Web address (point 7).
- **Library is a thumbnail grid, newest first,** with point 1's brand choice, an optional search and "Load more". A detail panel lets the person check an image before using it. Alt text, replace and hide sit behind "More".
- **Browsing comes first, and search is optional.** The user doubts managers remember names. This loosens point 5's "search only": the generated names still make search workable, but search is no longer the only way in. There are still no folders and no tags.

**3. Not built: keeping content records in step across brands.** The user noted it as a future how-to chapter. It is for companies that reuse one record in many brands and want the copies kept in step, in all fields or some. It is task-379. Nothing here decides it.

## Addendum 2026-10-15 — a library image always uses its own alt text

Decided with the user on 2026-10-15. This narrows point 1 and the last bullet of point 12. The Decision section is not edited.

**1. A library image's alt text lives on the library image only.**

- **A usage cannot override it.** A field that holds a library image always uses that image's own alt text.
- **This drops point 1's "a usage may override it" for library images,** and with it point 1's accepted cost: `image_alt` no longer stays in the manifests "usually empty" in order to inherit.
- **Point 12's last bullet no longer applies to library images.** Alt text is not inherited "when the paired field is empty". The library image's alt text is used whatever the paired field holds.
- **Alt text is changed in the library,** behind "More" (previous addendum, point 2).

**2. An image given as a web address keeps its alt text.**

- **The Web address tab asks for it** (previous addendum, point 2).
- **It is stored in the paired alt field** (`image_alt`, `logo_alt`). Point 7's "used as it stands" holds.
- **The paired alt field no longer shows as a field of its own in forms.** It is filled in the pop-in, together with the address.

**Consequences.**

- **One place holds a library image's alt text.** Correcting it there corrects it for every later render.
- **The reason for point 1's override is given up.** Alt text should convey purpose in context. The same library image now carries one description in every email.
- **A library image without alt text renders without it.** No usage can make up for it.
- **Alt values stored on usages that point to a library image are no longer used.** Whether they are cleared or kept is for the build. The header comment of `storage/fields.json` ("which inherits the library image's alt when left empty") is then out of date.
- **The `alt` key that pairs an image field with its alt field stands** (the ADR-177 and ADR-194 addenda of 2026-10-15). So does [[ADR-187 — A Manager Hides Fields Per Module, and Required Means Required When Shown]] point 8: `image_alt` follows the image and is not hideable.

## Addendum 2026-10-17 — A full demo reset deletes images

Decided by the user on 2026-10-17 in task-71 (realistic demo content and a demo reset command). This is the one exception to point 4 and point 13. Nothing above changes this record's Decision section.

**1. The demo reset deletes the whole image library.**

- **It empties all demo data:** content, campaigns, sends, recipients, results and the image library. Every asset row goes, and its file with it.
- **It keeps** user accounts, roles, grants, Settings, integrations and the audit log.
- **Point 4's reason does not hold at a reset.** Point 4 keeps a file because an email already sent may still fetch it. The reset deletes every email that could show one too: its sends, snapshots and deliveries.
- **This is the reasoning of [[ADR-198 — The Email Block Set Is Seven Blocks, Square Images and Text Links]] point 5** (task-381): a retired module's files are deleted only at a full reset, when nothing that used them remains.

**2. Only an explicit command deletes an asset.**

- **The reset runs as `backend/scripts/demo_reset.py --yes`,** and it refuses the test database. It is built in task-71.
- **Nothing in the product or the API deletes an asset.** There, point 4 holds unchanged: deleting hides from the picker.

**Consequences.**

- **A rehearsal starts from a known library.** Every reset leaves the same images.
- **No orphaned files.** No file outlives its asset row.
- **An email sent from a development database before a reset can no longer show its images.** That is acceptable only because the reset is for demo and development databases, never a real installation's.

## Related ADRs

### Depends On
- [[ADR-101 — Provider Capabilities Are Explicit]] — the seam: local disk today, object storage or a DAM behind the same declaration (points 7 and 10).
- [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] — the frame holds the resolved URL, and snapshot storage is settled without a file.
- [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] — the precedent for a public route outside the guard, and for a stored random token.
- [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] — brand-profile image fields; point 16 is widened by point 7.
- [[ADR-177 — A Field Is Defined Once, Required Per Module]] — `storage/fields.json` and its field types; the `image` type joins them.
- [[ADR-150 — Tenancy and Access Model]] — one library per brand, and `content.manage` is brand-scoped.
- [[ADR-162 — Channel Rendering and Artifacts]] — push renders a field dict, so it carries the resolved address.
- [[ADR-154 — Erasure and Retention]] — erasure of a person's records; it does not yet reach images in a brand's library.
