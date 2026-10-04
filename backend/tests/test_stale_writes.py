"""A write based on an out-of-date read is refused, not merged (task-110).

ADR-180 point 2: `updated_at` is the version token, a caller states the one it
read in `If-Match`, and a mismatch answers 409 — the collision of two editors
becomes visible instead of the second save silently erasing the first. The
token is optional (user, 2026-10-03): a write without it behaves as before,
which is what keeps the Jinja forms and existing integrations working.

Every case writes once with the token it read (accepted), then again with that
same, now stale token (refused, nothing changed), then without a token
(accepted).
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.permissions import CAMPAIGNS_MANAGE, VIEW
from app.campaigns.db_models import CampaignDB, DecisionSlotDB, ModuleInstanceDB, VariantDB
from main import app
from tests.machine import editor, machine

client = TestClient(app, raise_server_exceptions=False)

# One editing machine per test: several writes as different machines would
# meet each other's fence (task-254).
pytestmark = pytest.mark.usefixtures("one_editor")


@pytest.fixture
def world(db, default_brand):
    campaign = CampaignDB(brand_id=default_brand.id, name=f"stale-{uuid.uuid4().hex[:6]}")
    db.add(campaign); db.flush()
    variant = VariantDB(campaign_id=campaign.id, channel="email", name="v", status="draft")
    db.add(variant); db.flush()
    first = ModuleInstanceDB(variant_id=variant.id, module_type="cta", position=1, module_data={"label": "A"})
    second = ModuleInstanceDB(variant_id=variant.id, module_type="cta", position=2, module_data={"label": "B"})
    slot = DecisionSlotDB(variant_id=variant.id, name="s", decision_type="content_recommendation",
                          decision_strategy="top_score")
    db.add_all([first, second, slot]); db.commit()
    yield {"campaign": campaign, "variant": variant, "first": first, "second": second, "slot": slot}
    db.rollback()
    db.query(ModuleInstanceDB).filter(ModuleInstanceDB.variant_id == variant.id).delete()
    db.query(DecisionSlotDB).filter(DecisionSlotDB.variant_id == variant.id).delete()
    db.query(VariantDB).filter(VariantDB.id == variant.id).delete()
    db.query(CampaignDB).filter(CampaignDB.id == campaign.id).delete()
    db.commit()


def _send(method, url, token=None, **kw):
    with editor([CAMPAIGNS_MANAGE, VIEW]) as headers:
        if token is not None:
            headers = {**headers, "If-Match": token}
        return getattr(client, method)(url, headers=headers, **kw)


def _composed(campaign_id):
    response = _send("get", f"/campaigns/{campaign_id}/composition")
    assert response.status_code == 200, response.text
    [variant] = response.json()["variants"]
    return variant


# Each edit: how to read its token from what the editor reads, how to write it,
# and how to see whether the write landed.
def variant_edit(w, n):
    return ("put", f"/campaigns/variants/{w['variant'].id}",
            {"json": {"name": "v", "subject": f"Subject {n}"}})


def module_edit(w, n):
    return ("put", f"/campaigns/modules/{w['first'].id}",
            {"json": {"module_type": "cta", "module_data": {"label": f"L{n}"}}})


def slot_put(w, n):
    return ("put", f"/campaigns/decision-slots/{w['slot'].id}",
            {"json": {"decision_strategy": "top_score", "candidate_filter": {"category_ids": [n]}}})


def slot_patch(w, n):
    return ("patch", f"/campaigns/decision-slots/{w['slot'].id}",
            {"json": {"candidate_filter": {"category_ids": [n]}}})


def token_of(edit, composed):
    if edit is variant_edit:
        return composed["variant"]["updated_at"]
    if edit is module_edit:
        return next(m for m in composed["modules"] if m["id"] == composed["_first"])["updated_at"]
    return composed["decision_slots"][0]["updated_at"]


@pytest.mark.parametrize("edit", [variant_edit, module_edit, slot_put, slot_patch])
def test_a_stale_edit_is_refused_and_changes_nothing(db, world, edit):
    composed = {**_composed(world["campaign"].id), "_first": world["first"].id}
    token = token_of(edit, composed)

    method, url, body = edit(world, 1)
    fresh = _send(method, url, token, **body)
    assert fresh.status_code == 200, fresh.text

    method, url, body = edit(world, 2)
    stale = _send(method, url, token, **body)
    assert stale.status_code == 409, stale.text

    after = {**_composed(world["campaign"].id), "_first": world["first"].id}
    assert token_of(edit, after) == fresh.json()["updated_at"], "the refused write changed the row"

    method, url, body = edit(world, 3)
    assert _send(method, url, None, **body).status_code == 200, "a write without a token must still work"


def test_a_stale_move_is_refused(world):
    token = next(m for m in _composed(world["campaign"].id)["modules"]
                 if m["id"] == world["second"].id)["updated_at"]
    url = f"/campaigns/modules/{world['second'].id}/move?direction=up"
    assert _send("post", url, token).status_code == 200
    assert _send("post", url, token).status_code == 409
    order = [m["id"] for m in _composed(world["campaign"].id)["modules"]]
    assert order == [world["second"].id, world["first"].id], "the refused move moved"


def test_a_stale_delete_is_refused(db, world):
    token = next(m for m in _composed(world["campaign"].id)["modules"]
                 if m["id"] == world["first"].id)["updated_at"]
    edited = _send("put", f"/campaigns/modules/{world['first'].id}",
                   json={"module_type": "cta", "module_data": {"label": "changed"}})
    assert edited.status_code == 200
    assert _send("delete", f"/campaigns/modules/{world['first'].id}", token).status_code == 409
    db.expire_all()
    assert db.get(ModuleInstanceDB, world["first"].id) is not None, "deleted over someone's edit"
    assert _send("delete", f"/campaigns/modules/{world['first'].id}",
                 edited.json()["updated_at"]).status_code == 200


def test_a_subject_only_edit_moves_the_variants_token(world):
    """Subject and preheader live in the header module, so a subject-only edit
    left the variant row untouched — and two editors changing the subject
    would never have conflicted."""
    url = f"/campaigns/variants/{world['variant'].id}"
    token = _composed(world["campaign"].id)["variant"]["updated_at"]
    assert _send("put", url, token, json={"name": "v", "subject": "One"}).status_code == 200
    assert _send("put", url, token, json={"name": "v", "subject": "Two"}).status_code == 409


def test_a_token_that_is_not_a_timestamp_is_a_bad_request(world):
    response = _send("put", f"/campaigns/variants/{world['variant'].id}", "yesterday",
                     json={"name": "v"})
    assert response.status_code == 400, response.text
