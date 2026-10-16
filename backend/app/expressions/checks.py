"""What a text may hold of the dictionary, checked when it is saved (task-365, ADR-199).

A text uses entries only, by name: {{salutation_formal}}. Refused on save:
- a name the brand's dictionary does not have;
- a recipient field written directly ({{first_name}}): it belongs inside an
  entry, where a fallback covers the recipient it is empty for;
- any {{…}} in a link, an image address or an image's alt text, and in the
  target of a rich-text link: those never take entries.

Only a value that changes is judged, as images are (`refuse_bad_images`): a
text stored before this rule stays editable in its other fields.
"""
import re

from sqlalchemy.orm import Session

from app.expressions.rules import tokens
from app.recipients.service import PERSONAL_FIELDS

_LINK_TARGET = re.compile(r"\]\([^)]*\{\{")


def text_problems(db: Session, brand_id: int, values: dict | None, kinds: dict[str, str],
                  *, alts: frozenset[str] = frozenset(), previous: dict | None = None) -> list[tuple[str, str]]:
    """(field, why) for every changed value that may not hold what it holds.
    `kinds` is {field: type} from fields.json; `alts` the fields that hold an
    image's alt text."""
    previous = previous or {}
    known: set[str] | None = None
    problems = []
    for name, value in (values or {}).items():
        if not isinstance(value, str) or value == previous.get(name):
            continue
        used = tokens(value)
        if not used:
            continue
        kind = kinds.get(name, "text")
        if kind in ("url", "image") or name in alts:
            problems.append((name, "Personalisation does not work in a link, an image address or alt text."))
            continue
        if kind == "richtext" and _LINK_TARGET.search(value):
            problems.append((name, "Personalisation does not work in a link's address; put it in the link text."))
            continue
        direct = sorted({n for n in used if n in PERSONAL_FIELDS})
        if direct:
            problems.append((name, f"{{{{{direct[0]}}}}} is a recipient field; use an entry such as "
                                   "{{salutation_informal}}, which has a text for when it is empty."))
            continue
        if known is None:
            from app.expressions.service import by_name

            known = set(by_name(db, brand_id))
        unknown = sorted({n for n in used if n not in known})
        if unknown:
            names = ", ".join("{{" + n + "}}" for n in unknown)
            problems.append((name, f"{names} is not in this brand's dictionary (Settings, Personalisation)."))
    return problems


def kinds_of(manifest) -> tuple[dict[str, str], frozenset[str]]:
    """({field: type}, alt fields) of a module manifest."""
    if manifest is None:
        return {}, frozenset()
    return ({v.name: v.type for v in manifest.variables},
            frozenset(v.alt for v in manifest.variables if getattr(v, "alt", None)))


def content_kinds() -> tuple[dict[str, str], frozenset[str]]:
    """({field: type}, alt fields) of every field a content record holds."""
    from app.modules.registry import field_definitions

    definitions = field_definitions()
    return ({name: spec.get("type", "text") for name, spec in definitions.items()},
            frozenset(spec["alt"] for spec in definitions.values() if spec.get("alt")))
