"""Taking an older translation cannot hide a newer original edit (ADR-200 §5)."""
from tests import test_content_translation as fixtures
from tests.test_api_guard import signed_in

db = fixtures.db
world = fixtures.world
model = fixtures.model


def test_taking_a_proposal_keeps_a_later_original_change_visible(db, world, model):
    original = world["record"]
    model["reply"] = fixtures._reply()
    with signed_in(db) as (client, _token, csrf):
        headers = {"X-CSRF-Token": csrf}
        assert fixtures._set_language(client, csrf, original.id, "en").status_code == 200
        made = fixtures._translate(client, csrf, original.id)
        assert made.status_code == 201, made.text
        translated_id = made.json()["record_id"]
        changed = client.patch(f"/content/{original.id}", json={
            "content": {"headline_medium": "Four days in Lisbon"}, "groups": ["email"],
        }, headers=headers)
        assert changed.status_code == 200, changed.text
        model["reply"] = fixtures._reply(headline_medium="Vier Tage in Lissabon")
        proposed = client.post(f"/content/{translated_id}/retranslations", headers=headers)
        assert proposed.status_code == 200, proposed.text
        # A person changes the original again after this run read it.
        changed = client.patch(f"/content/{original.id}", json={
            "content": {"headline_medium": "Five days in Lisbon"}, "groups": ["email"],
        }, headers=headers)
        assert changed.status_code == 200, changed.text
        taken = client.patch(f"/content/{translated_id}", json={
            "content": {"headline_medium": "Vier Tage in Lissabon"}, "groups": ["email"],
            "applied_suggestion_run_id": proposed.json()["ai_run_id"],
        }, headers=headers)
        assert taken.status_code == 200, taken.text
        detail = client.get(f"/content/{translated_id}")
        assert detail.status_code == 200
        assert detail.json()["content"]["headline_medium"] == "Vier Tage in Lissabon"
        assert detail.json()["original_changed"] == ["headline_medium"]
