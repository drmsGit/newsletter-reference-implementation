"""The shared taxonomy's writes (task-359).

A category is renamed or changes type through PATCH, which did not exist; a
type is main or sub; and every category write is in the audit log, as
content's category assignments already were.
"""
import uuid

import pytest

from app.audit.db_models import AuditEventDB
from app.content.db_models import CategoryDB, CategoryRelationDB
from tests.test_api_guard import signed_in


@pytest.fixture
def db():
    from app.database import SessionLocal

    session = SessionLocal()
    yield session
    session.rollback()
    ids = [c.id for c in session.query(CategoryDB).filter(CategoryDB.name.like("t359-%"))]
    session.query(AuditEventDB).filter(AuditEventDB.subject_type == "category",
                                       AuditEventDB.subject_id.in_(ids)).delete(synchronize_session=False)
    session.query(CategoryRelationDB).filter(CategoryRelationDB.parent_category_id.in_(ids)
                                             | CategoryRelationDB.child_category_id.in_(ids)).delete(
        synchronize_session=False)
    session.query(CategoryDB).filter(CategoryDB.id.in_(ids)).delete(synchronize_session=False)
    session.commit()
    session.close()


def _name() -> str:
    return f"t359-{uuid.uuid4().hex[:6]}"


def _audited(db, action: str, category_id: int) -> list[AuditEventDB]:
    db.expire_all()
    return db.query(AuditEventDB).filter_by(action=action, subject_type="category", subject_id=category_id).all()


def test_a_category_is_renamed_and_changes_type_and_both_are_audited(db):
    with signed_in(db) as (client, _token, csrf):
        headers = {"X-CSRF-Token": csrf}
        created = client.post("/content/categories", json={"name": _name(), "type": "main"}, headers=headers).json()
        renamed = client.patch(f"/content/categories/{created['id']}", json={"name": "t359-Seaside", "type": "sub"},
                               headers=headers)
    assert renamed.status_code == 200, renamed.text
    assert (renamed.json()["name"], renamed.json()["type"]) == ("t359-Seaside", "sub")
    assert len(_audited(db, "category.created", created["id"])) == 1
    [change] = _audited(db, "category.changed", created["id"])
    assert change.detail["name"]["to"] == "t359-Seaside" and change.detail["type"] == {"from": "main", "to": "sub"}


@pytest.mark.parametrize("body", [{"type": "tag"}, {"name": "  "}])
def test_a_bad_name_or_type_is_refused(db, body):
    with signed_in(db) as (client, _token, csrf):
        headers = {"X-CSRF-Token": csrf}
        created = client.post("/content/categories", json={"name": _name()}, headers=headers).json()
        refused = client.patch(f"/content/categories/{created['id']}", json=body, headers=headers)
        new = client.post("/content/categories", json={"name": _name(), "type": "tag"}, headers=headers)
    assert refused.status_code == 422 and new.status_code == 422


def test_an_unknown_category_is_not_found(db):
    with signed_in(db) as (client, _token, csrf):
        response = client.patch("/content/categories/987654321", json={"name": "x"}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 404


def test_relations_and_deletion_are_audited(db):
    with signed_in(db) as (client, _token, csrf):
        headers = {"X-CSRF-Token": csrf}
        parent = client.post("/content/categories", json={"name": _name()}, headers=headers).json()
        child = client.post("/content/categories", json={"name": _name(), "type": "sub"}, headers=headers).json()
        relation = client.post("/content/category-relations", json={
            "parent_category_id": parent["id"], "child_category_id": child["id"]}, headers=headers).json()
        assert client.delete(f"/content/category-relations/{relation['id']}", headers=headers).status_code == 204
        assert client.delete(f"/content/categories/{child['id']}", headers=headers).status_code == 200
    assert len(_audited(db, "category.relation_added", child["id"])) == 1
    assert len(_audited(db, "category.relation_removed", child["id"])) == 1
    [deleted] = _audited(db, "category.deleted", child["id"])
    assert deleted.detail["name"] == child["name"]
