"""Transactional rule blocks share the send's purpose (ADR-195, ADR-176)."""
import pytest

from app.audience.db_models import AudienceGroupMemberDB, AudienceRuleBlockDB
from app.audience.service import add_block
from tests.test_transactional import _executions, _plan
from tests.test_transactional import db, drop_test_profiles, world  # noqa: F401


@pytest.fixture
def rule_world(db, world):  # noqa: F811
    yield world
    db.rollback()
    db.query(AudienceRuleBlockDB).filter_by(group_id=world["group"].id).delete()
    db.commit()


def test_transactional_include_rules_do_not_require_marketing_consent(db, rule_world):  # noqa: F811
    data = rule_world
    # The existing send fixture pins everyone. Remove pins so this exercises
    # rule-driven selection, not the path covered by the original tests.
    db.query(AudienceGroupMemberDB).filter_by(group_id=data["group"].id).delete()
    db.commit()
    for person in data["people"].values():
        person.language = "zz-codex"
    db.commit()
    add_block(db, data["group"].id, kind="include", criteria={"language": "zz-codex"},
              brand_id=data["brand"].id)

    planned = _executions(db, _plan(db, data))
    people = data["people"]
    assert set(planned) == {people["none"].id, people["crm_out"].id, people["opted_in"].id}
    assert people["bounced"].id not in planned
    assert {row.purpose for row in planned.values()} == {"transactional"}


def test_transactional_exclude_rules_still_remove_a_non_opted_in_pin(db, rule_world):  # noqa: F811
    data = rule_world
    people = data["people"]
    for name, person in people.items():
        person.language = "de" if name == "none" else "en"
    db.commit()
    add_block(db, data["group"].id, kind="exclude", criteria={"language": "de"},
              brand_id=data["brand"].id)

    planned = _executions(db, _plan(db, data))
    assert set(planned) == {people["crm_out"].id, people["opted_in"].id}, (
        "an explicit exclusion must beat a pin even without a marketing grant")
