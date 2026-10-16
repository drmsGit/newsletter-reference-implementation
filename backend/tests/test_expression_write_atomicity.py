"""Rejected personalisation writes preserve prior state (ADR-199/180; task-365)."""
import uuid

import pytest

from app.campaigns.db_models import ModuleInstanceDB, VariantDB
from app.campaigns.service import create_module_for_variant
from app.content.db_models import ContentRecordDB
from app.content.service import create_content
from app.database import SessionLocal
from app.expressions import service as dictionary
from app.overrides.db_models import ContentOverrideDB
from app.overrides.service import set_override_fields
from app.rendering.service import envelope_fields_for_variant
from tests.test_api_guard import signed_in
from tests.test_expression_checks import brand, db, world  # noqa: F401


def test_a_refused_envelope_also_rolls_back_the_rename_and_version(db, world, brand):  # noqa: F811
    variant = world["variant"]()
    db.refresh(variant)
    before = (variant.name, variant.updated_at, envelope_fields_for_variant(db, variant.id, "email"))
    with signed_in(db) as (client, _token, csrf):
        response = client.put(f"/campaigns/variants/{variant.id}",
                              headers={"X-CSRF-Token": csrf, "If-Match": before[1].isoformat()},
                              json={"name": "Must not persist", "envelope": {
                                  "subject": "Changed too", "preheader": "{{missing_entry}}"}})
    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["loc"] == ["body", "envelope", "preheader"]
    with SessionLocal() as observer:
        stored = observer.get(VariantDB, variant.id)
        assert (stored.name, stored.updated_at,
                envelope_fields_for_variant(observer, variant.id, "email")) == before


@pytest.mark.parametrize("surface", ["module", "content", "override"])
def test_another_brands_entry_is_refused_without_changing_saved_text(db, world, brand, foreign_brand, surface):  # noqa: F811
    name = "foreign_" + uuid.uuid4().hex[:8]
    dictionary.create_entry(db, foreign_brand.id, name=name, label="Other brand", languages={
        "en": {"cases": [], "fallback": "Only for the other brand"}})
    assert name not in dictionary.by_name(db, brand.id)
    record = create_content(db, title="Expression isolation", brand_id=brand.id,
                            content={"headline_medium": "Stored headline"})
    world["made"]["records"].append(record.id)
    variant = world["variant"]()
    module = create_module_for_variant(
        db, variant_id=variant.id, module_type="cta" if surface == "module" else "img_left",
        content_record_id=None if surface == "module" else record.id,
        module_data={"label": "Stored module label", "url": "https://example.test"} if surface == "module" else None,
        brand_id=brand.id)
    if surface == "override":
        set_override_fields(db, module.id, {"headline_medium": "Stored override"}, None,
                            brand_id=brand.id, author="test")
    db.expire_all()
    stored_module = db.get(ModuleInstanceDB, module.id)
    module_version = stored_module.updated_at
    module_before = dict(stored_module.module_data) if stored_module.module_data is not None else None
    stored_record = db.get(ContentRecordDB, record.id)
    record_before = (dict(stored_record.content), stored_record.updated_at)
    try:
        with signed_in(db) as (client, _token, csrf):
            headers = {"X-CSRF-Token": csrf}
            fields = {"label" if surface == "module" else "headline_medium": "{{" + name + "}}"}
            if surface == "module":
                response = client.put(f"/campaigns/modules/{module.id}", headers=headers,
                                      json={"module_type": "cta", "module_data": {**module_before, **fields}})
            elif surface == "content":
                response = client.patch(f"/content/{record.id}", headers=headers,
                                        json={"content": fields, "groups": ["email"]})
            else:
                response = client.put(f"/overrides/modules/{module.id}", headers=headers,
                                      json={"field_overrides": fields})
        assert response.status_code == (400 if surface == "override" else 422), response.text
        assert name in response.text and "this brand" in response.text
        with SessionLocal() as observer:
            current_module = observer.get(ModuleInstanceDB, module.id)
            current_record = observer.get(ContentRecordDB, record.id)
            assert current_module.updated_at == module_version
            assert current_module.module_data == module_before
            assert (current_record.content, current_record.updated_at) == record_before
            overrides = observer.query(ContentOverrideDB).filter_by(module_instance_id=module.id).all()
            if surface == "override":
                assert len(overrides) == 1 and overrides[0].active
                assert overrides[0].field_overrides == {"headline_medium": "Stored override"}
            else:
                assert overrides == []
    finally:
        db.rollback()
        db.query(ContentOverrideDB).filter_by(module_instance_id=module.id).delete(synchronize_session=False)
        db.commit()
