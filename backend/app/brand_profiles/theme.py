"""A brand profile's look and link tags, applied to an email (task-354;
ADR-194, addendum 2026-10-11 (third)).

brand.css names a profile value as `var(--field, fallback)`. Mail programs
cannot read CSS variables, so `resolve_css` replaces each one with the
profile's value, or with the fallback when the profile leaves it empty, before
the stylesheet is inlined. The link parameters every module link carries come
from the profile and the campaign's and variant's names.
"""
import re

from app.brand_profiles.structure import profile_structure
from app.rendering.tracking import CONTENT_PARAM

#: Field types whose values may go into CSS. A text, url or image field named
#: in brand.css always falls back: free text never reaches a stylesheet.
CSS_TYPES = frozenset({"colour", "size", "font_family", "number"})

#: `var(--name, fallback)`; the fallback runs to the closing parenthesis and
#: may hold commas (a font list).
_VAR = re.compile(r"var\(\s*--([a-z][a-z0-9_]*)\s*(?:,\s*([^)]*?))?\s*\)")


def resolve_css(css: str, values: dict | None) -> str:
    """brand.css with every var() replaced by a value or its fallback."""
    types = {f.name: f.type for f in profile_structure()}
    values = values or {}

    def value_for(match: re.Match) -> str:
        name, fallback = match.group(1), (match.group(2) or "").strip()
        value = values.get(name)
        if types.get(name) in CSS_TYPES and value not in (None, ""):
            return str(value)
        return fallback

    return _VAR.sub(value_for, css)


def slug(name: str | None) -> str:
    """A readable label: lowercase, every run of other characters one hyphen."""
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def link_params(values: dict | None, campaign_name: str | None, variant_name: str | None) -> list[list[str]]:
    """The parameters every module link carries, in order, as `[key, value]`
    pairs (JSON, for the frame). None at all unless the profile sets
    utm_source."""
    values = values or {}
    source = str(values.get("utm_source") or "").strip()
    if not source:
        return []
    params = [["utm_source", source]]
    if medium := str(values.get("utm_medium") or "").strip():
        params.append(["utm_medium", medium])
    if campaign := slug(campaign_name):
        params.append(["utm_campaign", campaign])
    if content := slug(variant_name):
        params.append(["utm_content", content])
    taken = {key for key, _ in params}
    for line in str(values.get("utm_extra") or "").splitlines():
        key, _, value = line.strip().partition("=")
        # Never the click-attribution parameter (ADR-182 point 3, Codex doc-15):
        # a profile's extras go on every module link, so `nl_content` there
        # would credit content to a header, footer or button. Nor a key set
        # above. Dropped here as well as refused on save, because a value saved
        # before the refusal existed must not attribute either.
        if key and key != CONTENT_PARAM and key not in taken:
            params.append([key, value])
            taken.add(key)
    return params


def live_theme(db, variant) -> dict:
    """The theme a live render uses (preview, test send): the variant's
    profile as it is now, and its campaign's and its own names. A snapshot
    freezes the same two things (`rendering.frame.build_frame`)."""
    from app.brand_profiles.service import profile_of_variant
    from app.campaigns.db_models import CampaignDB

    if variant is None:
        return {}
    campaign = db.query(CampaignDB).filter(CampaignDB.id == variant.campaign_id).first()
    if campaign is None:
        return {}
    from app.assets.resolve import resolve_profile_values

    # Library images become addresses here, as the frame freezes them (ADR-197).
    values = resolve_profile_values(
        db, dict(profile_of_variant(db, variant, campaign.brand_id).field_values or {}), campaign.brand_id)
    return {"values": values, "link_params": link_params(values, campaign.name, variant.name)}
