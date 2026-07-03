from pathlib import Path

import css_inline
from jinja2 import BaseLoader, Environment
from sqlalchemy.orm import Session

from app.campaigns.db_models import ModuleInstanceDB, DecisionResolutionDB
from app.content.db_models import ContentRecordDB, ContentVersionDB
from app.email_modules.registry import ModuleManifest, get_manifest, get_template_html

_jinja = Environment(loader=BaseLoader())
_inliner = css_inline.CSSInliner()

_BRAND_CSS_PATH = (
    Path(__file__).parent.parent.parent.parent / "storage" / "email_modules" / "brand.css"
)


def _load_brand_css() -> str:
    if _BRAND_CSS_PATH.exists():
        return _BRAND_CSS_PATH.read_text()
    return ""


def render_variant_html(
    db: Session,
    variant_id: int,
    recipient_id: int | None = None,
) -> str:
    modules = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position)
        .all()
    )

    rendered_modules = [
        render_module(db=db, module=module, recipient_id=recipient_id)
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
) -> str:
    manifest = get_manifest(module.module_type)

    if manifest is None:
        return render_unknown_module(module)

    if manifest.cms:
        return render_cms_module(db=db, module=module, manifest=manifest, recipient_id=recipient_id)

    return render_static_module(module=module, manifest=manifest)


def render_cms_module(
    db: Session,
    module: ModuleInstanceDB,
    manifest: ModuleManifest,
    recipient_id: int | None = None,
) -> str:
    content = resolve_content_for_module(db=db, module=module, recipient_id=recipient_id)

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
    module: ModuleInstanceDB,
    manifest: ModuleManifest,
) -> str:
    html_source = get_template_html(module.module_type)
    if html_source is None:
        return render_unknown_module(module)

    variables = module.module_data or {}
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
) -> dict | None:
    """
    Returns the raw content fields as a flat dict keyed by their CMS field names.
    Template variables must match these names exactly — no mapping layer.
    If a pinned version exists, its full JSON is returned.
    Falls back to the live ContentRecord columns (title → title, body → body).
    """
    if content_version_id is not None:
        version = (
            db.query(ContentVersionDB)
            .filter(ContentVersionDB.id == content_version_id)
            .first()
        )
        if version is not None:
            content = version.content or {}
            return {"id": content_record_id, **content}

    record = (
        db.query(ContentRecordDB)
        .filter(ContentRecordDB.id == content_record_id)
        .first()
    )
    if record is None:
        return None

    return {
        "id": record.id,
        "title": record.title,
        "body": record.body,
    }


def resolve_content_for_module(
    db: Session,
    module: ModuleInstanceDB,
    recipient_id: int | None = None,
) -> dict | None:
    if module.content_record_id is not None:
        return resolve_renderable_content(
            db=db,
            content_record_id=module.content_record_id,
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
        )

    return None
