"""Putting a recipient's entries into the texts (task-365, ADR-199).

**Never Jinja.** User text never goes through the template engine, which is
the line between a manager's text and template injection. A {{name}} in a text
is replaced here, in values already assembled:

- **plain text** gets the raw value, and the autoescaping template escapes it
  as it escapes every value;
- **rich text** arrives escaped and formatted (`render_rich_text`), so it gets
  the escaped value, and only outside tags: an href is never touched.

Links, url and image fields are never substituted. An image's alt text is not
either: it describes the image, not the reader.
"""
import re

from markupsafe import Markup, escape

from app.expressions.rules import TOKEN, resolve

#: Field types whose values take entries.
TEXT_TYPES = ("text", "richtext")
_TAG = re.compile(r"(<[^>]*>)")


class Personal:
    """One render's entries: `values` {name: text} for this recipient, and,
    after rendering, which names were `used` and which were `missing` (no
    entry for this message's language)."""

    def __init__(self, values: dict[str, str]):
        self.values = values
        self.used: set[str] = set()
        self.missing: set[str] = set()

    def _value(self, match: re.Match) -> str | None:
        name = match.group(1)
        if name in self.values:
            self.used.add(name)
            return self.values[name]
        self.missing.add(name)
        return None

    def text(self, value: str) -> str:
        """A plain text, raw values in; escaping is the template's."""
        def put(match: re.Match) -> str:
            found = self._value(match)
            return match.group(0) if found is None else found
        return TOKEN.sub(put, value)

    def markup(self, value: Markup) -> Markup:
        """Rich text, already escaped and formatted: escaped values, outside tags only."""
        def put(match: re.Match) -> str:
            found = self._value(match)
            return match.group(0) if found is None else str(escape(found))
        parts = _TAG.split(str(value))
        return Markup("".join(part if part.startswith("<") else TOKEN.sub(put, part) for part in parts))

    def fields(self, variables: dict, manifest, *, skip: frozenset = frozenset()) -> dict:
        """Module or push fields with entries in: text and rich-text fields
        only, never an image's alt text."""
        if manifest is None:
            return variables
        alts = {v.alt for v in manifest.variables if getattr(v, "alt", None)}
        kinds = {v.name: v.type for v in manifest.variables}
        out = dict(variables)
        for name, value in variables.items():
            if kinds.get(name) not in TEXT_TYPES or name in alts or name in skip or not value:
                continue
            if isinstance(value, Markup):
                out[name] = self.markup(value)
            elif isinstance(value, str):
                out[name] = self.text(value)
        return out

    def recorded(self) -> dict[str, str]:
        """What a delivery record keeps: the values this render used."""
        return {name: self.values[name] for name in sorted(self.used)}


def resolve_all(entries: dict[str, dict], recipient: dict | None) -> dict[str, str]:
    """{name: text} for every entry, given each entry's spec in the message's
    language (`entries` {name: {cases, fallback}}) and a recipient's fields."""
    return {name: resolve(spec, recipient) for name, spec in entries.items()}


def recipient_fields(db, recipient_id: int | None) -> dict | None:
    """The fields a case may test, for one recipient; None for nobody."""
    if recipient_id is None:
        return None
    from app.recipients.db_models import RecipientDB

    row = db.get(RecipientDB, recipient_id)
    if row is None:
        return None
    return {"gender": row.gender, "first_name": row.first_name, "last_name": row.last_name}


def entries_in(db, brand_id: int, language: str) -> dict[str, dict]:
    """The brand's entries that have this language, as {name: spec}: what a
    frame freezes and what the live render uses. Reads without starting the
    dictionary, so a render never writes."""
    from app.expressions.service import entries_of

    return {e.name: e.languages[language] for e in entries_of(db, brand_id, start=False)
            if language in (e.languages or {})}


__all__ = ["Personal", "TEXT_TYPES", "entries_in", "recipient_fields", "resolve_all"]


#: The first frame version that freezes the entries (ADR-199). Frames before
#: it render without substitution, as they were sent.
EXPRESSION_FRAME_VERSION = 4


def message_language(db, variant) -> tuple[int, str]:
    """(brand id, language) of a variant's message: its brand profile's
    language (ADR-194 point 6), for email and push alike — a variant with no
    profile of its own uses the brand's default."""
    from app.brand_profiles.service import profile_of_variant
    from app.campaigns.db_models import CampaignDB

    brand_id = db.query(CampaignDB.brand_id).filter(CampaignDB.id == variant.campaign_id).scalar()
    return brand_id, profile_of_variant(db, variant, brand_id).language


def live_personal(db, variant_id: int, recipient_id: int | None) -> Personal:
    """For the editor's preview: today's entries, the profile's language as
    it is, and the recipient as they are — or the fallbacks for nobody."""
    from app.campaigns.db_models import VariantDB

    variant = db.get(VariantDB, variant_id)
    if variant is None:
        return Personal({})
    brand_id, language = message_language(db, variant)
    return Personal(resolve_all(entries_in(db, brand_id, language), recipient_fields(db, recipient_id)))


def frozen_entries(db, variant) -> dict:
    """What a frame freezes: the message's language and every entry that has it."""
    brand_id, language = message_language(db, variant)
    return {"language": language, "entries": entries_in(db, brand_id, language)}


def frame_personal(db, frame: dict, recipient_id: int | None, recorded: dict | None = None) -> Personal | None:
    """For a frame: the recorded values when rebuilding what was sent (never
    re-reading the recipient, ADR-183 point 7), otherwise resolved now from
    the frozen entries. None for a frame from before the entries were frozen."""
    frozen = frame.get("expressions")
    if frame.get("frame_version", 0) < EXPRESSION_FRAME_VERSION or frozen is None:
        return None
    if recorded is not None:
        return Personal(dict(recorded))
    return Personal(resolve_all(frozen.get("entries") or {}, recipient_fields(db, recipient_id)))
