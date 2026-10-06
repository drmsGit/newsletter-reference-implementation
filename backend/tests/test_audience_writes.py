"""Audience writes: one version, audit, validated rules, safe delete, hand-add
reasons, paste (task-295).

Decided with the user on 2026-10-06 (task-293): [[Audience Write Surface - final design pass]]
and ADR-188. One version for the whole group — any write to it, its rules or
its members moves it, and every write states it (ADR-180 point 2); every write
is audited (ADR-153 point 4); rules are validated (a category always with a
score above 0, unknown fields refused, language and status as lists); a group
a send uses cannot be deleted; a hand-add carries an optional reason and who
added it; a list of people can be pasted, with a report first.
"""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.audience import service as audience
from app.audience.db_models import AudienceGroupDB, AudienceGroupMemberDB, AudienceRuleBlockDB
from app.audit import service as audit
from app.audit.db_models import AuditEventDB
from app.auth import service as auth
from app.database import SessionLocal
from app.delivery.db_models import SendInstanceDB
from app.recipients.consent import record_consent
from app.recipients.db_models import AddressabilityDB, ConsentEventDB, RecipientDB
from main import app

TAG = f"aw{uuid.uuid4().hex[:6]}"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def person(db, default_brand):
    user = auth.create_user(db, email=f"{TAG}-{uuid.uuid4().hex[:6]}@example.invalid",
                            role_key="admin", brand_id=default_brand.id)
    token = auth.create_session(db, user)
    client = TestClient(app, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    yield client, {"X-CSRF-Token": auth.csrf_token_for(token)}, user
    db.rollback()
    db.execute(text("DELETE FROM audit_events WHERE actor_id = :u AND actor_type = 'user'"), {"u": user.id})
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


@pytest.fixture
def world(db, default_brand):
    """A group and three people known to the brand: Anna (agreed to email, an
    address), Ben (agreed), Cleo (opted out)."""
    b = default_brand.id
    people = {}
    for name, consent in (("anna", "opted_in"), ("ben", "opted_in"), ("cleo", "opted_out")):
        r = RecipientDB(external_id=f"{TAG}-{name}", status="active", language=f"{TAG}-de")
        db.add(r); db.flush()
        record_consent(db, r.id, consent, b, channel="email", source="test", note="aw", commit=False,
                       purpose="marketing")
        db.add(AddressabilityDB(recipient_id=r.id, channel="email", value={"email": f"{name}.{TAG}@example.invalid"},
                                status="active", is_primary=True))
        people[name] = r
    group = AudienceGroupDB(brand_id=b, name=f"{TAG}-group")
    db.add(group); db.commit()
    groups = [group.id]
    yield {"group": group, "people": people, "brand": b, "groups": groups}
    db.rollback()
    db.query(SendInstanceDB).filter(SendInstanceDB.audience_group_id.in_(groups)).delete(synchronize_session=False)
    db.query(AuditEventDB).filter(AuditEventDB.subject_type == "audience_group",
                                  AuditEventDB.subject_id.in_(groups)).delete(synchronize_session=False)
    db.query(AudienceRuleBlockDB).filter(AudienceRuleBlockDB.group_id.in_(groups)).delete(synchronize_session=False)
    db.query(AudienceGroupMemberDB).filter(AudienceGroupMemberDB.group_id.in_(groups)).delete(synchronize_session=False)
    db.query(AudienceGroupDB).filter(AudienceGroupDB.id.in_(groups)).delete(synchronize_session=False)
    ids = [r.id for r in people.values()]
    for model in (AddressabilityDB, ConsentEventDB):
        db.query(model).filter(model.recipient_id.in_(ids)).delete(synchronize_session=False)
    db.query(RecipientDB).filter(RecipientDB.id.in_(ids)).delete(synchronize_session=False)
    db.commit()


def _version(db, group_id):
    db.expire_all()
    return db.get(AudienceGroupDB, group_id).updated_at.isoformat()


def _entries(db, action, group_id):
    return db.query(AuditEventDB).filter(AuditEventDB.action == action, AuditEventDB.subject_id == group_id).all()


URL = "/api/audience-groups"


class TestOneVersionAndAudit:
    def test_creating_a_group_is_audited(self, db, person, world):
        client, csrf, _ = person
        response = client.post(f"{URL}/", json={"name": f"{TAG}-new", "description": "Spring"}, headers=csrf)
        assert response.status_code == 201, response.text
        world["groups"].append(response.json()["id"])
        [entry] = _entries(db, audit.AUDIENCE_GROUP_CREATED, response.json()["id"])
        assert entry.detail["name"] == f"{TAG}-new"

    def test_a_rename_changes_only_what_is_sent_and_states_the_version(self, db, person, world):
        client, csrf, _ = person
        g = world["group"]
        db.query(AudienceGroupDB).filter_by(id=g.id).update({"description": "Keep me"}); db.commit()
        response = client.patch(f"{URL}/{g.id}", json={"name": f"{TAG}-renamed"},
                                headers={**csrf, "If-Match": _version(db, g.id)})
        assert response.status_code == 200, response.text
        assert (response.json()["name"], response.json()["description"]) == (f"{TAG}-renamed", "Keep me")
        cleared = client.patch(f"{URL}/{g.id}", json={"description": None},
                               headers={**csrf, "If-Match": _version(db, g.id)})
        assert cleared.json()["description"] is None
        assert len(_entries(db, audit.AUDIENCE_GROUP_UPDATED, g.id)) == 2

    def test_a_stale_version_is_refused_on_every_kind_of_write(self, db, person, world):
        client, csrf, _ = person
        g, stale = world["group"], {**csrf, "If-Match": "2020-01-01T00:00:00+00:00"}
        anna = world["people"]["anna"]
        assert client.patch(f"{URL}/{g.id}", json={"name": "x"}, headers=stale).status_code == 409
        assert client.post(f"{URL}/{g.id}/blocks", json={"kind": "include", "criteria": {}}, headers=stale).status_code == 409
        assert client.post(f"{URL}/{g.id}/members/{anna.id}", json={}, headers=stale).status_code == 409
        assert client.delete(f"{URL}/{g.id}", headers=stale).status_code == 409

    def test_a_rule_or_member_write_moves_the_groups_version_and_is_audited(self, db, person, world):
        client, csrf, _ = person
        g = world["group"]
        before = _version(db, g.id)
        added = client.post(f"{URL}/{g.id}/blocks", json={"kind": "include", "criteria": {"language": [f"{TAG}-de"]},
                                                          "label": "German"}, headers={**csrf, "If-Match": before})
        assert added.status_code == 201, added.text
        after_rule = _version(db, g.id)
        assert after_rule != before
        block = added.json()["id"]
        changed = client.patch(f"{URL}/{g.id}/blocks/{block}", json={"label": None},
                               headers={**csrf, "If-Match": after_rule})
        assert changed.status_code == 200 and changed.json()["label"] is None, "a label can be cleared"
        removed = client.delete(f"{URL}/{g.id}/blocks/{block}", headers={**csrf, "If-Match": _version(db, g.id)})
        assert removed.status_code == 204
        for action in (audit.AUDIENCE_RULE_ADDED, audit.AUDIENCE_RULE_CHANGED, audit.AUDIENCE_RULE_REMOVED):
            assert len(_entries(db, action, g.id)) == 1, action


class TestRules:
    @pytest.mark.parametrize("criteria, field", [
        ({"colour": ["red"]}, "colour"),
        ({"category_id": 1}, "min_score"),
        ({"category_id": 1, "min_score": 0}, "min_score"),
        ({"category_id": 1, "min_score": -2}, "min_score"),
        ({"min_score": 2}, "category_id"),
    ])
    def test_a_rule_that_does_not_say_something_meaningful_is_refused_by_field(self, db, person, world, criteria, field):
        client, csrf, _ = person
        response = client.post(f"{URL}/{world['group'].id}/blocks", json={"kind": "include", "criteria": criteria},
                               headers=csrf)
        assert response.status_code == 422, response.text
        assert field in response.text
        assert db.query(AudienceRuleBlockDB).filter_by(group_id=world["group"].id).count() == 0

    def test_language_and_status_take_several_values(self, db, world):
        g = world["group"]
        # Ben speaks the second language listed, so "is one of" must read both values.
        db.query(RecipientDB).filter_by(id=world["people"]["ben"].id).update({"language": f"{TAG}-fr"}); db.commit()
        audience.add_block(db, g.id, kind="include", criteria={"language": [f"{TAG}-de", f"{TAG}-fr"]},
                           brand_id=world["brand"])
        resolved = {r.id for r in audience.resolve_audience(db, g.id, "email")}
        assert resolved == {world["people"]["anna"].id, world["people"]["ben"].id}

    def test_a_single_value_from_an_older_rule_still_works(self, db, world):
        g = world["group"]
        db.add(AudienceRuleBlockDB(group_id=g.id, kind="include", criteria={"language": f"{TAG}-de"}, source="manual"))
        db.commit()
        assert len(audience.resolve_audience(db, g.id, "email")) == 2


class TestDelete:
    def test_a_group_a_send_uses_is_refused_naming_the_send(self, db, person, world):
        client, csrf, _ = person
        g = world["group"]
        from app.snapshots.db_models import SnapshotDB

        snapshot = db.query(SnapshotDB.id).first()[0]  # any: the seed has some
        db.add(SendInstanceDB(name=f"{TAG} spring send", status="draft", brand_id=world["brand"],
                              audience_group_id=g.id, provider="mock", snapshot_id=snapshot))
        db.commit()
        response = client.delete(f"{URL}/{g.id}", headers=csrf)
        assert response.status_code == 409
        assert f"{TAG} spring send" in response.text
        assert db.get(AudienceGroupDB, g.id) is not None

    def test_an_unused_group_is_deleted_and_audited(self, db, person, world):
        client, csrf, _ = person
        gid = world["group"].id
        assert client.delete(f"{URL}/{gid}", headers=csrf).status_code == 204
        db.expire_all()
        assert db.query(AudienceGroupDB).filter_by(id=gid).first() is None
        assert len(_entries(db, audit.AUDIENCE_GROUP_DELETED, gid)) == 1


class TestHandAdds:
    def test_a_hand_add_records_its_reason_and_who_added_it(self, db, person, world):
        client, csrf, user = person
        g, anna = world["group"], world["people"]["anna"]
        response = client.post(f"{URL}/{g.id}/members/{anna.id}", json={"reason": "Asked for this mailing"},
                               headers=csrf)
        assert response.status_code == 201, response.text
        assert (response.json()["reason"], response.json()["added_by"]) == ("Asked for this mailing", user.email)
        [entry] = _entries(db, audit.AUDIENCE_MEMBER_ADDED, g.id)
        assert entry.detail == {"recipient_id": anna.id, "reason": "Asked for this mailing"}
        assert client.delete(f"{URL}/{g.id}/members/{anna.id}", headers=csrf).status_code == 204
        assert len(_entries(db, audit.AUDIENCE_MEMBER_REMOVED, g.id)) == 1

    def test_a_reason_is_optional(self, db, person, world):
        client, csrf, _ = person
        response = client.post(f"{URL}/{world['group'].id}/members/{world['people']['ben'].id}", headers=csrf)
        assert response.status_code == 201 and response.json()["reason"] is None


class TestPastePeople:
    def _text(self, world):
        p = world["people"]
        return (f"{p['anna'].external_id}, ben.{TAG}@example.invalid;{p['cleo'].external_id}\n"
                f"nobody-{TAG}\t{p['anna'].external_id}")

    def test_the_preview_reports_before_anything_is_added(self, db, person, world):
        client, csrf, _ = person
        g = world["group"]
        db.add(AudienceGroupMemberDB(group_id=g.id, recipient_id=world["people"]["anna"].id)); db.commit()
        response = client.post(f"{URL}/{g.id}/members/paste-preview",
                               json={"text": self._text(world), "channel": "email"}, headers=csrf)
        assert response.status_code == 200, response.text
        body = response.json()
        assert (body["to_add"], body["already_in"], body["not_found"], body["not_agreed"]) == (
            2, 1, [f"nobody-{TAG}"], 1)
        assert db.query(AudienceGroupMemberDB).filter_by(group_id=g.id).count() == 1, "a preview adds nobody"

    def test_applying_adds_them_with_the_reason_creates_nobody_and_is_audited(self, db, person, world):
        client, csrf, _ = person
        g = world["group"]
        recipients_before = db.query(RecipientDB).count()
        response = client.post(f"{URL}/{g.id}/members/paste", json={"text": self._text(world), "reason": "Sales list"},
                               headers={**csrf, "If-Match": _version(db, g.id)})
        assert response.status_code == 200, response.text
        assert response.json()["added"] == 3
        rows = db.query(AudienceGroupMemberDB).filter_by(group_id=g.id).all()
        assert {r.reason for r in rows} == {"Sales list"}
        assert db.query(RecipientDB).count() == recipients_before
        [entry] = _entries(db, audit.AUDIENCE_PEOPLE_PASTED, g.id)
        assert (entry.detail["added"], entry.detail["not_found"]) == (3, 1)

    def test_more_than_five_thousand_is_refused(self, person, world):
        client, csrf, _ = person
        text_ = "\n".join(f"x{i}" for i in range(5001))
        response = client.post(f"{URL}/{world['group'].id}/members/paste-preview",
                               json={"text": text_, "channel": "email"}, headers=csrf)
        assert response.status_code == 422
        assert "5,000" in response.text or "5000" in response.text


def test_the_values_a_rule_can_choose_from(person, world):
    client, _, _ = person
    body = client.get(f"{URL}/criteria-values").json()
    assert f"{TAG}-de" in body["languages"]
    assert "active" in body["statuses"]


def test_the_migration_gives_scoreless_category_rules_a_score_once(db, world):
    from scripts import migrate_0035_category_rules_get_a_score as migration

    g = world["group"]
    db.add_all([
        AudienceRuleBlockDB(group_id=g.id, kind="include", criteria={"category_id": 1}, source="manual"),
        AudienceRuleBlockDB(group_id=g.id, kind="include", criteria={"category_id": 2, "min_score": 0}, source="manual"),
        AudienceRuleBlockDB(group_id=g.id, kind="include", criteria={"category_id": 3, "min_score": 2.5}, source="manual"),
    ])
    db.commit()
    assert migration.fix(db, apply=True) >= 2
    db.expire_all()
    scores = sorted(b.criteria["min_score"] for b in db.query(AudienceRuleBlockDB).filter_by(group_id=g.id))
    assert scores == [1.0, 1.0, 2.5]
    assert len(_entries(db, audit.AUDIENCE_RULE_CHANGED, g.id)) == 2
    assert migration.fix(db, apply=True) == 0, "running it again changes nothing"


class TestTheJinjaForms:
    """The same audit entries on the Jinja plane, and a readable refusal where
    deleting a used group used to fail in the database."""

    def test_a_rule_and_a_hand_add_are_audited_and_a_used_group_is_not_deleted(self, db, person, world):
        client, _, user = person
        token = client.cookies.get(auth.SESSION_COOKIE)
        form = {"csrf_token": auth.csrf_token_for(token)}
        g = world["group"]
        client.post(f"/ui/audience-groups/{g.id}/blocks", data={**form, "kind": "include", "language": f"{TAG}-de"},
                    follow_redirects=False)
        client.post(f"/ui/audience-groups/{g.id}/members", data={**form, "recipient_id": world["people"]["anna"].id},
                    follow_redirects=False)
        assert len(_entries(db, audit.AUDIENCE_RULE_ADDED, g.id)) == 1
        [added] = _entries(db, audit.AUDIENCE_MEMBER_ADDED, g.id)
        db.expire_all()
        assert db.query(AudienceGroupMemberDB).filter_by(group_id=g.id).one().added_by == user.email

        from app.snapshots.db_models import SnapshotDB

        db.add(SendInstanceDB(name=f"{TAG} planned", status="draft", brand_id=world["brand"], audience_group_id=g.id,
                              provider="mock", snapshot_id=db.query(SnapshotDB.id).first()[0]))
        db.commit()
        response = client.post(f"/ui/audience-groups/{g.id}/delete", data=form, follow_redirects=False)
        assert response.status_code == 303 and "Used%20by%201%20send" in response.headers["location"]
        db.expire_all()
        assert db.query(AudienceGroupDB).filter_by(id=g.id).first() is not None


def test_the_members_list_names_each_person_and_who_an_exclusion_leaves_out(db, person, world):
    """The editor's hand-added list (task-297): who, reason, who added them, and
    the exclusion rules that leave a hand-added person out on the channel."""
    client, csrf, user = person
    g, anna, ben = world["group"], world["people"]["anna"], world["people"]["ben"]
    client.post(f"{URL}/{g.id}/members/{anna.id}", json={"reason": "VIP"}, headers=csrf)
    client.post(f"{URL}/{g.id}/members/{ben.id}", headers=csrf)
    db.query(RecipientDB).filter_by(id=ben.id).update({"status": "paused"}); db.commit()
    audience.add_block(db, g.id, kind="exclude", criteria={"status": ["paused"]}, label="Paused", brand_id=world["brand"])
    body = client.get(f"{URL}/{g.id}/members", params={"channel": "email"}).json()
    rows = {m["recipient_id"]: m for m in body["items"]}
    assert (rows[anna.id]["external_id"], rows[anna.id]["reason"], rows[anna.id]["added_by"]) == (
        anna.external_id, "VIP", user.email)
    assert (rows[anna.id]["left_out_by"], rows[ben.id]["left_out_by"]) == ([], ["Paused"])
    plain = client.get(f"{URL}/{g.id}/members").json()["items"]
    assert all(m["left_out_by"] == [] for m in plain), "no channel, no exclusion verdict"
