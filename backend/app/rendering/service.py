import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

import css_inline
from jinja2 import BaseLoader, Environment
from markupsafe import Markup, escape
from sqlalchemy.orm import Session

from app.campaigns.db_models import ModuleInstanceDB, DecisionResolutionDB, VariantDB
from app.content.db_models import ContentRecordDB, ContentVersionDB
from app.email_modules.registry import ModuleManifest, get_manifest, get_template_html
from app.overrides.db_models import ContentOverrideDB
from app.overrides.service import get_active_content_override

RenderMode = Literal["preview", "send"]


class UnpublishedContentError(Exception):
    """Raised in send mode when a content record has no frozen version yet."""

    def __init__(self, content_record_id: int):
        self.content_record_id = content_record_id
        super().__init__(
            f"Content record {content_record_id} contains unpublished content — "
            "freeze a version before sending."
        )


_jinja = Environment(loader=BaseLoader(), autoescape=True)
_inliner = css_inline.CSSInliner()

_BRAND_CSS_PATH = (
    Path(__file__).parent.parent.parent.parent / "storage" / "email_modules" / "brand.css"
)

_RICH_TEXT_FIELD = "body_medium"
_RICH_TEXT_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_RICH_TEXT_BOLD = re.compile(r"\*\*(.+?)\*\*")


@lru_cache(maxsize=1)
def _load_brand_css() -> str:
    if _BRAND_CSS_PATH.exists():
        return _BRAND_CSS_PATH.read_text()
    return ""


def render_rich_text(text: str) -> Markup:
    """
    Minimal, safe markdown-like syntax for CMS body fields: **bold** and
    [label](url) links, plus newlines. Everything else is HTML-escaped first,
    so raw HTML can never be injected through content — the controlled
    alternative to the raw-HTML-in-content-fields risk autoescaping closed.
    """
    body = str(escape(text))
    body = _RICH_TEXT_LINK.sub(r'<a href="\2">\1</a>', body)
    body = _RICH_TEXT_BOLD.sub(r"<strong>\1</strong>", body)
    body = body.replace("\n", "<br>")
    return Markup(body)


def render_variant_html(
    db: Session,
    variant_id: int,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
    collect_resolutions: bool = False,
) -> str | tuple[str, dict[int, DecisionResolutionDB]]:
    modules = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position)
        .all()
    )

    rendered_modules = []
    resolutions_by_module_id: dict[int, DecisionResolutionDB] = {}

    for module in modules:
        html, resolution = render_module(db=db, module=module, recipient_id=recipient_id, mode=mode)
        rendered_modules.append(html)
        if resolution is not None:
            resolutions_by_module_id[module.id] = resolution

    brand_css = _load_brand_css()

    # Preheader: the inbox preview text shown after the subject line. It lives
    # on the variant and is emitted as a hidden span at the very top of the
    # body (the standard email technique) so clients pick it up without it
    # showing in the rendered email. Escaped — it's recipient-facing copy.
    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()
    preheader_html = ""
    if variant is not None and variant.preheader:
        preheader_html = (
            '<span class="preheader" '
            'style="display:none!important;visibility:hidden;opacity:0;'
            'color:transparent;height:0;width:0;overflow:hidden;">'
            f"{escape(variant.preheader)}</span>"
        )

    raw_html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Newsletter Preview</title>
    <style>{brand_css}</style>
  </head>
  <body>
    {preheader_html}
    {"".join(rendered_modules)}
  </body>
</html>"""

    final_html = _inliner.inline(raw_html)

    if collect_resolutions:
        return final_html, resolutions_by_module_id
    return final_html


def render_module(
    db: Session,
    module: ModuleInstanceDB,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
) -> tuple[str, DecisionResolutionDB | None]:
    manifest = get_manifest(module.module_type)

    if manifest is None:
        return render_unknown_module(module), None

    if manifest.cms:
        return render_cms_module(db=db, module=module, manifest=manifest, recipient_id=recipient_id, mode=mode)

    return render_static_module(db=db, module=module, manifest=manifest, mode=mode), None


def render_cms_module(
    db: Session,
    module: ModuleInstanceDB,
    manifest: ModuleManifest,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
) -> tuple[str, DecisionResolutionDB | None]:
    # An active content override (ADR-040/041) takes precedence over what the
    # system would resolve — a record pin swaps which content record fills the
    # module, and/or field overrides replace individual fields — until reset.
    override = get_active_content_override(db, module.id)

    content, decision_resolution = resolve_content_for_module(
        db=db, module=module, recipient_id=recipient_id, mode=mode, override=override
    )

    if content is None:
        # ADR-086: no content resolved — hide the slot rather than show a placeholder
        return (
            f"<!-- module {module.id} ({module.module_type}): no content resolved, slot hidden -->",
            decision_resolution,
        )

    field_overrides = (override.field_overrides if override else None) or {}
    variables: dict = {}

    for var in manifest.variables:
        # Convention: template variable name = CMS field name exactly. A
        # field-level override wins over the resolved content value (ADR-041).
        if var.name in field_overrides:
            variables[var.name] = field_overrides[var.name]
        else:
            variables[var.name] = content.get(var.name, "")

    if variables.get(_RICH_TEXT_FIELD):
        variables[_RICH_TEXT_FIELD] = render_rich_text(variables[_RICH_TEXT_FIELD])

    html_source = get_template_html(module.module_type)
    if html_source is None:
        return render_unknown_module(module), decision_resolution

    rendered = _jinja.from_string(html_source).render(**variables)

    html = (
        f'<div data-module-id="{module.id}" data-module-type="{module.module_type}"'
        f' data-content-id="{content["id"]}">\n'
        f"{rendered}\n"
        f"</div>"
    )
    return html, decision_resolution


def render_static_module(
    db: Session,
    module: ModuleInstanceDB,
    manifest: ModuleManifest,
    mode: RenderMode = "preview",
) -> str:
    html_source = get_template_html(module.module_type)
    if html_source is None:
        return render_unknown_module(module)

    variables = dict(module.module_data or {})

    # If module_data is sparse, fill missing required variables from the
    # linked content record so static modules render something useful.
    if module.content_record_id is not None:
        content = resolve_renderable_content(db=db, content_record_id=module.content_record_id, mode=mode)
        if content:
            for var in manifest.variables:
                if var.name not in variables or not variables[var.name]:
                    variables[var.name] = content.get(var.name, "")

    rendered = _jinja.from_string(html_source).render(**variables)

    return (
        f'<div data-module-id="{module.id}" data-module-type="{module.module_type}">\n'
        f"{rendered}\n"
        f"</div>"
    )


def render_unknown_module(module: ModuleInstanceDB) -> str:
    return (
        f'<div data-module-id="{module.id}" data-module-type="{module.module_type}">'
        f"<!-- unknown module type: {module.module_type} -->"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Content resolution
# ---------------------------------------------------------------------------

def resolve_renderable_content(
    db: Session,
    content_record_id: int,
    content_version_id: int | None = None,
    mode: RenderMode = "preview",
) -> dict | None:
    """
    Returns the raw content fields as a flat dict keyed by their CMS field names.
    Template variables must match these names exactly — no mapping layer.

    Preview mode: a pinned version is used if given, otherwise falls back to the
    live, mutable ContentRecord.content — draft edits show up immediately.

    Send mode: a pinned version is used if given, otherwise the latest frozen
    ContentVersionDB is resolved. If no version exists at all, raises
    UnpublishedContentError rather than silently sending draft content.
    """
    version = None

    if content_version_id is not None:
        version = (
            db.query(ContentVersionDB)
            .filter(ContentVersionDB.id == content_version_id)
            .first()
        )
    elif mode == "send":
        version = (
            db.query(ContentVersionDB)
            .filter(ContentVersionDB.content_record_id == content_record_id)
            .order_by(ContentVersionDB.version_number.desc())
            .first()
        )

    if version is not None:
        return {"id": content_record_id, **(version.content or {})}

    if mode == "send":
        raise UnpublishedContentError(content_record_id)

    record = (
        db.query(ContentRecordDB)
        .filter(ContentRecordDB.id == content_record_id)
        .first()
    )
    if record is None:
        return None

    return {"id": record.id, **(record.content or {})}


def resolve_content_for_module(
    db: Session,
    module: ModuleInstanceDB,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
    override: "ContentOverrideDB | None" = None,
) -> tuple[dict | None, DecisionResolutionDB | None]:
    """
    Returns (content, decision_resolution). decision_resolution is the
    DecisionResolutionDB row actually used (set only for decision-slot-driven
    modules) — callers building an audit/render_context should reuse this
    rather than re-querying, so rendering and the recorded metadata can never
    disagree about which resolution was used (ADR-062).
    """
    # Record-level override pin (ADR-041) wins over both static content and the
    # decision slot: render the pinned record instead. No decision_resolution is
    # returned — the decision wasn't what got used.
    if override is not None and override.override_content_record_id is not None:
        return (
            resolve_renderable_content(
                db=db,
                content_record_id=override.override_content_record_id,
                mode=mode,
            ),
            None,
        )

    if module.content_record_id is not None:
        return (
            resolve_renderable_content(
                db=db,
                content_record_id=module.content_record_id,
                mode=mode,
            ),
            None,
        )

    if module.decision_slot_id is not None:
        resolution_query = (
            db.query(DecisionResolutionDB)
            .filter(DecisionResolutionDB.decision_slot_id == module.decision_slot_id)
        )

        if recipient_id is not None:
            resolution = (
                resolution_query
                .filter(DecisionResolutionDB.recipient_id == recipient_id)
                .order_by(DecisionResolutionDB.created_at.desc())
                .first()
            )
            if resolution is None:
                resolution = (
                    resolution_query
                    .filter(DecisionResolutionDB.recipient_id.is_(None))
                    .order_by(DecisionResolutionDB.created_at.desc())
                    .first()
                )
        else:
            resolution = (
                resolution_query
                .filter(DecisionResolutionDB.recipient_id.is_(None))
                .order_by(DecisionResolutionDB.created_at.desc())
                .first()
            )

        if resolution is None:
            return None, None

        content = resolve_renderable_content(
            db=db,
            content_record_id=resolution.content_record_id,
            content_version_id=resolution.content_version_id,
            mode=mode,
        )
        return content, resolution

    return None, None
