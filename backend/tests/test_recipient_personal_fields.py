"""Recipients carry gender, first name and last name (task-365; ADR-199).

The fields personalisation reads are real columns, written through the
recipients API that a CRM sync calls. Gender is female, male, diverse or
empty; anything else is refused with the allowed values. A sync that leaves a
field out keeps what it holds; one that sends null clears it.
"""
import uuid

import pytest

from app.recipients.db_models import RecipientDB
from app.recipients.service import create_recipient, validate_personal_fields
from tests import test_render_skip as fixtures
from tests.test_api_guard import signed_in

db = fixtures.db
world = fixtures.world


def _post(db, world, **fields):
    external_id = fields.pop("external_id", None) or f"t365-{uuid.uuid4().hex[:8]}"
    with signed_in(db) as (client, _token, csrf):
        response = client.post("/recipients/", headers={"X-CSRF-Token": csrf}, json={
            "brand_id": world["brand"].id, "external_id": external_id,
            "address": f"{external_id}@example.invalid", **fields})
    if response.status_code == 200:
        world["made"]["people"].append(response.json()["id"])
    return response


def test_the_api_takes_and_returns_the_three_fields(db, world):
    response = _post(db, world, gender="female", first_name="Anna", last_name="Müller")
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["gender"], body["first_name"], body["last_name"]) == ("female", "Anna", "Müller")


def test_any_other_gender_is_refused_with_the_allowed_values(db, world):
    response = _post(db, world, gender="w")
    assert response.status_code == 422
    assert "female" in response.text and "diverse" in response.text


def test_a_sync_that_leaves_them_out_keeps_them_and_null_clears(db, world):
    first = _post(db, world, gender="male", first_name="Jan", last_name="de Vries").json()
    again = _post(db, world, external_id=first["external_id"]).json()
    assert (again["gender"], again["first_name"], again["last_name"]) == ("male", "Jan", "de Vries")
    cleared = _post(db, world, external_id=first["external_id"], last_name=None).json()
    assert (cleared["first_name"], cleared["last_name"]) == ("Jan", None)


def test_text_is_trimmed_and_empty_is_none():
    assert validate_personal_fields({"first_name": "  Anna ", "last_name": "", "gender": ""}) == {
        "first_name": "Anna", "last_name": None, "gender": None}


@pytest.mark.parametrize("personal", [{"gender": "f"}, {"nickname": "A"}, {"first_name": 3}])
def test_the_service_refuses_what_the_api_would(db, world, personal):
    external_id = f"t365-{uuid.uuid4().hex[:8]}"
    with pytest.raises(ValueError):
        create_recipient(db, world["brand"].id, external_id, personal=personal)
    db.rollback()
    assert db.query(RecipientDB).filter(RecipientDB.external_id == external_id).count() == 0
