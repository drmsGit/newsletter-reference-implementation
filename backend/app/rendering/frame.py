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
from app.modules.registry import MODULES_DIR, get_manifest
from app.overrides.service import get_active_content_override
from app.rendering.renderers.base import ROLE_HTML, ROLE_PAYLOAD, RenderedArtifact

#: Bumped when the frame's shape changes, so a reader can tell what it holds.
FRAME_VERSION = 1

KIND_CONTENT = "content"   # cms module bound to a content record
KIND_STATIC = "static"     # cms: false module (module_data, maybe a content fill)
KIND_SLOT = "slot"         # bound to a decision slot: picked per recipient
KIND_EMPTY = "empty"       # cms module bound to nothing — hidden (ADR-086)
KIND_UNKNOWN = "unknown"   # no manifest for this type on this channel


def is_frame(render_context: dict | None) -> bool:
    """Whether a snapshot carries a frame. Snapshots made before ADR-183 do
    not, and are refused at send time rather than sent from live state."""
    return bool(render_context) and render_context.get("frame_version") == FRAME_VERSION


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


def _public(content: dict | None) -> dict:
    """Drop the private keys a resolved content dict carries (`_version_id`)."""
    return {k: v for k, v in (content or {}).items() if not k.startswith("_")}


def build_frame(db: Session, variant_id: int) -> dict:
    """Freeze a variant's composition, with its values, as of now (send mode).

    Send mode throughout: a content module freezes its latest *published*
    version, and unpublished content raises `UnpublishedContentError`, as a
    snapshot always has.
    """
    from app.rendering.service import (
        envelope_fields_for_variant, resolve_module_variables, static_module_variables,
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
                    variables=variables,
                    content_record_id=(content or {}).get("id"),
                    content_version_id=(content or {}).get("_version_id"),
                    override_id=override.id if override else None,
                )
        entries.append(entry)

    return {
        "frame_version": FRAME_VERSION,
        "variant_id": variant_id,
        "channel": channel,
        "envelope": envelope_fields_for_variant(db, variant_id, channel),
        "templates_fingerprint": templates_fingerprint(channel),
        "modules": entries,
    }


def _pick_for_slot(db: Session, entry: dict, channel: str, recipient_id: int | None) -> dict | None:
    """The slot's pick for this recipient now: their resolution, else the
    slot's global one — the order the live render has always used. Returns the
    pick with a copy of its values, or None when nothing resolved (ADR-086)."""
    from app.rendering.service import resolve_renderable_content

    query = db.query(DecisionResolutionDB).filter(
        DecisionResolutionDB.decision_slot_id == entry["decision_slot_id"]
    )
    resolution = None
    if recipient_id is not None:
        resolution = (
            query.filter(DecisionResolutionDB.recipient_id == recipient_id)
            .order_by(DecisionResolutionDB.created_at.desc()).first()
        )
    if resolution is None:
        resolution = (
            query.filter(DecisionResolutionDB.recipient_id.is_(None))
            .order_by(DecisionResolutionDB.created_at.desc()).first()
        )
    if resolution is None:
        return None
    content = resolve_renderable_content(
        db=db, content_record_id=resolution.content_record_id,
        content_version_id=resolution.content_version_id, mode="send",
    )
    if content is None:
        return None
    manifest = get_manifest(channel, entry["module_type"])
    # No override: a decision slot is never overridden (ADR-178 point 5).
    variables = {var.name: content.get(var.name, "") for var in manifest.variables}
    return {
        "module_id": entry["module_id"],
        "decision_resolution_id": resolution.id,
        "content_record_id": resolution.content_record_id,
        "content_version_id": content.get("_version_id"),
        "variables": variables,
    }


def render_frame(
    db: Session, frame: dict, recipient_id: int | None = None, picks: list[dict] | None = None,
) -> tuple[RenderedArtifact, list[dict]]:
    """Lay a frame out for one recipient. Returns `(artifact, picks)`.

    `picks=None` makes each slot's pick now (the send, or a preview); recorded
    `picks` are re-used as they are (reconstruction). The returned picks are
    what a delivery record stores.
    """
    from app.rendering.service import module_html, email_document, strip_rich_text

    channel = frame["channel"]
    recorded = {p["module_id"]: p for p in (picks or [])}
    made: list[dict] = []
    html_parts: list[str] = []
    fields: dict = {}

    for entry in frame["modules"]:
        kind = entry["kind"]
        variables, content_id = None, None
        if kind in (KIND_CONTENT, KIND_STATIC):
            variables, content_id = entry["variables"], entry.get("content_record_id")
            if kind == KIND_STATIC:
                content_id = None  # the static wrapper never carried one
        elif kind == KIND_SLOT:
            pick = recorded.get(entry["module_id"]) if picks is not None else _pick_for_slot(
                db, entry, channel, recipient_id,
            )
            if pick is not None:
                made.append(pick)
                variables, content_id = pick["variables"], pick["content_record_id"]

        if channel == "email":
            if kind == KIND_UNKNOWN:
                html_parts.append(module_html(channel, entry["module_type"], entry["module_id"], {}))
            elif variables is None:
                html_parts.append(
                    f"<!-- module {entry['module_id']} ({entry['module_type']}): "
                    "no content resolved, slot hidden -->"
                )
            else:
                html_parts.append(module_html(
                    channel, entry["module_type"], entry["module_id"], variables,
                    content_id=content_id,
                ))
        elif variables is not None and not fields:
            # A push carries one module's fields (ADR-160 point 2), stripped of
            # rich-text markup an operating system would show literally.
            fields = strip_rich_text(variables, get_manifest(channel, entry["module_type"]))

    if channel == "email":
        artifact = RenderedArtifact(
            role=ROLE_HTML, media_type="text/html", body=email_document(html_parts),
            envelope=dict(frame.get("envelope") or {}),
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
        manifest = get_manifest(frame["channel"], entry["module_type"])
        for var in manifest.variables:
            if var.required and not str(entry["variables"].get(var.name, "") or "").strip():
                missing.append((entry["module_id"], entry["module_type"], var.name))
    return missing


def slot_ids(frame: dict) -> list[int]:
    return [m["decision_slot_id"] for m in frame["modules"] if m["kind"] == KIND_SLOT]
