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
from app.modules.registry import (
    ModuleManifest, envelope_module_type, get_manifest, get_template_html, required_when_shown,
)
from app.overrides.service import get_active_content_override
from app.brand_profiles.theme import resolve_css

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


def parse_links(value) -> list[dict]:
    """A profile's link list (field type `links`): one link per line,
    "Label | https://address", in the order written; blank lines skipped.
    Templates read it as `{% for link in profile.menu_links | links %}`."""
    links = []
    for line in str(value or "").splitlines():
        label, _, url = line.partition("|")
        if label.strip() and url.strip():
            links.append({"label": label.strip(), "url": url.strip()})
    return links


_jinja.filters["links"] = parse_links
_inliner = css_inline.CSSInliner()

_BRAND_CSS_PATH = (
    Path(__file__).parent.parent.parent.parent / "storage" / "modules" / "email" / "brand.css"
)

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


def apply_rich_text(variables: dict, manifest: ModuleManifest) -> dict:
    """Format every `richtext` field, leave every other field alone.

    **Driven by the declared type, not by a field name.** Until 2026-09-28 a
    module-level constant named one field — `body_medium` — so `body_long`,
    which ADR-177's size vocabulary requires, would have rendered as literal
    asterisks and nobody would have been told. The type is declared once in
    `storage/fields.json` and every field carrying it is formatted.

    **Only the HTML-producing renderers call this.** Rich text emits `<strong>`
    and `<br>`; a push notification has no document to put them in, so the push
    renderer calls `strip_rich_text` instead. That was previously true only by
    accident of layout — the paths diverged before the constant was read, and
    push happened to use `push_body` rather than `body_medium`. A declared type
    any channel can use removes the accident, so the rule is written down.

    **Not called by `missing_required_fields`**, deliberately: that check reads
    values to see whether they are empty, and formatting them first would mean
    asking whether `Markup('')` is falsey rather than whether a manager filled
    the field in.
    """
    formatted = dict(variables)
    for var in manifest.variables:
        if var.type == "richtext" and formatted.get(var.name):
            formatted[var.name] = render_rich_text(formatted[var.name])
    return formatted


def strip_rich_text(variables: dict, manifest: ModuleManifest) -> dict:
    """The counterpart, for a channel with no document to render into.

    A notification body is read by an operating system, not a browser, so
    markup arrives as the characters it is made of. Stripping is part of
    formatting for that channel rather than a degradation of it.
    """
    plain = dict(variables)
    for var in manifest.variables:
        value = plain.get(var.name)
        if var.type != "richtext" or not isinstance(value, str) or not value:
            continue
        text = _RICH_TEXT_LINK.sub(r"\1", value)
        plain[var.name] = _RICH_TEXT_BOLD.sub(r"\1", text)
    return plain


def render_variant_html(
    db: Session,
    variant_id: int,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
    collect_resolutions: bool = False,
    footer: str = "",
) -> str | tuple[str, dict[int, DecisionResolutionDB]]:
    # The variant's channel decides which manifests resolve — ADR-161 point 7:
    # a channel is "an attribute on the variant plus which manifests it
    # accepts". Read once here rather than per module.
    #
    # This function stays EMAIL-shaped: it returns an HTML string, and ADR-162
    # point 3's role-tagged artifacts are not built. The channel is threaded
    # through so module lookup is correct, not because this can render a push.

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
    # The variant's brand profile as it is now (task-354): its look fills
    # brand.css and the templates, its tags go on every module link. A
    # snapshot freezes the same theme (frame.py), so preview and send agree.
    from app.brand_profiles.theme import live_theme

    theme = live_theme(db, variant)

    for module in modules:
        html, resolution = render_module(db=db, module=module, channel=channel, recipient_id=recipient_id,
                                         mode=mode, theme=theme)
        rendered_modules.append(html)
        if resolution is not None:
            resolutions_by_module_id[module.id] = resolution

    # The preheader — the hidden span clients read as the inbox preview — is
    # rendered by the `header` module's own template (ADR-162 point 1), so its
    # markup lives with the field that produces it. Nothing is injected here.
    # `footer` is the legal footer a test send carries (task-357); a preview
    # passes none, so what the editor shows is unchanged.
    final_html = email_document(rendered_modules, footer, theme=theme)

    if collect_resolutions:
        return final_html, resolutions_by_module_id
    return final_html


def render_module(
    db: Session,
    module: ModuleInstanceDB,
    channel: str,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
    theme: dict | None = None,
) -> tuple[str, DecisionResolutionDB | None]:
    """`channel` is passed down rather than looked up per module: the caller
    already has the variant, and a query per module to re-derive a value that
    cannot differ within one variant is the kind of thing that is invisible
    until a variant has forty of them."""
    manifest = get_manifest(channel, module.module_type)

    if manifest is None:
        return render_unknown_module(module), None

    if manifest.cms:
        return render_cms_module(db=db, module=module, manifest=manifest, channel=channel, recipient_id=recipient_id,
                                 mode=mode, theme=theme)

    return render_static_module(db=db, module=module, manifest=manifest, channel=channel, mode=mode,
                                theme=theme), None


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
    return fill_variables(module, manifest, content, field_overrides), content, decision_resolution


def fill_variables(module: ModuleInstanceDB, manifest: ModuleManifest, content: dict,
                   field_overrides: dict | None = None) -> dict:
    """One record's values onto the module's declared variables."""
    field_overrides = field_overrides or {}
    variables: dict = {}
    module_data = module.module_data or {}
    for var in manifest.variables:
        # A field typed in the module itself (ADR-179's 2026-10-04 addendum):
        # read from module_data, never overridden. Reached only once content
        # resolved, so it hides with its module (ADR-086).
        if var.source == "module":
            variables[var.name] = module_data.get(var.name) or ""
            continue
        # Convention: template variable name = CMS field name exactly. A
        # field-level override wins over the resolved content value (ADR-041).
        if var.name in field_overrides:
            variables[var.name] = field_overrides[var.name]
        else:
            variables[var.name] = content.get(var.name, "")
    return variables


def module_html(
    channel: str,
    module_type: str,
    module_id: int,
    variables: dict,
    content_id: int | None = None,
    *,
    template_type: str | None = None,
    theme: dict | None = None,
) -> str:
    """One module's HTML from values already decided — the formatting half.

    `theme` is `{"values", "link_params"}` from the brand profile (task-354):
    the template gets the values as `profile` (for styles written as
    attributes, MJML's way, ADR-131), and every link gets the parameters.
    None renders as a frame made before profiles did.

    Shared by the live render (`render_cms_module`, `render_static_module`) and
    the frame render (`app.rendering.frame`), so a module looks the same
    whichever path produced it. Rich text is applied here; nothing is resolved.
    """
    # `template_type` is where the template and manifest are found when that
    # differs from the name written into the HTML: a frame frozen before the
    # envelope was renamed still renders as `header` (task-349).
    looked_up = template_type or module_type
    manifest = get_manifest(channel, looked_up)
    html_source = get_template_html(channel, looked_up)
    if manifest is None or html_source is None:
        return (
            f'<div data-module-id="{module_id}" data-module-type="{module_type}">'
            f"<!-- unknown module type: {module_type} -->"
            f"</div>"
        )
    theme = theme or {}
    rendered = _jinja.from_string(html_source).render(
        **{**apply_rich_text(variables, manifest), "profile": theme.get("values") or {}},
    )
    if content_id is not None:
        # The link names its content (task-240, ADR-182): only here, inside a
        # content-bound module, so a non-content link credits nothing.
        from app.rendering.tracking import tag_links

        rendered = tag_links(rendered, content_id)
    if theme.get("link_params"):
        # Every module link, content or typed in; never the legal footer,
        # which is not a module (ADR-194 addendum 2026-10-11 (third)).
        from app.rendering.tracking import tag_params

        rendered = tag_params(rendered, theme["link_params"])
    content_attr = f' data-content-id="{content_id}"' if content_id is not None else ""
    return (
        f'<div data-module-id="{module_id}" data-module-type="{module_type}"{content_attr}>\n'
        f"{rendered}\n"
        f"</div>"
    )


def email_document(rendered_modules: list[str], footer: str = "", *, theme: dict | None = None) -> str:
    """Wrap rendered modules into the inlined email document. Shared by the live
    and the frame render for the same reason as `module_html`.

    `footer` is the unsubscribe line a sent marketing email carries (ADR-191
    point 5); a preview has none. **Without one the document is byte-for-byte
    what it always was**, so every delivery record written before ADR-191
    still reconstructs to its stored hash (ADR-183).
    """
    raw_html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Newsletter Preview</title>
    <style>{resolve_css(_load_brand_css(), (theme or {}).get("values"))}</style>
  </head>
  <body>
    {""}
    {"".join(rendered_modules)}{f"""
    {footer}""" if footer else ""}
  </body>
</html>"""
    return _inliner.inline(raw_html)


#: The legal footer's template (ADR-194, addendum 2026-10-11 (second)): in the
#: channel's template folder so the fingerprint covers it, named with a leading
#: underscore so the registry does not take it for a module.
LEGAL_FOOTER_TEMPLATE = "_legal_footer.html"


def legal_footer_html(
    profile: dict, unsubscribe_url: str | None = None, *, unsubscribe_unlinked: bool = False,
) -> str:
    """The legal footer for a frozen profile (`{language, values, ...}`, as a
    version-3 frame holds it): legal name and address, imprint and privacy
    links, and the unsubscribe wording — linked to `unsubscribe_url`, shown
    plain when `unsubscribe_unlinked` (a test send has no token), and left out
    otherwise or when the profile has no wording."""
    from app.modules.registry import MODULES_DIR

    source = (MODULES_DIR / "email" / LEGAL_FOOTER_TEMPLATE).read_text()
    values = profile.get("values") or {}
    return _jinja.from_string(source).render(
        **values,
        language=profile.get("language") or "en",
        unsubscribe_url=unsubscribe_url,
        unsubscribe_unlinked=unsubscribe_unlinked,
    ).strip()


def render_cms_module(
    db: Session,
    module: ModuleInstanceDB,
    manifest: ModuleManifest,
    channel: str,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
    theme: dict | None = None,
) -> tuple[str, DecisionResolutionDB | None]:
    if module.decision_slot_id is not None:
        # A slot shows up to its "show up to", first pick first: the module
        # repeats once per pick, each copy with its own content id (ADR-084
        # addendum 2026-10-11). Never overridden (ADR-178 point 5).
        picked = slot_contents(db, module, recipient_id=recipient_id, mode=mode)
        if not picked:
            return (f"<!-- module {module.id} ({module.module_type}): no content resolved, slot hidden -->",
                    None)
        return (
            "\n".join(
                module_html(channel, module.module_type, module.id,
                            without_hidden(fill_variables(module, manifest, content), module.hidden_fields),
                            content_id=content["id"], theme=theme)
                for content, _resolution in picked
            ),
            picked[0][1],
        )

    variables, content, decision_resolution = resolve_module_variables(
        db=db, module=module, manifest=manifest, recipient_id=recipient_id, mode=mode
    )

    if variables is None:
        # ADR-086: no content resolved — hide the slot rather than show a placeholder
        return (
            f"<!-- module {module.id} ({module.module_type}): no content resolved, slot hidden -->",
            decision_resolution,
        )

    return (
        module_html(channel, module.module_type, module.id, without_hidden(variables, module.hidden_fields),
                    content_id=content["id"], theme=theme),
        decision_resolution,
    )


def without_hidden(variables: dict, hidden) -> dict:
    """`variables` less the fields the module hides (ADR-187 point 5): a hidden
    field reaches the template as empty — before any MJML compile — and its
    value stays where it is. Applied where values are handed to a template,
    never where they are read for editing."""
    hidden = set(hidden or ())
    return {k: v for k, v in variables.items() if k not in hidden}


def static_module_variables(
    db: Session,
    module: ModuleInstanceDB,
    manifest: ModuleManifest,
    mode: RenderMode = "preview",
    with_source: bool = False,
) -> dict | tuple[dict, dict | None]:
    """A static module's declared variables, filled — the `cms: false` twin of
    `resolve_module_variables`, and **no formatting of any kind**.

    Extracted from `render_static_module` on 2026-09-28 so the pre-send
    required-field check can ask what a module *would* render without
    rendering it. The extraction is the point rather than a tidy-up: a check
    that rebuilt this merge itself would drift from what actually ships, which
    is the failure `CONTENT_FIELD_GROUPS` documents about its own duplicate.

    The precedence is unchanged — `module_data`, then a fill from the linked
    content record where `module_data` is sparse, then an active field override
    on top ([[ADR-041]]).
    """
    variables = dict(module.module_data or {})

    # If module_data is sparse, fill missing required variables from the
    # linked content record so static modules render something useful.
    content = None
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

    # `with_source` hands back the content the fill came from, for a frame that
    # records which version was used (ADR-183).
    return (variables, content) if with_source else variables


def render_static_module(
    db: Session,
    module: ModuleInstanceDB,
    manifest: ModuleManifest,
    channel: str,
    mode: RenderMode = "preview",
    theme: dict | None = None,
) -> str:
    return module_html(
        channel, module.module_type, module.id,
        without_hidden(static_module_variables(db, module, manifest, mode=mode), module.hidden_fields),
        theme=theme,
    )


# ---------------------------------------------------------------------------
# Pre-send checks
# ---------------------------------------------------------------------------

def missing_required_fields(
    db: Session, variant_id: int, mode: RenderMode = "send"
) -> list[tuple[int, str, str]]:
    """Required fields that would render empty, for the modules whose content
    does not depend on who receives it.

    Returns `(module_id, module_type, field_name)`, empty when nothing is
    missing. [[ADR-174]] point 3: *a required-field check runs before a send
    fires, this is not optional and it does not exist today* — an empty
    `push_title` ships to a real device and the first party to learn is the
    recipient.

    **Deliberately only the deterministic half.** A slot-bound module resolves
    per recipient inside the send loop, so whether one of its required fields
    is empty is a different question with a different answer per person, and
    refusing a thousand-recipient send because one person's pick lacks a field
    would be absurd. That case is a per-recipient skip, not a block, and it
    belongs to the "nothing meaningful" rule this deliberately does not touch.

    **An unbound module is not a finding, and that falls out rather than being
    special-cased.** It resolves to no content at all, so it declares no filled
    variables to test — which is the same answer the Manager Workflow interview
    reached for it independently: report it, never block on it.

    **It asks the render path rather than reimplementing it.** `cms` modules go
    through `resolve_module_variables` and static ones through
    `static_module_variables`, which are the functions that actually produce
    what ships. A second implementation of the merge would eventually disagree
    with the first, and the disagreement would be invisible until a send went
    out wrong.
    """
    from app.campaigns.db_models import ModuleInstanceDB

    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()
    if variant is None:
        return []

    modules = (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position)
        .all()
    )

    missing: list[tuple[int, str, str]] = []
    for module in modules:
        if module.decision_slot_id is not None:
            continue  # per-recipient; see the docstring

        manifest = get_manifest(variant.channel, module.module_type)
        if manifest is None:
            continue  # an unknown module renders a comment and declares nothing

        try:
            if manifest.cms:
                variables, _, _ = resolve_module_variables(
                    db=db, module=module, manifest=manifest, recipient_id=None, mode=mode,
                )
                if variables is None:
                    continue  # nothing bound — not a finding
            else:
                variables = static_module_variables(db, module, manifest, mode=mode)
        except UnpublishedContentError:
            # A different gate's job, and it is already closed:
            # `create_snapshot_for_variant` refuses to freeze a variant whose
            # content has never been published, so such a variant cannot reach
            # a send at all. Reporting it here as a missing field would name
            # the wrong cause — the fields may be perfectly well filled on a
            # draft nobody has frozen yet.
            continue

        # Required when shown (ADR-187 point 6): a hidden field is not missing.
        for name in required_when_shown(manifest, module.hidden_fields):
            if not str(variables.get(name, "") or "").strip():
                missing.append((module.id, module.module_type, name))

    return missing


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
    """The record's fields as rendering uses them: `_raw_renderable_content`,
    with every library image (`asset:<id>`) made an absolute address and an
    empty paired alt filled from the image (ADR-197 point 12). Every path into
    rendering comes through here — live preview, frame, slot picks, push — so
    the frame freezes the address, never the reference."""
    content = _raw_renderable_content(db, content_record_id, content_version_id, mode)
    if content is None:
        return None
    from app.assets.resolve import content_image_fields, resolve_images

    pairs = content_image_fields()
    if not any(isinstance(content.get(name), str) and content[name].startswith("asset:") for name in pairs):
        return content
    brand_id = db.query(ContentRecordDB.brand_id).filter(ContentRecordDB.id == content_record_id).scalar()
    return resolve_images(db, content, pairs, brand_id)


def _raw_renderable_content(
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
        # `_version_id` says which frozen version this is, so a frame can record
        # the version actually used rather than re-querying "latest" afterwards
        # (ADR-128, ADR-183). Underscored: no manifest variable can be named it,
        # so it never reaches a template.
        return {"id": content_record_id, **(version.content or {}), "_version_id": version.id}

    if mode == "send":
        raise UnpublishedContentError(content_record_id)

    record = (
        db.query(ContentRecordDB)
        .filter(ContentRecordDB.id == content_record_id)
        .first()
    )
    if record is None:
        return None

    return {"id": record.id, **(record.content or {}), "_version_id": None}


def slot_contents(
    db: Session,
    module: ModuleInstanceDB,
    recipient_id: int | None = None,
    mode: RenderMode = "preview",
) -> list[tuple[dict, DecisionResolutionDB]]:
    """A slot module's picks as renderable content, first pick first: the
    recipient's set, else the slot's global one (`app.decision.sets`). A pick
    whose content cannot be rendered is left out. Empty: nothing to show."""
    from app.decision.sets import latest_pick_set

    picked = []
    for resolution in latest_pick_set(db, module.decision_slot_id, recipient_id):
        content = resolve_renderable_content(
            db=db, content_record_id=resolution.content_record_id,
            content_version_id=resolution.content_version_id, mode=mode,
        )
        if content is not None:
            picked.append((content, resolution))
    return picked


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
        picked = slot_contents(db, module, recipient_id=recipient_id, mode=mode)
        return picked[0] if picked else (None, None)

    return None, None


def module_states(
    db: Session, variant_id: int, recipient_id: int | None = None, *, brand_id: int
) -> list[dict]:
    """What each module of a variant is doing, for the composer's preview
    (task-227). Read-only: nothing is resolved or written.

    Per module, in order, the envelope left out (it is the variant's, shown
    apart): its `kind` — `record`, `slot`, `typed` (a static module's own
    fields), `unbound` (a catalogue module with no content yet) or `unknown`
    (no manifest on this channel) — and, as they apply:

    - `slot_state` (Variant Editor interview 4.4): `resolved`, `not_run`,
      `per_recipient` (no generic pick, but picks for named people: name one to
      see theirs), or
      `finds_nothing` — its rule matches no active content
      (`slot_candidate_count`, task-205), so ADR-086 will hide it and the
      email ships shorter. That outranks an older pick: the rule is what a
      send will run.
    - `generic_pick` (4.2): a recipient was named and has no pick of their
      own, so the generic one is shown. Read from the resolution the renderer
      itself uses (`resolve_content_for_module`), so the label and the render
      cannot disagree.
    - `unpublished_changes` (4.3): the record's live content, which a preview
      shows, differs from the version a send would use (task-257).
    - `missing_required`: required fields that would render empty, for the
      modules whose content does not depend on the recipient (ADR-174 point 3).
    """
    from app.campaigns.service import slot_candidate_count
    from app.content.service import get_content_record, publish_state

    variant = db.query(VariantDB).filter(VariantDB.id == variant_id).first()
    envelope = envelope_module_type(variant.channel)
    missing: dict[int, list[str]] = {}
    for module_id, _type, field in missing_required_fields(db, variant_id, mode="preview"):
        missing.setdefault(module_id, []).append(field)

    states = []
    for module in (
        db.query(ModuleInstanceDB)
        .filter(ModuleInstanceDB.variant_id == variant_id)
        .order_by(ModuleInstanceDB.position)
    ):
        if module.module_type == envelope:
            continue
        manifest = get_manifest(variant.channel, module.module_type)
        state = {
            "module_id": module.id, "position": module.position, "module_type": module.module_type,
            "slot_state": None, "generic_pick": False, "unpublished_changes": False,
            "missing_required": sorted(missing.get(module.id, [])),
        }
        if manifest is None:
            state["kind"] = "unknown"
        elif module.decision_slot_id is not None:
            state["kind"] = "slot"
            _content, resolution = resolve_content_for_module(
                db=db, module=module, recipient_id=recipient_id, mode="preview")
            candidates = slot_candidate_count(db, module.decision_slot_id, brand_id=brand_id)
            if candidates is not None and candidates["candidate_count"] == 0:
                state["slot_state"] = "finds_nothing"
            elif resolution is None:
                # No generic pick, but picks for named people: a per-recipient
                # strategy that has run. "Not run" would be false; it needs a
                # recipient named to show anything (found live, 2026-10-04).
                personal = recipient_id is None and db.query(DecisionResolutionDB.id).filter(
                    DecisionResolutionDB.decision_slot_id == module.decision_slot_id,
                    DecisionResolutionDB.recipient_id.isnot(None),
                ).first() is not None
                state["slot_state"] = "per_recipient" if personal else "not_run"
            else:
                state["slot_state"] = "resolved"
                state["generic_pick"] = recipient_id is not None and resolution.recipient_id is None
        elif module.content_record_id is not None:
            state["kind"] = "record"
            record = get_content_record(db, module.content_record_id, brand_id=brand_id)
            state["unpublished_changes"] = record is not None and publish_state(db, record)[1]
        elif manifest.cms:
            state["kind"] = "unbound"
        else:
            state["kind"] = "typed"
        states.append(state)
    return states
