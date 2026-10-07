"""Store every audience rule's category interest as a list of categories.

task-300, decided with the user 2026-10-06 (ADR-188's addendum of that date):
a rule's category interest takes several categories, each with its own score,
stored as `categories: [{category_id, min_score}, …]`. A rule saved before
holds the single pair `category_id` + `min_score`; this rewrites it to a
one-entry list. **Meaning unchanged** — one category is a list of one.

Each rewritten rule gets an audit entry by the system actor with the old and
new criteria, and the run prints how many there were. Idempotent and dry-run
by default; `--apply` commits.

    venv/bin/python scripts/migrate_0037_category_rules_take_a_list.py
    venv/bin/python scripts/migrate_0037_category_rules_take_a_list.py --apply
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.auth.db_models  # noqa: E402,F401
import app.campaigns.db_models  # noqa: E402,F401
from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB  # noqa: E402
from app.audit import service as audit  # noqa: E402
from app.database import SessionLocal  # noqa: E402


def _as_list(criteria: dict) -> dict | None:
    """The criteria with the old pair as a one-entry list, or None if there is no old pair."""
    if not criteria or ("category_id" not in criteria and "min_score" not in criteria):
        return None
    rest = {k: v for k, v in criteria.items() if k not in ("category_id", "min_score")}
    category = criteria.get("category_id")
    if category in (None, ""):
        return rest
    score = criteria.get("min_score")
    return {**rest, "categories": [{"category_id": int(category),
                                    "min_score": float(score) if score not in (None, "") else 1.0}]}


def fix(db, *, apply: bool) -> int:
    """Rewrite every rule holding the old pair; return how many."""
    changed = 0
    for block in db.query(AudienceRuleBlockDB).order_by(AudienceRuleBlockDB.id.asc()):
        after = _as_list(block.criteria or {})
        if after is None:
            continue
        changed += 1
        if apply:
            before = dict(block.criteria)
            block.criteria = after
            audit.record(db, audit.AUDIENCE_RULE_CHANGED, actor_type=audit.ACTOR_SYSTEM, actor_id=None,
                         subject_type="audience_group", subject_id=block.group_id,
                         brand_id=db.get(AudienceGroupDB, block.group_id).brand_id, commit=False,
                         detail={"block_id": block.id, "from": before, "to": after,
                                 "why": "migration 0037: category interest is a list (ADR-188 addendum 2026-10-06)"})
    if apply:
        db.commit()
    return changed


def main() -> int:
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        count = fix(db, apply=apply)
        print(f"{count} audience rule(s) held a single category"
              + ("; rewritten as a list." if apply else " (dry run; --apply to rewrite them)."))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
