"""The Jinja send flow, over HTTP (task-239).

`send_instance_create` and `send_instance_trigger` called
`working_brand_id(request, db)` without declaring `request`, so both raised
NameError (a 500) from the ADR-172 brand rollout until 2026-10-02. Nothing
caught it: `prepare_send_from_audience` was covered only by direct calls, and
`test_auth_policy.py` only resolves the policy for these paths.

These tests post to the real routes with a signed-in session and the form CSRF
token, and assert the route *ran* — a redirect to the delivery page — not
merely that something answered.
"""
import re
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import service as auth
from app.database import SessionLocal
from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
from main import app

TAG = "uisendflow"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin(db):
    user = auth.create_user(
        db, email=f"{TAG}-{uuid.uuid4().hex[:8]}@example.invalid", role_key="admin",
    )
    token = auth.create_session(db, user)
    client = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    client.cookies.set(auth.SESSION_COOKIE, token)
    csrf = re.search(
        r'name="csrf_token" value="([^"]+)"', client.get("/ui/approvals").text,
    )
    assert csrf, "the UI page carried no CSRF token to post back"
    yield client, csrf.group(1)
    db.rollback()
    for table in ("login_codes", "auth_sessions", "role_assignments"):
        db.execute(
            text(f"DELETE FROM {table} WHERE user_id = :u"),
            {"u": user.id},
        )
    db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
    db.commit()


@pytest.fixture
def created(db):
    """Ids of send instances a test made, removed afterwards."""
    ids = []
    yield ids
    db.rollback()
    for send_id in ids:
        db.query(DeliveryExecutionDB).filter(
            DeliveryExecutionDB.send_instance_id == send_id).delete()
        db.query(SendInstanceDB).filter(SendInstanceDB.id == send_id).delete()
    db.commit()


@pytest.fixture
def audience_group_id(db):
    """An empty audience in the default brand: planning against it is refused
    ("no consenting recipients"), which still proves the route got as far as
    `prepare_send_from_audience` with a brand."""
    from app.audience.db_models import AudienceGroupDB

    group = AudienceGroupDB(
        brand_id=auth.ensure_default_brand(db).id, name=f"{TAG}-{uuid.uuid4().hex[:8]}",
    )
    db.add(group)
    db.commit()
    yield group.id
    db.rollback()
    db.query(AudienceGroupDB).filter(AudienceGroupDB.id == group.id).delete()
    db.commit()


def _seeded_snapshot_id(db):
    return db.query(SendInstanceDB).order_by(SendInstanceDB.id).first().snapshot_id


def test_planning_a_send_from_the_jinja_flow_runs(admin, db, created, audience_group_id):
    client, csrf = admin
    snapshot_id = _seeded_snapshot_id(db)
    before = {row.id for row in db.query(SendInstanceDB.id).all()}

    response = client.post(
        f"/ui/campaigns/1/snapshots/{snapshot_id}/send-instances",
        data={
            "csrf_token": csrf,
            "name": f"{TAG}-{uuid.uuid4().hex[:6]}",
            "audience_group_id": str(audience_group_id),
            "provider": "mock",
        },
    )
    db.expire_all()
    created.extend(row.id for row in db.query(SendInstanceDB.id).all() if row.id not in before)

    assert response.status_code == 303, response.text[:300]
    location = response.headers["location"]
    # A refusal (e.g. an audience with no consenting recipients) redirects back
    # to the campaign with ?error=; success lands on the delivery page. A
    # NameError is neither — it is a 500, asserted away above. Either redirect
    # proves `prepare_send_from_audience` was reached with a brand.
    assert location.startswith(("/ui/deliveries/send-instances/", "/ui/campaigns/1?error=")), location


def test_firing_a_send_from_the_jinja_flow_runs(admin, db, created):
    client, csrf = admin
    snapshot_id = _seeded_snapshot_id(db)
    brand = auth.ensure_default_brand(db)
    row = SendInstanceDB(
        snapshot_id=snapshot_id, brand_id=brand.id,
        name=f"{TAG}-{uuid.uuid4().hex[:6]}", status="draft", provider="mock",
    )
    db.add(row)
    db.commit()
    created.append(row.id)

    response = client.post(f"/ui/send-instances/{row.id}/send", data={"csrf_token": csrf})

    assert response.status_code == 303, response.text[:300]
    location = response.headers["location"]
    assert location.startswith(f"/ui/deliveries/send-instances/{row.id}"), location
    # The seeded snapshot may be refused by a preflight check (missing content,
    # no recipients) and that is a redirect with ?error=. What must not happen
    # is "not found": it would mean the brand never resolved to this row.
    assert "not%20found" not in location, location
    db.expire_all()
    assert "?error=" in location or db.get(SendInstanceDB, row.id).status != "draft", (
        "the route answered without an error and without attempting the send"
    )
