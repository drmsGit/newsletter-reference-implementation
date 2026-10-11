"""The snapshot frame: a composition frozen with its values, and rendering from it (ADR-183).

A send used to take only `variant_id` from its snapshot and re-render every
recipient from live database state, so an edit made after approval went out
unreviewed and nothing could say what a recipient actually got. A frame is the
composition at snapshot time, **with the values copied in** — not references to
rows that can change:

  - every module, in order, with its type;
  - for a content-bound or static module, the final field values (content
    version used, static `module_data`, applied override), plus the ids they
    came from, for tracing;
  - for a decision-slot module, only the slot: its pick is per recipient and
    is made at send time, which is what personalisation means;
  - the envelope (subject, preheader) — or, for push, the payload fields come
    from the modules like everything else;
  - a fingerprint of the templates and brand CSS the values were laid out with.

`render_frame` lays a frame out for one recipient. With `picks=None` it makes
the slot picks now and returns them, which is the send; given recorded `picks`
it re-uses them, which is reconstruction. Content is exact either way; layout
is today's templates, and the fingerprint says whether they still match.
"""
import hashlib
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.campaigns.db_models import DecisionResolutionDB, ModuleInstanceDB, VariantDB
from app.modules.registry import MODULES_DIR, get_manifest, required_when_shown
from app.overrides.service import get_active_content_override
from app.rendering.renderers.base import ROLE_HTML, ROLE_PAYLOAD, RenderedArtifact

#: Bumped when the frame's shape changes, so a reader can tell what it holds.
FRAME_VERSION = 3
#: Every version a reader understands. Version 2 (2026-10-10, task-349): the
#: email envelope module is `envelope`; in a version-1 email frame it is
#: `header`. Frozen frames are never rewritten — `module_html` writes the type
#: into the HTML, so a rewrite would change what a sent email reconstructs to
#: (ADR-183) — so readers translate instead, keyed on the version so a
#: version-1 `header` can never be confused with ADR-193's visible `header`.
#: Version 3 (2026-10-11, task-357): an email frame freezes its brand profile
#: (`brand_profile`, ADR-194) and renders the legal footer from it. Frames
#: below 3 keep the legacy unsubscribe line byte for byte, and are refused for
#: sending (`profile_refusal`): they carry no legal details.
FRAME_VERSIONS = (1, 2, 3)
#: The first version whose email frames carry a brand profile.
PROFILE_FRAME_VERSION = 3
LEGACY_EMAIL_ENVELOPE = "header"

KIND_CONTENT = "content"   # cms module bound to a content record
KIND_STATIC = "static"     # cms: false module (module_data, maybe a content fill)
KIND_SLOT = "slot"         # bound to a decision slot: picked per recipient
KIND_EMPTY = "empty"       # cms module bound to nothing — hidden (ADR-086)
KIND_UNKNOWN = "unknown"   # no manifest for this type on this channel


def is_frame(render_context: dict | None) -> bool:
    """Whether a snapshot carries a frame. Snapshots made before ADR-183 do
    not, and are refused at send time rather than sent from live state."""
    return bool(render_context) and render_context.get("frame_version") in FRAME_VERSIONS


def _frame_envelope(frame: dict) -> str | None:
    """The name this frame's envelope module was frozen under."""
    from app.modules.registry import envelope_module_type

    if frame.get("frame_version") == 1 and frame.get("channel") == "email":
        return LEGACY_EMAIL_ENVELOPE
    return envelope_module_type(frame["channel"])


def lookup_type(frame: dict, entry: dict) -> str:
    """Where an entry's manifest and template are found today. The same as
    the name it was frozen under, except a version-1 email frame's envelope."""
    from app.modules.registry import envelope_module_type

    if entry["module_type"] == LEGACY_EMAIL_ENVELOPE and _frame_envelope(frame) == LEGACY_EMAIL_ENVELOPE:
        return envelope_module_type(frame["channel"]) or entry["module_type"]
    return entry["module_type"]


def templates_fingerprint(channel: str) -> str:
    """A hash of every template, manifest and stylesheet for this channel.

    Templates are files and are not versioned (ADR-183 point 4: content exact,
    layout best-effort), so a reconstruction can only *say* whether the layout
    it used is the one the message was sent with. This is what it compares.
    """
    digest = hashlib.sha256()
    channel_dir = Path(MODULES_DIR) / channel
    for path in sorted(channel_dir.glob("*")):
        if path.is_file():
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def artifact_hash(artifact: RenderedArtifact) -> str:
    """A hash of what a recipient was sent: body or payload, and envelope."""
    payload = {
        "body": artifact.body,
        "fields": artifact.fields or {},
        "envelope": artifact.envelope or {},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def build_frame(db: Session, variant_id: int) -> dict:
    """Freeze a variant's composition, with its values, as of now (send mode).

    Send mode throughout: a content module freezes its latest *published*
    version, and unpublished content raises `UnpublishedContentError`, as a
    snapshot always has.
    """
    from app.rendering.service import (
        envelope_fields_for_variant, resolve_module_variables, static_module_variables, without_hidden,
    )

    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()
    if variant is None:
        raise ValueError(f"variant {variant_id} does not exist")
    channel = variant.channel

    entries = []
    modules = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position)
        .all()
    )
    for module in modules:
        entry = {
            "module_id": module.id,
            "module_type": module.module_type,
            "position": module.position,
        }
        manifest = get_manifest(channel, module.module_type)
        if manifest is not None:
            # What the manager hid (ADR-187): recorded, so the as-sent view
            # stays true if the toggle changes later, and the frozen values are
            # only the shown ones. A frame without the key hid nothing.
            entry["hidden_fields"] = list(module.hidden_fields or [])
        if manifest is None:
            entry["kind"] = KIND_UNKNOWN
        elif module.decision_slot_id is not None:
            entry.update(kind=KIND_SLOT, decision_slot_id=module.decision_slot_id)
        else:
            override = get_active_content_override(db, module.id)
            if manifest.cms:
                variables, content, _ = resolve_module_variables(
                    db=db, module=module, manifest=manifest, recipient_id=None, mode="send",
                )
            else:
                variables, content = static_module_variables(
                    db, module, manifest, mode="send", with_source=True,
                )
            if variables is None:
                entry["kind"] = KIND_EMPTY
            else:
                entry.update(
                    kind=KIND_CONTENT if manifest.cms else KIND_STATIC,
                    variables=without_hidden(variables, module.hidden_fields),
                    content_record_id=(content or {}).get("id"),
                    content_version_id=(content or {}).get("_version_id"),
                    override_id=override.id if override else None,
                )
        entries.append(entry)

    frame = {
        "frame_version": FRAME_VERSION,
        "variant_id": variant_id,
        "channel": channel,
        "envelope": envelope_fields_for_variant(db, variant_id, channel),
        "templates_fingerprint": templates_fingerprint(channel),
        "modules": entries,
    }
    if channel == "email":
        frame["brand_profile"] = _frozen_profile(db, variant)
        # The tags every module link carries, frozen with the names they come
        # from (task-354): a rename after the snapshot changes nothing sent.
        from app.brand_profiles.theme import link_params
        from app.campaigns.db_models import CampaignDB

        campaign_name = db.query(CampaignDB.name).filter(CampaignDB.id == variant.campaign_id).scalar()
        frame["link_params"] = link_params(frame["brand_profile"]["values"], campaign_name, variant.name)
    return frame


def _frame_theme(frame: dict) -> dict:
    """The look and tags a frame was frozen with; empty for frames made
    before them, which then render as they were sent."""
    return {
        "values": (frame.get("brand_profile") or {}).get("values") or {},
        "link_params": frame.get("link_params") or [],
    }


def _frozen_profile(db: Session, variant: VariantDB) -> dict:
    """The variant's brand profile as it is now, or the brand's default when
    it names none (ADR-194 points 4 and 7). Every value is frozen, so a later
    edit to the profile reaches no email made from this frame."""
    from app.brand_profiles.service import profile_of_variant
    from app.campaigns.db_models import CampaignDB

    brand_id = db.query(CampaignDB.brand_id).filter(CampaignDB.id == variant.campaign_id).scalar()
    profile = profile_of_variant(db, variant, brand_id)
    return {
        "id": profile.id, "name": profile.name, "language": profile.language,
        "kind": profile.kind, "values": dict(profile.field_values or {}),
    }


def _picks_for_slot(db: Session, entry: dict, channel: str, recipient_id: int | None) -> list[dict]:
    """The slot's picks for this recipient now, first pick first: their set,
    else the slot's global one — the order the live render has always used
    (`app.decision.sets`). Each pick carries a copy of its values and its
    rank. Empty when nothing resolved (ADR-086). A pick whose content cannot
    be rendered now is left out, and the ones after it move up."""
    from app.decision.sets import latest_pick_set
    from app.rendering.service import resolve_renderable_content

    manifest = get_manifest(channel, entry["module_type"])
    # No override: a decision slot is never overridden (ADR-178 point 5). A
    # field the module hides is left out of the pick, as of every render.
    hidden = set(entry.get("hidden_fields") or ())
    picks: list[dict] = []
    for resolution in latest_pick_set(db, entry["decision_slot_id"], recipient_id):
        content = resolve_renderable_content(
            db=db, content_record_id=resolution.content_record_id,
            content_version_id=resolution.content_version_id, mode="send",
        )
        if content is None:
            continue
        picks.append({
            "module_id": entry["module_id"],
            "rank": len(picks) + 1,
            "decision_resolution_id": resolution.id,
            "content_record_id": resolution.content_record_id,
            "content_version_id": content.get("_version_id"),
            "variables": {var.name: content.get(var.name, "") for var in manifest.variables
                          if var.name not in hidden},
        })
    return picks


def what_rendered(frame: dict, picks: list[dict]) -> tuple[bool, int]:
    """For one recipient's render: whether anything meaningful came out, and
    how many slots the frame has (task-228; ADR-086 addendum 2026-10-08).

    Meaningful is any module but the envelope that produced output: typed-in
    content, a catalogue record, or a slot that found something for this
    person (`picks` holds only those). An empty slot, an unbound module and an
    unknown one do not count, and neither does the envelope module (for
    email the subject and preheader; push has none), nor a module whose
    manifest says `decorative`: the visible header and footer (task-351).
    """
    envelope = _frame_envelope(frame)
    picked = {p["module_id"] for p in picks}
    slots = sum(1 for entry in frame["modules"] if entry["kind"] == KIND_SLOT)

    def decorative(entry: dict) -> bool:
        # The visible header and footer (task-351): never content. Looked up
        # by today's name, so a version-1 `header` is the envelope, not this.
        manifest = get_manifest(frame["channel"], lookup_type(frame, entry))
        return bool(manifest and manifest.decorative)

    meaningful = any(
        entry["module_type"] != envelope
        and not decorative(entry)
        and (entry["kind"] in (KIND_CONTENT, KIND_STATIC)
             or (entry["kind"] == KIND_SLOT and entry["module_id"] in picked))
        for entry in frame["modules"]
    )
    return meaningful, slots


def render_frame(
    db: Session, frame: dict, recipient_id: int | None = None, picks: list[dict] | None = None,
    *, empty_slots: frozenset[int] = frozenset(), unsubscribe: dict | None = None,
) -> tuple[RenderedArtifact, list[dict]]:
    """Lay a frame out for one recipient. Returns `(artifact, picks)`.

    `picks=None` makes each slot's pick now (the send, or a preview); recorded
    `picks` are re-used as they are (reconstruction). The returned picks are
    what a delivery record stores.

    `empty_slots` names slots whose decision found nothing in this run: they
    render empty instead of falling back to an older stored pick that the
    decision has just refused (task-320). A preview, which runs no decision,
    passes none and shows the last stored pick, as it always has.

    `unsubscribe` — `{"url", "brand"}` from `subscriptions.footer_for`, or as
    recorded in a delivery record — adds the footer line and puts the URL in the
    envelope, where the provider turns it into the List-Unsubscribe headers
    (ADR-191 point 5; the envelope is the artifact's delivery metadata, ADR-161
    point 1). Email only; a preview passes none.
    """
    from app.rendering.service import module_html, email_document, strip_rich_text

    channel = frame["channel"]
    theme = _frame_theme(frame)
    # Recorded picks by module, in their order: a slot shows up to five, and
    # a pick recorded before ranks existed is a set of one (task-109).
    recorded: dict[int, list[dict]] = {}
    for pick in picks or []:
        recorded.setdefault(pick["module_id"], []).append(pick)
    made: list[dict] = []
    html_parts: list[str] = []
    fields: dict = {}

    for entry in frame["modules"]:
        kind = entry["kind"]
        # (variables, content id) per copy of the module: one for a content
        # or static module, one per pick for a slot (ADR-084 addendum
        # 2026-10-11 — several picks repeat the module, first pick first).
        copies: list[tuple[dict, int | None]] = []
        if kind in (KIND_CONTENT, KIND_STATIC):
            # The static wrapper never carried a content id.
            copies = [(entry["variables"], None if kind == KIND_STATIC else entry.get("content_record_id"))]
        elif kind == KIND_SLOT:
            if picks is not None:
                slot_picks = recorded.get(entry["module_id"], [])
            elif entry["decision_slot_id"] in empty_slots:
                slot_picks = []
            else:
                slot_picks = _picks_for_slot(db, entry, channel, recipient_id)
            made.extend(slot_picks)
            copies = [(pick["variables"], pick["content_record_id"]) for pick in slot_picks]
        if entry.get("hidden_fields"):
            # Already left out when frozen or picked; a recorded pick from
            # before the list existed is held to it here too.
            copies = [({k: v for k, v in variables.items() if k not in set(entry["hidden_fields"])}, content_id)
                      for variables, content_id in copies]

        if channel == "email":
            if kind == KIND_UNKNOWN:
                html_parts.append(module_html(channel, entry["module_type"], entry["module_id"], {}, theme=theme))
            elif not copies:
                html_parts.append(
                    f"<!-- module {entry['module_id']} ({entry['module_type']}): "
                    "no content resolved, slot hidden -->"
                )
            else:
                for variables, content_id in copies:
                    html_parts.append(module_html(
                        channel, entry["module_type"], entry["module_id"], variables,
                        content_id=content_id, template_type=lookup_type(frame, entry), theme=theme,
                    ))
        elif copies and not fields:
            # A push carries one module's fields (ADR-160 point 2), stripped of
            # rich-text markup an operating system would show literally. A
            # push slot shows one pick; should more ever be recorded, the
            # first is the one.
            fields = strip_rich_text(copies[0][0], get_manifest(channel, entry["module_type"]))

    if channel == "email":
        from app.rendering.service import legal_footer_html
        from app.subscriptions.texts import footer_html

        envelope = dict(frame.get("envelope") or {})
        footer = ""
        if frame.get("frame_version", 0) >= PROFILE_FRAME_VERSION and frame.get("brand_profile"):
            # Every email from version 3 on: the profile's legal details, and
            # for a marketing message the unsubscribe wording as its link.
            footer = legal_footer_html(
                frame["brand_profile"], unsubscribe["url"] if unsubscribe else None,
            )
        elif unsubscribe:
            # Older frames: the line they were sent with, unchanged (ADR-183).
            footer = footer_html(unsubscribe["brand"], unsubscribe["url"])
        if unsubscribe:
            envelope["list_unsubscribe"] = unsubscribe["url"]
        artifact = RenderedArtifact(
            role=ROLE_HTML, media_type="text/html", body=email_document(html_parts, footer, theme=theme),
            envelope=envelope,
        )
    else:
        artifact = RenderedArtifact(
            role=ROLE_PAYLOAD, media_type="application/json", fields=fields,
            envelope=dict(frame.get("envelope") or {}),
        )
    return artifact, made


def missing_required_in_frame(frame: dict) -> list[tuple[int, str, str]]:
    """Required fields the frame would send empty — the frame twin of
    `rendering.service.missing_required_fields` (ADR-174 point 3).

    Asked of the frame because the frame is what is sent: checking the live
    variant would pass a send whose frozen copy is empty, or refuse one whose
    frozen copy is fine. Slot modules are per recipient and are not checked
    here, for the reason the live check gives.
    """
    missing = []
    for entry in frame["modules"]:
        if entry["kind"] not in (KIND_CONTENT, KIND_STATIC):
            continue
        manifest = get_manifest(frame["channel"], lookup_type(frame, entry))
        # Required when shown (ADR-187 point 6), from the list the frame froze.
        for name in required_when_shown(manifest, entry.get("hidden_fields")):
            if not str(entry["variables"].get(name, "") or "").strip():
                missing.append((entry["module_id"], entry["module_type"], name))
    return missing


def profile_refusal(frame: dict) -> str | None:
    """Why this frame may not be sent for its brand profile, or None
    (ADR-194, addendum 2026-10-11 points 2, 5 and 6).

    Every email carries the sender's legal details, so an email frame needs a
    frozen profile with every required field. Asked of the frame, not the live
    profile: the frame is what is sent, so filling the profile afterwards needs
    a new snapshot, and the sentence says so. Push carries no footer.
    """
    from app.brand_profiles.structure import missing_fields, profile_structure

    if frame.get("channel") != "email":
        return None
    profile = frame.get("brand_profile")
    if frame.get("frame_version", 0) < PROFILE_FRAME_VERSION or not profile:
        return (
            "This send's snapshot was made before brand profiles, so it carries no legal "
            "details and cannot be sent. Take a new snapshot."
        )
    missing = missing_fields(profile.get("kind") or "marketing", profile.get("values") or {})
    if not missing:
        return None
    labels = {f.name: f.label for f in profile_structure()}
    named = ", ".join(labels.get(name, name) for name in missing)
    return (
        f'The brand profile "{profile.get("name")}" is missing: {named}. Every email carries '
        "the sender's legal details, so this send is refused. Fill them in under Settings, "
        "Brand profiles, then take a new snapshot."
    )


def slot_ids(frame: dict) -> list[int]:
    return [m["decision_slot_id"] for m in frame["modules"] if m["kind"] == KIND_SLOT]


def hand_bound_ids(frame: dict) -> set[int]:
    """The content records placed by hand in the frame's modules."""
    return {m["content_record_id"] for m in frame["modules"]
            if m["kind"] == KIND_CONTENT and m.get("content_record_id") is not None}


def send_purpose(frame: dict | None) -> str:
    """The purpose a send of this frame records and is gated on (ADR-195):
    transactional when its frozen brand profile is, marketing otherwise. Read
    from the frame, not the live profile, because the frame is what is sent:
    a profile re-marked after the snapshot changes nothing already planned."""
    from app.recipients.consent import MARKETING, TRANSACTIONAL

    frame = frame or {}
    profile = frame.get("brand_profile") or {}
    if (frame.get("channel") == "email" and frame.get("frame_version", 0) >= PROFILE_FRAME_VERSION
            and profile.get("kind") == TRANSACTIONAL):
        return TRANSACTIONAL
    return MARKETING
