"""Give every audience rule that names a category without a score the default 1.0.

task-295, decided with the user 2026-10-06 (ADR-188 point 3; Audience Write
Surface final design pass): interest in a category always carries a minimum
score above 0. A rule saved before that rule existed, with a category and no
score (or a score of 0 or less), matched nearly everyone — every recipient's
signal is at least 0 unless they unsubscribed. It now means what it says:
people with real interest, at the default suggested rules use.

**Changes meaning on purpose, and says so.** Each changed rule gets an audit
entry by the system actor with the old and new criteria, and the run prints
how many there were, so the size of the change is visible rather than silent.

Idempotent and dry-run by default; `--apply` commits.

    venv/bin/python scripts/migrate_0035_category_rules_get_a_score.py
    venv/bin/python scripts/migrate_0035_category_rules_get_a_score.py --apply
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.auth.db_models  # noqa: E402,F401
import app.campaigns.db_models  # noqa: E402,F401
from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB  # noqa: E402
from app.audit import service as audit  # noqa: E402
from app.database import SessionLocal  # noqa: E402

DEFAULT_SCORE = 1.0


def _scoreless(criteria: dict) -> bool:
    if (criteria or {}).get("category_id") in (None, ""):
        return False
    score = criteria.get("min_score")
    try:
        return score in (None, "") or float(score) <= 0
    except (TypeError, ValueError):
        return True


def fix(db, *, apply: bool) -> int:
    """Set the default score on every scoreless category rule; return how many."""
    changed = 0
    for block in db.query(AudienceRuleBlockDB).order_by(AudienceRuleBlockDB.id.asc()):
        if not _scoreless(block.criteria or {}):
            continue
        changed += 1
        if apply:
            before = dict(block.criteria)
            block.criteria = {**before, "min_score": DEFAULT_SCORE}
            audit.record(db, audit.AUDIENCE_RULE_CHANGED, actor_type=audit.ACTOR_SYSTEM, actor_id=None,
                         subject_type="audience_group", subject_id=block.group_id,
                         brand_id=db.get(AudienceGroupDB, block.group_id).brand_id, commit=False,
                         detail={"block_id": block.id, "from": before, "to": block.criteria,
                                 "why": "migration 0035: a category rule needs a score (ADR-188 point 3)"})
    if apply:
        db.commit()
    return changed


def main() -> int:
    apply = "--apply" in sys.argv
    db = SessionLocal()
    try:
        count = fix(db, apply=apply)
        print(f"{count} audience rule(s) named a category without a score"
              + (f"; set to {DEFAULT_SCORE}." if apply else " (dry run; --apply to set them)."))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
