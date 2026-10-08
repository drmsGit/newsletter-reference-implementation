"""The AI modes are named by what they do (task-97; ADR-140 addendum 2026-10-08).

"Mode A" collided with the roadmap's "Phase 4A" and misread a planning session.
The modes are Assistive (was A, ADR-141), Autonomous (was B, ADR-142) and
Development (was C, ADR-143). Dated records — every ADR among them — keep the
letters they were written with (the user's rule of 2026-10-05), and ADR-140's
addendum is the key. Living files use the names, and this keeps them there:
every ADR still says "Mode A", so the letters return whenever something is
copied from one.

Same scan as the product name's guard (`scripts/rename_product.py`): tracked
text files, dated records and ADR links aside.
"""
import re
from pathlib import Path

from scripts import rename_product

ROOT = Path(__file__).resolve().parents[2]

#: "Mode A", "Mode-A", "Mode A/B/C", "Modes A and B", "Mode-A-vs-…" — not
#: "Mode Boundary" or a lower-case "mode" in ordinary prose.
LETTERED = re.compile(r"\bModes?[ -][ABC](?![a-zA-Z])")


def lettered_mode_hits(root: Path) -> list[str]:
    hits = []
    for path in rename_product.tracked(root):
        if rename_product.is_dated(path) or path.suffix not in rename_product.TEXT:
            continue
        if not (root / path).is_file():
            continue
        for number, line in enumerate((root / path).read_text(errors="ignore").splitlines(), 1):
            if LETTERED.search(rename_product.ADR_LINK.sub("", line)):
                hits.append(f"{path}:{number}: {line.strip()[:120]}")
    return hits


def test_the_pattern_catches_every_spelling_and_nothing_else():
    for lettered in ("Mode A", "the Mode-A task", "Mode A/B/C", "Modes A and B", "Mode-A-vs-slot", "Mode C."):
        assert LETTERED.search(lettered), lettered
    for plain in ("Mode Boundary", "mode A", "Model A", "the Assistive mode", "ModeA"):
        assert not LETTERED.search(plain), plain


def test_living_files_name_the_modes_by_function():
    hits = lettered_mode_hits(ROOT)
    assert hits == [], (
        "a lettered AI mode in a living file — say Assistive / Autonomous / Development "
        "(ADR-140 addendum 2026-10-08):\n" + "\n".join(hits))
