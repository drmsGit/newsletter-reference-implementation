"""What an expression entry may hold, and what it resolves to (task-365, ADR-199).

Pure functions, no database: the starter file, the API and rendering all use
them, so an entry means the same wherever it is read.

**Cases, not formulas.** An entry is, per language, an ordered list of cases
and a fallback. A case tests one recipient field (filled, empty, or equal to a
value) and gives a text; the first case that holds wins, otherwise the
fallback. Nothing is parsed as code. A case applies only when every recipient
field its text uses is filled, and the fallback uses none, so a salutation is
never "Hallo ,".
"""
import re

from app.recipients.service import GENDERS, PERSONAL_FIELDS

#: An entry's name: what a text writes between the braces.
NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
#: A {{name}} in a text. Spaces inside the braces are tolerated.
TOKEN = re.compile(r"\{\{\s*([a-z][a-z0-9_]*)\s*\}\}")
#: The language of a message: a brand profile's (ADR-194 point 6).
LANGUAGE = re.compile(r"[a-z]{2}(-[A-Z]{2})?")
OPERATORS = ("filled", "empty", "equals")
#: The recipient fields a case's text may print. Gender is tested, not printed.
PRINTABLE = ("first_name", "last_name")
MAX_TEXT = 500
MAX_CASES = 20


class EntryInvalid(ValueError):
    """What is wrong, as (location, message) pairs a form can mark."""

    def __init__(self, errors: list[tuple[tuple, str]]):
        self.errors = errors
        super().__init__("; ".join(message for _, message in errors))


def tokens(text: str | None) -> list[str]:
    """The names a text uses, in order."""
    return TOKEN.findall(text or "")


def check_name(name) -> str | None:
    if not isinstance(name, str) or not NAME.fullmatch(name):
        return "A name is lower-case letters, digits and _, starting with a letter."
    if name in PERSONAL_FIELDS:
        return f"{name} is a recipient field; an entry needs a name of its own."
    return None


def check_languages(languages) -> list[tuple[tuple, str]]:
    """Every problem with an entry's languages, empty when it is sound."""
    errors: list[tuple[tuple, str]] = []
    if not isinstance(languages, dict) or not languages:
        return [(("languages",), "An entry needs at least one language.")]
    for language, spec in languages.items():
        where = ("languages", language)
        if not isinstance(language, str) or not LANGUAGE.fullmatch(language):
            errors.append((where, f"{language!r} is not a language code like de or en-GB."))
            continue
        if not isinstance(spec, dict) or set(spec) - {"cases", "fallback"}:
            errors.append((where, "A language holds cases and a fallback, nothing else."))
            continue
        fallback = spec.get("fallback")
        if not isinstance(fallback, str) or not fallback.strip():
            errors.append((where + ("fallback",), "The fallback text is required."))
        elif len(fallback) > MAX_TEXT:
            errors.append((where + ("fallback",), f"The fallback is longer than {MAX_TEXT} characters."))
        elif tokens(fallback):
            errors.append((where + ("fallback",),
                           "The fallback is for recipients nothing is known about: it uses no {{…}}."))
        cases = spec.get("cases", [])
        if not isinstance(cases, list) or len(cases) > MAX_CASES:
            errors.append((where + ("cases",), f"Cases are a list of at most {MAX_CASES}."))
            continue
        for index, case in enumerate(cases):
            errors.extend(_check_case(case, where + ("cases", index)))
    return errors


def _check_case(case, where: tuple) -> list[tuple[tuple, str]]:
    if not isinstance(case, dict) or set(case) - {"field", "is", "value", "text"}:
        return [(where, "A case is a field, a test, maybe a value, and a text.")]
    errors = []
    field, test, text = case.get("field"), case.get("is"), case.get("text")
    if field not in PERSONAL_FIELDS:
        errors.append((where + ("field",), f"The field is one of {', '.join(PERSONAL_FIELDS)}."))
    if test not in OPERATORS:
        errors.append((where + ("is",), f"The test is one of {', '.join(OPERATORS)}."))
    if test == "equals":
        value = case.get("value")
        if not isinstance(value, str) or not value.strip():
            errors.append((where + ("value",), "Equals needs a value."))
        elif field == "gender" and value not in GENDERS:
            errors.append((where + ("value",), f"Gender is one of {', '.join(GENDERS)}."))
    elif "value" in case:
        errors.append((where + ("value",), "Only equals takes a value."))
    if not isinstance(text, str) or not text.strip():
        errors.append((where + ("text",), "Each case needs a text."))
    elif len(text) > MAX_TEXT:
        errors.append((where + ("text",), f"The text is longer than {MAX_TEXT} characters."))
    else:
        unknown = [name for name in tokens(text) if name not in PRINTABLE]
        if unknown:
            errors.append((where + ("text",), f"A case's text may use {{{{first_name}}}} and "
                           f"{{{{last_name}}}} only, not {', '.join(sorted(set(unknown)))}."))
    return errors


def check_entry(name, label, languages, *, name_given: bool = True) -> None:
    """Raise EntryInvalid when the entry cannot be stored."""
    errors: list[tuple[tuple, str]] = []
    if name_given and (problem := check_name(name)):
        errors.append((("name",), problem))
    if not isinstance(label, str) or not label.strip() or len(label) > 200:
        errors.append((("label",), "A label of up to 200 characters is required."))
    errors.extend(check_languages(languages))
    if errors:
        raise EntryInvalid(errors)


def _holds(case: dict, recipient: dict) -> bool:
    value = (recipient.get(case["field"]) or "").strip()
    if case["is"] == "filled" and not value:
        return False
    if case["is"] == "empty" and value:
        return False
    if case["is"] == "equals" and value != case.get("value"):
        return False
    # The filled-fields rule (ADR-199): a case whose text prints an empty
    # field does not apply.
    return all((recipient.get(name) or "").strip() for name in tokens(case["text"]))


def resolve(spec: dict, recipient: dict | None) -> str:
    """One language of one entry, for one recipient (None: nobody known, the
    fallback). Recipient values are inserted raw: escaping is the renderer's."""
    for case in spec.get("cases", []) if recipient else []:
        if _holds(case, recipient):
            return TOKEN.sub(lambda m: (recipient.get(m.group(1)) or "").strip(), case["text"])
    return spec["fallback"]
