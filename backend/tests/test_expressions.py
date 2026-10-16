"""A brand's expression dictionary (task-365; ADR-199).

Entries are cases per language plus a fallback: a form, not a language. The
starters come from storage/expressions.json and are copied into a brand once,
on first use. An entry's name is fixed; label and cases change. An entry a
text still uses is not deleted. Writes are people with brand_profiles.manage.
"""
import json
import uuid

import pytest

from app.auth.permissions import BRAND_PROFILES_MANAGE, VIEW
from app.content.db_models import ContentRecordDB
from app.expressions import rules, service, starters
from app.expressions.db_models import ExpressionEntryDB
from tests.test_brand_profile_api import admin, db, person_with  # noqa: F401

FORMAL = starters.starters()["salutation_formal"]["languages"]
INFORMAL = starters.starters()["salutation_informal"]["languages"]


# --- what an entry resolves to -----------------------------------------------------------

@pytest.mark.parametrize("recipient, expected", [
    ({"gender": "female", "last_name": "Müller"}, "Sehr geehrte Frau Müller,"),
    ({"gender": "male", "last_name": "de Vries"}, "Sehr geehrter Herr de Vries,"),
    ({"gender": "diverse", "last_name": "Weber"}, "Sehr geehrte Damen und Herren,"),
    ({"gender": "female", "last_name": None}, "Sehr geehrte Damen und Herren,"),
    ({"gender": "female", "last_name": "  "}, "Sehr geehrte Damen und Herren,"),
    (None, "Sehr geehrte Damen und Herren,"),
])
def test_the_formal_salutation(recipient, expected):
    assert rules.resolve(FORMAL["de"], recipient) == expected


@pytest.mark.parametrize("recipient, expected", [
    ({"first_name": "Anna"}, "Hallo Anna,"), ({"first_name": ""}, "Hallo,"), ({}, "Hallo,"), (None, "Hallo,"),
])
def test_the_informal_salutation(recipient, expected):
    assert rules.resolve(INFORMAL["de"], recipient) == expected


def test_a_case_whose_text_prints_an_empty_field_does_not_apply():
    """The filled-fields rule (ADR-199): never "Liebe Frau ,"."""
    spec = {"cases": [{"field": "gender", "is": "equals", "value": "female", "text": "Liebe {{first_name}} {{last_name}},"},
                      {"field": "first_name", "is": "filled", "text": "Liebe {{first_name}},"}],
            "fallback": "Hallo,"}
    assert rules.resolve(spec, {"gender": "female", "first_name": "Anna"}) == "Liebe Anna,"
    assert rules.resolve(spec, {"gender": "female", "first_name": "Anna", "last_name": "Weber"}) == "Liebe Anna Weber,"


def test_empty_tests_for_nothing_there():
    spec = {"cases": [{"field": "first_name", "is": "empty", "text": "Hallo Gast,"}], "fallback": "Hallo,"}
    assert rules.resolve(spec, {"first_name": None}) == "Hallo Gast,"
    assert rules.resolve(spec, {"first_name": "Anna"}) == "Hallo,"


def test_a_value_is_inserted_raw_escaping_is_the_renderers():
    assert rules.resolve(INFORMAL["en"], {"first_name": "<b>Ann</b>"}) == "Hi <b>Ann</b>,"


# --- what an entry may hold --------------------------------------------------------------

@pytest.mark.parametrize("languages, where", [
    ({}, ("languages",)),
    ({"deutsch": {"cases": [], "fallback": "Hallo"}}, ("languages", "deutsch")),
    ({"de": {"cases": []}}, ("languages", "de", "fallback")),
    ({"de": {"cases": [], "fallback": "Hallo {{first_name}}"}}, ("languages", "de", "fallback")),
    ({"de": {"cases": [{"field": "age", "is": "filled", "text": "x"}], "fallback": "x"}},
     ("languages", "de", "cases", 0, "field")),
    ({"de": {"cases": [{"field": "gender", "is": "equals", "text": "x"}], "fallback": "x"}},
     ("languages", "de", "cases", 0, "value")),
    ({"de": {"cases": [{"field": "gender", "is": "equals", "value": "w", "text": "x"}], "fallback": "x"}},
     ("languages", "de", "cases", 0, "value")),
    ({"de": {"cases": [{"field": "first_name", "is": "filled", "text": "Hi {{gender}}"}], "fallback": "x"}},
     ("languages", "de", "cases", 0, "text")),
    ({"de": {"cases": [{"field": "first_name", "is": "filled", "text": "Hi {{salutation_formal}}"}],
             "fallback": "x"}}, ("languages", "de", "cases", 0, "text")),
])
def test_what_an_entry_may_not_hold(languages, where):
    with pytest.raises(rules.EntryInvalid) as refused:
        rules.check_entry("greeting", "Greeting", languages)
    assert where in [loc for loc, _ in refused.value.errors]


@pytest.mark.parametrize("name", ["Greeting", "1st", "first_name", "a-b", ""])
def test_a_name_is_a_plain_word_and_not_a_recipient_field(name):
    assert rules.check_name(name) is not None


def test_the_shipped_starters_are_sound():
    assert set(starters.starters()) == {"salutation_informal", "salutation_formal"}


def test_a_bad_starter_file_is_refused(tmp_path, monkeypatch):
    bad = tmp_path / "expressions.json"
    bad.write_text(json.dumps({"entries": {"x": {"label": "X", "languages": {"de": {"cases": []}}}}}))
    monkeypatch.setattr(starters, "STARTERS_PATH", bad)
    with pytest.raises(ValueError, match="fallback"):
        starters.assert_starters_load()
    monkeypatch.undo()
    starters.assert_starters_load()


# --- the starters, copied once -----------------------------------------------------------

def test_a_brand_gets_the_starters_once(db, temp_brand):  # noqa: F811
    brand = temp_brand("expressions")
    assert brand.expressions_started_at is None
    first = service.entries_of(db, brand.id)
    assert {e.name for e in first} == {"salutation_informal", "salutation_formal"}
    for entry in first:
        db.delete(entry)
    db.commit()
    assert service.entries_of(db, brand.id) == [], "deleting them all does not bring them back"


def test_rendering_reads_without_starting(db, temp_brand):  # noqa: F811
    brand = temp_brand("expressions")
    assert service.entries_of(db, brand.id, start=False) == []
    db.refresh(brand)
    assert brand.expressions_started_at is None


# --- the API -----------------------------------------------------------------------------

LANGUAGES = {"de": {"cases": [{"field": "first_name", "is": "filled", "text": "Moin {{first_name}}!"}],
                    "fallback": "Moin!"}}


@pytest.fixture
def made(db):  # noqa: F811
    names: list[str] = []
    yield names
    db.rollback()
    db.query(ContentRecordDB).filter(ContentRecordDB.title.like("t365-%")).delete(synchronize_session=False)
    db.query(ExpressionEntryDB).filter(ExpressionEntryDB.name.in_(names)).delete(synchronize_session=False)
    db.commit()


def _name(made):
    name = f"t365_{uuid.uuid4().hex[:6]}"
    made.append(name)
    return name


def test_the_dictionary_is_read_with_the_starters_and_who_may_change_it(db):  # noqa: F811
    with admin(db) as (client, _headers):
        body = client.get("/expressions").json()
    assert {"salutation_informal", "salutation_formal"} <= {e["name"] for e in body["items"]}
    assert body["may_manage"] is True
    formal = next(e for e in body["items"] if e["name"] == "salutation_formal")
    assert formal["languages"]["de"]["cases"][0]["is"] == "equals"


def test_an_entry_is_created_changed_and_its_name_stays(db, made):  # noqa: F811
    name = _name(made)
    with admin(db) as (client, headers):
        created = client.post("/expressions", json={"name": name, "label": "Moin", "languages": LANGUAGES},
                              headers=headers)
        assert created.status_code == 201, created.text
        entry = created.json()
        again = client.post("/expressions", json={"name": name, "label": "Twice", "languages": LANGUAGES},
                            headers=headers)
        changed = client.put(f"/expressions/{entry['id']}", json={"name": "other", "label": "Moin moin",
                                                                  "languages": LANGUAGES},
                             headers={**headers, "If-Match": entry["updated_at"]})
        stale = client.put(f"/expressions/{entry['id']}", json={"label": "Late", "languages": LANGUAGES},
                           headers={**headers, "If-Match": entry["updated_at"]})
    assert again.status_code == 409
    assert changed.status_code == 200, changed.text
    assert (changed.json()["name"], changed.json()["label"]) == (name, "Moin moin")
    assert stale.status_code == 409


def test_a_bad_entry_is_refused_per_part(db, made):  # noqa: F811
    with admin(db) as (client, headers):
        response = client.post("/expressions", json={"name": _name(made), "label": "X", "languages": {
            "de": {"cases": [], "fallback": "Hallo {{first_name}}"}}}, headers=headers)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "languages", "de", "fallback"]


def test_an_entry_in_use_is_not_deleted_and_the_refusal_says_where(db, made, default_brand):  # noqa: F811
    name = _name(made)
    with admin(db) as (client, headers):
        entry = client.post("/expressions", json={"name": name, "label": "Moin", "languages": LANGUAGES},
                            headers=headers).json()
        db.add(ContentRecordDB(title="t365-record", brand_id=default_brand.id,
                               content={"body_medium": f"{{{{ {name} }}}} and welcome"}))
        db.commit()
        refused = client.delete(f"/expressions/{entry['id']}", headers=headers)
        db.query(ContentRecordDB).filter(ContentRecordDB.title == "t365-record").delete()
        db.commit()
        deleted = client.delete(f"/expressions/{entry['id']}", headers=headers)
    assert refused.status_code == 409
    assert "t365-record" in refused.json()["detail"]
    assert deleted.status_code == 204


def test_changing_it_needs_brand_profiles_manage(db, made):  # noqa: F811
    with person_with(db, [VIEW]) as (client, headers):
        read = client.get("/expressions")
        write = client.post("/expressions", json={"name": _name(made), "label": "X", "languages": LANGUAGES},
                            headers=headers)
    assert read.status_code == 200 and read.json()["may_manage"] is False
    assert write.status_code == 403
    with person_with(db, [VIEW, BRAND_PROFILES_MANAGE]) as (client, headers):
        allowed = client.post("/expressions", json={"name": _name(made), "label": "X", "languages": LANGUAGES},
                              headers=headers)
    assert allowed.status_code == 201, allowed.text
