"""A rule's category interest takes several categories, each with its own score (task-300).

Decided with the user on 2026-10-06, after the task-297 editor: "language de,
active, Nature ≥ 5 or Wellness ≥ 5" is ONE rule. ADR-188 point 1 already said
a field takes several values; its 2026-10-06 addendum applies that to
category interest — OR inside the field, a minimum score above 0 per category
(point 3, per category). Stored as `categories: [{category_id, min_score}]`;
the old single pair is still accepted and normalised. Suggested rules keep
one category each, so "Recalculate from campaign" stays per category.

Fixture, all agreed to email with this brand and speaking `TAG-de`:
  anna  Nature 6
  ben   Wellness 4
  cleo  Nature 2, Wellness 2
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audience import service as audience
from app.audience.db_models import AudienceGroupDB, AudienceRuleBlockDB
from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.campaigns.db_models import CampaignDB
from app.content.db_models import CategoryDB
from app.database import SessionLocal
from app.recipients.consent import record_consent
from app.recipients.db_models import ConsentEventDB, RecipientDB, SignalContributionDB
from main import app

TAG = f"ac{uuid.uuid4().hex[:6]}"
URL = "/api/audience-groups"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def world(db, default_brand):
    b = default_brand.id
    nature, wellness = CategoryDB(name=f"{TAG} Nature"), CategoryDB(name=f"{TAG} Wellness")
    db.add_all([nature, wellness]); db.flush()
    people = {}
    for name, signals in (("anna", {nature: 6.0}), ("ben", {wellness: 4.0}), ("cleo", {nature: 2.0, wellness: 2.0})):
        r = RecipientDB(external_id=f"{TAG}-{name}", status="active", language=f"{TAG}-de")
        db.add(r); db.flush()
        record_consent(db, r.id, "opted_in", b, channel="email", source="test", note="ac", commit=False,
                       purpose="marketing")
        for category, weight in signals.items():
            db.add(SignalContributionDB(recipient_id=r.id, category_id=category.id, contribution_type="manual",
                                        base_weight=weight))
        people[name] = r
    campaign = CampaignDB(brand_id=b, name=f"{TAG}-campaign")
    db.add(campaign); db.flush()
    group = AudienceGroupDB(brand_id=b, name=f"{TAG}-group", source_campaign_id=campaign.id)
    db.add(group); db.commit()
    yield {"group": group, "people": people, "brand": b, "nature": nature.id, "wellness": wellness.id,
           "campaign": campaign}
    db.rollback()
    ids = [r.id for r in people.values()]
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == "audience_group",
                                  AuditEventDB.subject_id == group.id).delete(synchronize_session=False)
    db.query(AudienceRuleBlockDB).filter_by(group_id=group.id).delete(synchronize_session=False)
    db.query(AudienceGroupDB).filter_by(id=group.id).delete(synchronize_session=False)
    db.query(CampaignDB).filter_by(id=campaign.id).delete(synchronize_session=False)
    db.query(SignalContributionDB).filter(SignalContributionDB.recipient_id.in_(ids)).delete(synchronize_session=False)
    db.query(ConsentEventDB).filter(ConsentEventDB.recipient_id.in_(ids)).delete(synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id.in_(ids)).delete(synchronize_session=False)
    db.query(CategoryDB).filter(CategoryDB.id.in_([nature.id, wellness.id])).delete(synchronize_session=False)
    db.commit()


@pytest.fixture
def person(db, default_brand):
    user = auth.create_user(db, email=f"{TAG}-{uuid.uuid4().hex[:6]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    yield client, {"X-CSRF-Token": auth.csrf_token_for(token)}
    db.rollback()
    db.execute(text("DELETE FROM audit_events WHERE actor_id = :u AND actor_type = 'user'"), {"u": user.id})
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


def _resolved(db, world) -> set[str]:
    names = {r.id: n for n, r in world["people"].items()}
    return {names[r.id] for r in audience.resolve_audience(db, world["group"].id, "email") if r.id in names}


def _rule(db, world, criteria, kind="include", **more):
    return audience.add_block(db, world["group"].id, kind=kind, criteria=criteria, brand_id=world["brand"], **more)


class TestSeveralCategories:
    def test_any_one_category_is_enough_each_with_its_own_score(self, db, world):
        n, w = world["nature"], world["wellness"]
        _rule(db, world, {"categories": [{"category_id": n, "min_score": 5}, {"category_id": w, "min_score": 3}]})
        assert _resolved(db, world) == {"anna", "ben"}, "cleo clears neither threshold"

    def test_the_score_is_per_category(self, db, world):
        n, w = world["nature"], world["wellness"]
        _rule(db, world, {"categories": [{"category_id": n, "min_score": 5}, {"category_id": w, "min_score": 5}]})
        assert _resolved(db, world) == {"anna"}, "ben's Wellness 4 is below this rule's Wellness 5"

    def test_the_other_fields_still_hold_for_every_category(self, db, world):
        """The user's case: the shared condition stays in the one rule."""
        db.query(RecipientDB).filter_by(id=world["people"]["ben"].id).update({"language": f"{TAG}-fr"}); db.commit()
        n, w = world["nature"], world["wellness"]
        _rule(db, world, {"language": [f"{TAG}-de"], "status": ["active"],
                          "categories": [{"category_id": n, "min_score": 5}, {"category_id": w, "min_score": 3}]})
        assert _resolved(db, world) == {"anna"}

    def test_the_count_and_the_arithmetic_read_the_same_rule(self, db, world):
        n, w = world["nature"], world["wellness"]
        block = _rule(db, world, {"categories": [{"category_id": n, "min_score": 5}, {"category_id": w, "min_score": 3}]})
        numbers = audience.audience_arithmetic(db, world["group"].id, "email")
        assert numbers["matched_rules"] >= 2
        preview = audience.preview_group(db, world["group"], channel="email")
        row = next(b for b in preview["blocks"] if b["id"] == block.id)
        assert row["category_name"] == f"{TAG} Nature or {TAG} Wellness"


class TestTheStoredShape:
    def test_the_old_single_pair_is_accepted_and_stored_as_a_list(self, db, world):
        block = _rule(db, world, {"category_id": world["nature"], "min_score": "5"})
        assert block.criteria == {"categories": [{"category_id": world["nature"], "min_score": 5.0}]}
        assert _resolved(db, world) == {"anna"}

    def test_a_rule_stored_in_the_old_shape_still_resolves(self, db, world):
        """Before the migration runs, or written around the service."""
        db.add(AudienceRuleBlockDB(group_id=world["group"].id, kind="include", source="manual",
                                   criteria={"category_id": world["wellness"], "min_score": 3.0}))
        db.commit()
        assert _resolved(db, world) == {"ben"}

    @pytest.mark.parametrize("criteria, field", [
        ({"categories": [{"category_id": 1}]}, "categories.0.min_score"),
        ({"categories": [{"category_id": 1, "min_score": 0}]}, "categories.0.min_score"),
        ({"categories": [{"category_id": 1, "min_score": 2}, {"category_id": 2, "min_score": -1}]}, "categories.1.min_score"),
        ({"categories": [{"min_score": 2}]}, "categories.0.category_id"),
        ({"categories": [{"category_id": "nature", "min_score": 2}]}, "categories.0.category_id"),
        ({"categories": [{"category_id": 1, "min_score": 2, "colour": "red"}]}, "categories.0.colour"),
        ({"categories": [{"category_id": 1, "min_score": 2}, {"category_id": 1, "min_score": 3}]}, "categories.1.category_id"),
        ({"categories": {"category_id": 1, "min_score": 2}}, "categories"),
        ({"categories": [{"category_id": 1, "min_score": 2}], "category_id": 2, "min_score": 1}, "category_id"),
    ])
    def test_a_category_list_that_does_not_say_something_meaningful_is_refused(self, criteria, field):
        with pytest.raises(audience.CriteriaInvalid) as refused:
            audience.normalise_criteria(criteria)
        assert field in [f for f, _ in refused.value.errors], refused.value.errors

    def test_an_empty_list_is_no_category_at_all(self):
        assert audience.normalise_criteria({"categories": []}) == {}

    def test_the_route_names_the_refused_entry(self, person, world):
        client, csrf = person
        response = client.post(f"{URL}/{world['group'].id}/blocks", headers=csrf, json={
            "kind": "include", "criteria": {"categories": [{"category_id": world["nature"], "min_score": 0}]}})
        assert response.status_code == 422, response.text
        assert response.json()["detail"][0]["loc"] == ["body", "criteria", "categories.0.min_score"]


class TestSuggestedRules:
    def test_a_suggestion_names_one_category(self, db, world, monkeypatch):
        monkeypatch.setattr(audience, "campaign_category_scores", lambda _db, _id: [
            {"category_id": world["nature"], "category_name": "Nature", "content_score": 9}])
        [suggestion] = audience.suggest_include_blocks_for_campaign(db, world["campaign"].id)
        assert suggestion["criteria"] == {"categories": [
            {"category_id": world["nature"], "min_score": audience.DEFAULT_SUGGESTION_MIN_SCORE}]}

    def test_recalculating_works_per_category_and_leaves_a_tuned_one(self, db, world, monkeypatch):
        n, w = world["nature"], world["wellness"]
        g = world["group"]
        tuned = AudienceRuleBlockDB(group_id=g.id, kind="include", source="suggested",
                                    criteria={"categories": [{"category_id": n, "min_score": 4.0}]})
        dropped = AudienceRuleBlockDB(group_id=g.id, kind="include", source="suggested",
                                      criteria={"category_id": 999_999, "min_score": 1.0})  # the old shape
        mine = AudienceRuleBlockDB(group_id=g.id, kind="include", source="manual",
                                   criteria={"categories": [{"category_id": 999_999, "min_score": 1.0}]})
        db.add_all([tuned, dropped, mine]); db.commit()
        monkeypatch.setattr(audience, "campaign_category_scores", lambda _db, _id: [
            {"category_id": n, "category_name": "Nature", "content_score": 9},
            {"category_id": w, "category_name": "Wellness", "content_score": 5}])
        audience.recalculate_suggested_blocks(db, g.id, brand_id=world["brand"])
        db.expire_all()
        rows = {(b.source, b.id): b.criteria for b in db.query(AudienceRuleBlockDB).filter_by(group_id=g.id)}
        assert rows[("suggested", tuned.id)] == {"categories": [{"category_id": n, "min_score": 4.0}]}, "kept as tuned"
        assert ("suggested", dropped.id) not in rows, "its category left the campaign"
        assert ("manual", mine.id) in rows, "a manager's own rule is never touched"
        added = [c for (source, i), c in rows.items() if source == "suggested" and i not in (tuned.id,)]
        assert added == [{"categories": [{"category_id": w, "min_score": audience.DEFAULT_SUGGESTION_MIN_SCORE}]}]


    def test_a_suggested_rule_the_manager_widened_is_theirs_now(self, db, world, monkeypatch):
        """A suggested rule given a second category was edited by hand: a
        recalculation neither removes it nor suggests its categories again."""
        n, w = world["nature"], world["wellness"]
        g = world["group"]
        widened = AudienceRuleBlockDB(group_id=g.id, kind="include", source="suggested", criteria={"categories": [
            {"category_id": n, "min_score": 1.0}, {"category_id": 999_999, "min_score": 2.0}]})
        db.add(widened); db.commit()
        monkeypatch.setattr(audience, "campaign_category_scores", lambda _db, _id: [
            {"category_id": n, "category_name": "Nature", "content_score": 9},
            {"category_id": w, "category_name": "Wellness", "content_score": 5}])
        audience.recalculate_suggested_blocks(db, g.id, brand_id=world["brand"])
        db.expire_all()
        rows = db.query(AudienceRuleBlockDB).filter_by(group_id=g.id).order_by(AudienceRuleBlockDB.id).all()
        assert [b.id for b in rows][0] == widened.id, "kept"
        assert [audience.category_terms(b.criteria) for b in rows[1:]] == [
            [(w, audience.DEFAULT_SUGGESTION_MIN_SCORE)]], "only Wellness is new; Nature is covered by the widened rule"


def test_the_migration_rewrites_the_old_pair_once_and_audits_it(db, world):
    from scripts import migrate_0037_category_rules_take_a_list as migration

    g = world["group"]
    old = AudienceRuleBlockDB(group_id=g.id, kind="include", source="manual",
                              criteria={"language": ["de"], "category_id": world["nature"], "min_score": 5.0})
    new = AudienceRuleBlockDB(group_id=g.id, kind="include", source="manual",
                              criteria={"categories": [{"category_id": world["wellness"], "min_score": 3.0}]})
    none = AudienceRuleBlockDB(group_id=g.id, kind="exclude", source="manual", criteria={"status": ["paused"]})
    db.add_all([old, new, none]); db.commit()
    assert migration.fix(db, apply=False) >= 1
    db.expire_all()
    assert db.get(AudienceRuleBlockDB, old.id).criteria["category_id"] == world["nature"], "a dry run changes nothing"
    assert migration.fix(db, apply=True) >= 1
    db.expire_all()
    assert db.get(AudienceRuleBlockDB, old.id).criteria == {
        "language": ["de"], "categories": [{"category_id": world["nature"], "min_score": 5.0}]}
    assert db.get(AudienceRuleBlockDB, new.id).criteria == {
        "categories": [{"category_id": world["wellness"], "min_score": 3.0}]}
    assert db.get(AudienceRuleBlockDB, none.id).criteria == {"status": ["paused"]}
    entries = db.query(AuditEventDB).filter(AuditEventDB.action == audit.AUDIENCE_RULE_CHANGED,
                                            AuditEventDB.subject_id == g.id).all()
    assert [e.detail["block_id"] for e in entries] == [old.id]
    assert migration.fix(db, apply=True) == 0, "running it again changes nothing"


def test_the_jinja_page_shows_several_categories_and_offers_no_form_that_would_drop_them(db, person, world):
    client, _ = person
    n, w = world["nature"], world["wellness"]
    several = _rule(db, world, {"categories": [{"category_id": n, "min_score": 5}, {"category_id": w, "min_score": 3}]},
                    label="Outdoors or spa")
    one = _rule(db, world, {"categories": [{"category_id": w, "min_score": 3}]}, label="Spa")
    page = client.get(f"/ui/audience-groups/{world['group'].id}").text
    assert f"interested in {TAG} Nature ≥ 5.0 or {TAG} Wellness ≥ 3.0" in page
    assert f"/blocks/{several.id}/edit" not in page
    assert "edited in the manager client" in page
    assert f"/blocks/{one.id}/edit" in page, "a one-category rule keeps its form"
    assert f'<option value="{w}" selected>' in page
