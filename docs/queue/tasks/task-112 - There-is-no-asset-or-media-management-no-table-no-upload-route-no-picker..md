---
id: TASK-112
title: 'There is no asset or media management: no table, no upload route, no picker.'
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 206500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — CONFIRMED NEEDED by the user 2026-09-27; scope is the only open part. An entire subsystem that does not exist.** **There is no asset or media management: no table, no upload route, no picker.** `image_url` is a plain string typed into a form field (`backend/app/frontend/router.py:2218`), and a grep for `UploadFile`, an asset model or any media handling across `backend/app/` returns nothing. Surfaced during [[Variant Editor - design interview]] question 2.10, where the user reasoned it out from the field model: *"image 'long' or 'wide' is a url in the end so 120 might be too short (or it's just referring to a folder) it also will need an upload/select function, so maybe it just fills an ID"*.

  **The typed string is an inherited workaround, not a design, and this must be recorded before anyone defends it.** The user, 2026-09-27: *"Image_url is a typed string in the client's project because of guards in Salesforce permissions. In our platform a manager must be able to upload and/or select an image."* So the current shape came across from CampaignStudio, which the interview already established is **not a blueprint** — it is one of the workarounds, and it was carried in by resemblance rather than by decision.

  **An image is not a long text field; it is a different `type`.** That is why the module-variable descriptor settled in interview question 2.10 grew `type` (`text` · `url` · `asset`) rather than stretching `size`. **Storing an ID rather than a URL is what makes the rest possible**: reuse across content records, a picker instead of copy-pasted links, alt text that travels with the asset rather than being retyped per record, and any hope of knowing what references an asset before deleting it.

  **The storage shape already exists in this repository, and this is its second consumer.** `SnapshotDB` carries `artifact_storage_type` (`"file"` / `"inline"`), `artifact_location` and `artifact_size`, and `backend/app/snapshots/service.py:106` already names *"the open snapshot-storage question"* as unresolved. **Answer both together.** Designing asset storage on its own would produce a second abstraction for the same problem, and [[ADR-101 — Provider Capabilities Are Explicit]] is the pattern for the seam — local disk today, object storage or an adopter's existing DAM behind the same declaration.

  **Design settled 2026-09-27** — five questions asked directly rather than as an interview, because the user challenged the proposed five-cluster document as over-scoped for *"just a few images"* and was right. The shape is **asset records**: content stores an id, not a path.

  **1. Alt text lives on the asset, overridable at the usage.** Written once at upload, so it is far more likely to exist at all — the realistic failure is *absent* alt text, not wrong alt text, and per-usage means filling it every time. The override exists because accessibility guidance is right that alt text should convey purpose *in context*. Cost accepted: `image_alt` stays in the manifests rather than disappearing, and is usually empty and inheriting.

  **2. Replacing an image is done in place — same asset, new file — with no reach warning.** The user: *"a change is a change because 'we can't send it as is', if it's a similar but different image managers will upload it as new image anyway."* **This is deliberately unlike the content-record rule.** A text edit is *ambiguous* — typo or campaign-specific? — which is why interview question 3.7 requires a reach count. An image replacement is not ambiguous: nobody replaces an image in order to make it different in one place. So the propagation is the intent and needs no confirmation.

  **3. Assets are served from an unguessable path with no authentication.** This is **the only thing in the platform that must serve anonymously** — a mail client fetches an image days later with no session, no cookie. Signed or expiring URLs are out: an email sits in an inbox for months and the image must still resolve. Guessable paths are out because `/assets/1..9999` would walk every brand's library, including images from campaigns never sent. An unguessable component protects everything *except* the image that was mailed, which was public the moment it was sent. The record stores the served path rather than deriving it from the id — the shape `artifact_location` already uses.

  **4. Deletion means hiding from the picker. The file is served forever.** Hard deletion would **retroactively break every email ever sent** using that asset, since those are in inboxes and fetch on open. **The user generalised this into a principle**: *"similar as no deletion on content records or categories for example as those are woven into the affinity profiles (deleting would mean we can't interpret it)"* — see the standalone entry below. Consequence: **no usage query is needed for assets at all.** Question 2 removed the reach warning and this removes the deletion check, so the interview-3.7 query stays a content-record concern.

  **5. Search only, made viable by generated filenames.** The picker gets a search box and nothing else — no folders, no tags — *"time will tell if something else will be needed"*. **What makes search-only workable is that names are generated rather than typed.** The user proposes a company-configurable template applied at upload, for example `yyyymmdd-#-pxWidth-pxHeight-name.filetype`, or with a product id inserted. Upload date, pixel dimensions and an incrementing number are filled automatically; the dialog asks only for the free-text name (and product id where used). **The reasoning is the load-bearing part**: *"Companies will have some kind of structure for asset management, but maintaining it is the difficult part (especially if it comes to special characters) so we need some process in the back so 'search only' is actually possible."* A convention people must follow decays; a template the system applies does not.

  **Two consequences of (5) worth carrying into the build.** The **generated name and the served path are different things** — a fully predictable filename would hand back the enumeration that (3) just removed, so the name is searchable metadata and the path keeps its unguessable component, stored separately. And the template is configured **at implementation**, because *"or in the settings?"* lands on an open gap: there is no `app/settings/router.py` and the whole settings surface is UI-only (see the C2 item above).

  **Scale sets the seam rather than the design.** The user: an eCommerce shop uploading every product image reaches tens of thousands, *"but they might skip the asset library and connect a media center anyway"*. That is the [[ADR-101 — Provider Capabilities Are Explicit]] seam doing its job — the built-in library targets ordinary volumes and an adopter's DAM replaces it behind the same declaration. **It is an argument for the seam, not for building a DAM.**

  **The minimum that unblocks the composer** is upload, list, pick and serve, brand-scoped.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 374, section "Features", position 65 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
