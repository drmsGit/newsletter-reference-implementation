"""The starter entries, from `storage/expressions.json` (task-365, ADR-199).

Loaded like `storage/brand_profile.json` (`app/brand_profiles/structure.py`):
read again when the file changes, unknown keys refused, and checked at startup
so a bad file fails the deploy rather than the first brand that opens its
dictionary. The file is the installation's: it may change or empty the
starters. A brand copies them once (`service.entries_of`) and owns its copy.
"""
import json
from pathlib import Path

from app.expressions.rules import EntryInvalid, check_entry

STARTERS_PATH = Path(__file__).parent.parent.parent.parent / "storage" / "expressions.json"

_loaded: dict[str, dict] = {}
_loaded_mtime: float | None = None


def _read() -> dict[str, dict]:
    if not STARTERS_PATH.exists():
        return {}
    try:
        document = json.loads(STARTERS_PATH.read_text())
    except json.JSONDecodeError as error:
        raise ValueError(f"{STARTERS_PATH} is not valid JSON: {error}") from error
    unknown = sorted(set(document) - {"_comment", "entries"})
    if unknown:
        raise ValueError(f"{STARTERS_PATH} declares {', '.join(map(repr, unknown))} (unknown — a typo?).")
    entries = document.get("entries") or {}
    if not isinstance(entries, dict):
        raise ValueError(f"{STARTERS_PATH}: 'entries' must be an object of name to entry.")
    for name, entry in entries.items():
        if not isinstance(entry, dict) or set(entry) - {"label", "languages"}:
            raise ValueError(f"{STARTERS_PATH}: entry {name!r} holds a label and languages, nothing else.")
        try:
            check_entry(name, entry.get("label"), entry.get("languages"))
        except EntryInvalid as error:
            raise ValueError(f"{STARTERS_PATH}: entry {name!r}: {error}") from error
    return entries


def starters() -> dict[str, dict]:
    """{name: {"label", "languages"}}, as the file holds them now."""
    global _loaded, _loaded_mtime
    current = STARTERS_PATH.stat().st_mtime if STARTERS_PATH.exists() else 0.0
    if _loaded_mtime is None or current != _loaded_mtime:
        _loaded = _read()
        _loaded_mtime = current
    return _loaded


def assert_starters_load() -> None:
    """Read the file at startup, so a bad one fails the deploy."""
    global _loaded_mtime
    _loaded_mtime = None
    starters()
