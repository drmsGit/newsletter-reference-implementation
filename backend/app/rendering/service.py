import re
from pathlib import Path
from typing import Literal

import css_inline
from jinja2 import BaseLoader, Environment
from markupsafe import Markup, escape
from sqlalchemy.orm import Session

from app.campaigns.db_models import ModuleInstanceDB, DecisionResolutionDB
from app.content.db_models import ContentRecordDB, ContentVersionDB
from app.email_modules.registry import ModuleManifest, get_manifest, get_template_html

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
) -> str:
    modules = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position)
        .all()
    )

    rendered_modules = [
        render_module(db=db, module=module, recipient_id=recipient_id, mode=mode)
        for module in modules
    ]

    brand_css = _load_brand_css()

    raw_html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Newsletter Preview</title>
    <style>{brand_css}</style>
  </head>
  <body>
    {"".join(rendered_modules)}
  </body>
</html>"""

    return _inliner.inline(raw_html)


def render_module(
    db: Session,
    module: ModuleInstanceDB,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
) -> str:
    manifest = get_manifest(module.module_type)

    if manifest is None:
        return render_unknown_module(module)

    if manifest.cms:
        return render_cms_module(db=db, module=module, manifest=manifest, recipient_id=recipient_id, mode=mode)

    return render_static_module(db=db, module=module, manifest=manifest, mode=mode)


def render_cms_module(
    db: Session,
    module: ModuleInstanceDB,
    manifest: ModuleManifest,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
) -> str:
    content = resolve_content_for_module(db=db, module=module, recipient_id=recipient_id, mode=mode)

    if content is None:
        # ADR-086: no content resolved — hide the slot rather than show a placeholder
        return f"<!-- module {module.id} ({module.module_type}): no content resolved, slot hidden -->"

    data = module.module_data or {}
    variables: dict = {}

    for var in manifest.variables:
        # Convention: template variable name = CMS field name exactly.
        # Override in module_data (stored as {name}_override) takes priority.
        override = data.get(f"{var.name}_override")
        variables[var.name] = override if override else content.get(var.name, "")

    if variables.get(_RICH_TEXT_FIELD):
        variables[_RICH_TEXT_FIELD] = render_rich_text(variables[_RICH_TEXT_FIELD])

    html_source = get_template_html(module.module_type)
    if html_source is None:
        return render_unknown_module(module)

    rendered = _jinja.from_string(html_source).render(**variables)

    return (
        f'<div data-module-id="{module.id}" data-module-type="{module.module_type}"'
        f' data-content-id="{content["id"]}">\n'
        f"{rendered}\n"
        f"</div>"
    )


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
) -> dict | None:
    if module.content_record_id is not None:
        return resolve_renderable_content(
            db=db,
            content_record_id=module.content_record_id,
            mode=mode,
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
            return None

        return resolve_renderable_content(
            db=db,
            content_record_id=resolution.content_record_id,
            content_version_id=resolution.content_version_id,
            mode=mode,
        )

    return None
