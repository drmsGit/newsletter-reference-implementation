from sqlalchemy.orm import Session

from app.campaigns.db_models import (
    ModuleInstanceDB,
    DecisionResolutionDB,
)
from app.content.db_models import ContentRecordDB


def render_variant_html(
    db: Session,
    variant_id: int,
) -> str:
    modules = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position)
        .all()
    )

    rendered_modules = [
        render_module(db=db, module=module)
        for module in modules
    ]

    return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Newsletter Preview</title>
  </head>
  <body>
    {content}
  </body>
</html>
""".replace("{content}", "\n".join(rendered_modules))


def render_module(
    db: Session,
    module: ModuleInstanceDB,
) -> str:
    if module.module_type == "hero":
        return render_hero(module)

    if module.module_type == "content_card":
        return render_content_card(db=db, module=module)

    if module.module_type == "cta":
        return render_cta(module)

    return render_unknown_module(module)


def render_hero(module: ModuleInstanceDB) -> str:
    data = module.module_data or {}

    headline = data.get("headline", "Hero")
    text = data.get("text", "")

    return f"""
<section data-module-id="{module.id}" data-module-type="hero">
  <h1>{headline}</h1>
  <p>{text}</p>
</section>
"""


def render_content_card(
    db: Session,
    module: ModuleInstanceDB,
) -> str:
    content_record = resolve_content_record_for_module(
        db=db,
        module=module,
    )

    if content_record is None:
        return f"""
<section data-module-id="{module.id}" data-module-type="content_card">
  <p>No content resolved.</p>
</section>
"""

    data = module.module_data or {}

    title = data.get("headline_override") or content_record.title
    body = data.get("body_override") or content_record.body

    return f"""
<article data-module-id="{module.id}" data-module-type="content_card" data-content-record-id="{content_record.id}">
  <h2>{title}</h2>
  <p>{body}</p>
</article>
"""


def render_cta(module: ModuleInstanceDB) -> str:
    data = module.module_data or {}

    label = data.get("label", "Click here")
    url = data.get("url", "#")

    return f"""
<section data-module-id="{module.id}" data-module-type="cta">
  <a href="{url}">{label}</a>
</section>
"""


def render_unknown_module(module: ModuleInstanceDB) -> str:
    return f"""
<section data-module-id="{module.id}" data-module-type="{module.module_type}">
  <p>Unknown module type: {module.module_type}</p>
</section>
"""


def resolve_content_record_for_module(
    db: Session,
    module: ModuleInstanceDB,
) -> ContentRecordDB | None:
    if module.content_record_id is not None:
        return (
            db.query(ContentRecordDB)
            .filter(ContentRecordDB.id == module.content_record_id)
            .first()
        )

    if module.decision_slot_id is not None:
        resolution = (
            db.query(DecisionResolutionDB)
            .filter(DecisionResolutionDB.decision_slot_id == module.decision_slot_id)
            .order_by(DecisionResolutionDB.created_at.desc())
            .first()
        )

        if resolution is None:
            return None

        return (
            db.query(ContentRecordDB)
            .filter(ContentRecordDB.id == resolution.content_record_id)
            .first()
        )

    return None