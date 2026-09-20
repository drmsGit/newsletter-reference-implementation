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
from app.modules.registry import ModuleManifest, get_manifest, get_template_html
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
    Path(__file__).parent.parent.parent.parent / "storage" / "modules" / "email" / "brand.css"
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
    # The variant's channel decides which manifests resolve — ADR-161 point 7:
    # a channel is "an attribute on the variant plus which manifests it
    # accepts". Read once here rather than per module.
    #
    # This function stays EMAIL-shaped: it returns an HTML string, and ADR-162
    # point 3's role-tagged artifacts are not built. The channel is threaded
    # through so module lookup is correct, not because this can render a push.
    from app.campaigns.db_models import VariantDB

    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()
    channel = variant.channel if variant is not None else "email"

    # **Refuses a variant that is not an email**, rather than producing an
    # empty document. This function assembles email modules; handed a push
    # variant it found no email manifest for `notification`, rendered every
    # module as an HTML comment, and returned a 252-character empty shell —
    # with no error, because nothing failed. The send-test page then mailed
    # that shell to a real address and reported success, since its
    # `except Exception` fallback never fired.
    #
    # Callers that do not know the channel should use `render_variant`, which
    # dispatches (ADR-162 point 4). This one is the email path by name.
    # The literal is deliberate: importing `EmailRenderer` here to read its
    # `channel` would close a loop — `renderers/email.py` imports this module —
    # that only survives because the reverse import is lazy. This function is
    # the email path by name, so naming the channel is honest rather than a
    # hardcoding the registry should own.
    if channel != "email":
        raise ValueError(
            f"variant {variant_id} is a {channel} variant — render_variant_html "
            f"assembles email modules. Use render_variant() to dispatch by channel."
        )

    modules = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position)
        .all()
    )

    rendered_modules = []
    resolutions_by_module_id: dict[int, DecisionResolutionDB] = {}

    for module in modules:
        html, resolution = render_module(db=db, module=module, channel=channel, recipient_id=recipient_id, mode=mode)
        rendered_modules.append(html)
        if resolution is not None:
            resolutions_by_module_id[module.id] = resolution

    brand_css = _load_brand_css()

    # The preheader — the hidden span clients read as the inbox preview — is
    # rendered by the `header` module's own template (ADR-162 point 1), so its
    # markup lives with the field that produces it. Nothing is injected here.
    preheader_html = ""

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
    channel: str,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
) -> tuple[str, DecisionResolutionDB | None]:
    """`channel` is passed down rather than looked up per module: the caller
    already has the variant, and a query per module to re-derive a value that
    cannot differ within one variant is the kind of thing that is invisible
    until a variant has forty of them."""
    manifest = get_manifest(channel, module.module_type)

    if manifest is None:
        return render_unknown_module(module), None

    if manifest.cms:
        return render_cms_module(db=db, module=module, manifest=manifest, channel=channel, recipient_id=recipient_id, mode=mode)

    return render_static_module(db=db, module=module, manifest=manifest, channel=channel, mode=mode), None


def envelope_fields_for_variant(
    db: Session, variant_id: int, channel: str
) -> dict:
    """Fields this variant's modules declare as belonging to the **envelope**
    rather than to the rendered body — ADR-162 point 1.

    Read from the manifests, so nothing here knows that email has a subject or
    that the module carrying it happens to be called `header`. A channel whose
    envelope needs a different field declares it and this function finds it.

    The modules are the only source. `variants.subject` / `preheader` were read
    as a fallback during the expand half and are gone (migration 0012) — a
    variant with no envelope module simply has no envelope copy, which is a
    real state and the reason the send path keeps the send instance's name as
    its last resort.
    """
    envelope: dict = {}
    modules = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position)
        .all()
    )
    for module in modules:
        manifest = get_manifest(channel, module.module_type)
        if manifest is None:
            continue
        data = module.module_data or {}
        for var in manifest.variables:
            if var.envelope and data.get(var.name):
                envelope[var.name] = data[var.name]

    return envelope


def render_variant(
    db: Session,
    variant_id: int,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
    *,
    brand_id: int | None = None,
):
    """Render a variant through its channel's renderer — ADR-162 point 4.

    **`brand_id` is optional here and required by its routes, deliberately.**
    Rendering is reached two ways: from a request, which has a working brand
    and passes it so another brand's variant cannot be previewed; and from the
    send path, which already resolved the brand when it locked the send
    instance and would only be re-deriving what it holds. Requiring it in both
    would push a redundant argument through `send_send_instance`; defaulting it
    in the route would be the fail-open ADR-172 point 3 refuses. The route
    passes `Depends(working_brand)` and therefore cannot forget.

    `render_variant_html` remains the email path and its four callers are
    untouched; this is the channel-neutral entry point, and for email it simply
    wraps that. Two entry points rather than one is a transitional state, not a
    design: point 3's artifact-set contract is what eventually collapses them,
    and it is not built.

    Raises ValueError for a channel with no renderer, rather than falling back
    to email. A fallback would render a push variant as an HTML email and
    deliver something nobody composed.
    """
    if brand_id is not None:
        from app.campaigns.service import get_variant

        if get_variant(db, variant_id, brand_id=brand_id) is None:
            raise ValueError(f"variant {variant_id} does not exist")

    from app.campaigns.db_models import VariantDB
    from app.rendering.renderers.registry import get_renderer

    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()
    if variant is None:
        raise ValueError(f"variant {variant_id} does not exist")

    renderer = get_renderer(variant.channel)
    if renderer is None:
        raise ValueError(
            f"no renderer is registered for channel '{variant.channel}' — "
            f"drop one into app/rendering/renderers/"
        )

    return renderer.render(
        db=db, variant_id=variant_id, recipient_id=recipient_id, mode=mode
    )


def resolve_module_variables(
    db: Session,
    module: ModuleInstanceDB,
    manifest: ModuleManifest,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
) -> tuple[dict | None, dict | None, DecisionResolutionDB | None]:
    """A module's declared variables, filled — decisions resolved, overrides
    applied, content version pinned. **No formatting of any kind.**

    Extracted from `render_cms_module` so the push renderer can share it, and
    that sharing is the point rather than a convenience: ADR-162 point 1's
    claim that moving fields into modules means "**overrides work unchanged**"
    is only true if every channel resolves its fields through the same path.
    A second copy of this loop would be where a channel quietly stopped
    honouring the override layer.

    It also keeps ADR-162 point 2's line intact — "it formats, it never
    decides". Everything decided happens here; a renderer receives values.

    Returns `(variables, content, resolution)`. The resolved content comes back
    alongside the variables because the caller may need the record it came from
    — email stamps `data-content-id` on the wrapper so a rendered email can be
    traced to its source. `(None, None, resolution)` means nothing resolved,
    which ADR-086 says is a hidden slot rather than a placeholder.
    """
    # An active content override (ADR-040/041) replaces individual fields of
    # the resolved content — a consistent headline across personalized picks,
    # a shorter copy for this send — and takes precedence until reset.
    override = get_active_content_override(db, module.id)

    content, decision_resolution = resolve_content_for_module(
        db=db, module=module, recipient_id=recipient_id, mode=mode
    )

    if content is None:
        return None, None, decision_resolution

    field_overrides = (override.field_overrides if override else None) or {}
    variables: dict = {}

    for var in manifest.variables:
        # Convention: template variable name = CMS field name exactly. A
        # field-level override wins over the resolved content value (ADR-041).
        if var.name in field_overrides:
            variables[var.name] = field_overrides[var.name]
        else:
            variables[var.name] = content.get(var.name, "")

    return variables, content, decision_resolution


def render_cms_module(
    db: Session,
    module: ModuleInstanceDB,
    manifest: ModuleManifest,
    channel: str,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
) -> tuple[str, DecisionResolutionDB | None]:
    variables, content, decision_resolution = resolve_module_variables(
        db=db, module=module, manifest=manifest, recipient_id=recipient_id, mode=mode
    )

    if variables is None:
        # ADR-086: no content resolved — hide the slot rather than show a placeholder
        return (
            f"<!-- module {module.id} ({module.module_type}): no content resolved, slot hidden -->",
            decision_resolution,
        )

    if variables.get(_RICH_TEXT_FIELD):
        variables = {
            **variables,
            _RICH_TEXT_FIELD: render_rich_text(variables[_RICH_TEXT_FIELD]),
        }

    html_source = get_template_html(channel, module.module_type)
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
    channel: str,
    mode: RenderMode = "preview",
) -> str:
    html_source = get_template_html(channel, module.module_type)
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

    # A field override wins over both module_data and the content-record fill
    # (ADR-041) — same treatment as the CMS path, so overrides work on any
    # content-resolving module, not only cms:true ones.
    override = get_active_content_override(db, module.id)
    if override is not None and override.field_overrides:
        for name, value in override.field_overrides.items():
            variables[name] = value

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
) -> tuple[dict | None, DecisionResolutionDB | None]:
    """
    Returns (content, decision_resolution). decision_resolution is the
    DecisionResolutionDB row actually used (set only for decision-slot-driven
    modules) — callers building an audit/render_context should reuse this
    rather than re-querying, so rendering and the recorded metadata can never
    disagree about which resolution was used (ADR-062).

    Content-record *swaps* (Case 2, category-scoped) are not applied here yet —
    only field overrides exist today, applied by the callers after resolution.
    """
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
