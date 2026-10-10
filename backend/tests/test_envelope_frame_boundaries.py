"""The rename must stay safe when the freed header name is used (task-349).

ADR-183 freezes content; ADR-193 reserves header for a visible module. Supply
that future module through lookup fixtures without installing production files.
"""
import copy

import pytest

from app.modules import registry
from app.modules.registry import ModuleManifest, ModuleVariable
from app.rendering import frame as frames, service
from tests import test_render_skip as _render_skip

db = _render_skip.db
world = _render_skip.world


@pytest.fixture
def frozen_header():
    return {
        "frame_version": 1,
        "channel": "email",
        "envelope": {"subject": "Frozen subject"},
        "modules": [{
            "module_id": 17, "module_type": "header", "position": 0,
            "kind": frames.KIND_STATIC,
            "variables": {"preheader": "Frozen inbox text", "logo_url": ""},
        }],
    }


@pytest.fixture
def visible_header(monkeypatch):
    manifest = ModuleManifest(
        name="header", channel="email", label="Visible header",
        description="Fixture for the freed name", cms=False,
        variables=[ModuleVariable(name="logo_url", required=True)],
    )
    original_manifest = registry.get_manifest
    original_template = service.get_template_html

    def get_manifest(channel, name):
        if (channel, name) == ("email", "header"):
            return manifest
        return original_manifest(channel, name)

    def get_template(channel, name):
        if (channel, name) == ("email", "header"):
            return '<img alt="Visible logo" src="{{ logo_url }}">'
        return original_template(channel, name)

    monkeypatch.setattr(registry, "get_manifest", get_manifest)
    monkeypatch.setattr(frames, "get_manifest", get_manifest)
    monkeypatch.setattr(service, "get_manifest", get_manifest)
    monkeypatch.setattr(service, "get_template_html", get_template)


def test_installing_a_visible_header_cannot_change_an_old_delivery(
    frozen_header, request,
):
    before = copy.deepcopy(frozen_header)
    sent = frames.render_frame(None, frozen_header, picks=[])[0]
    request.getfixturevalue("visible_header")
    reconstructed = frames.render_frame(None, frozen_header, picks=[])[0]

    assert "Frozen inbox text" in reconstructed.body
    assert "Visible logo" not in reconstructed.body
    assert 'data-module-type="header"' in reconstructed.body
    assert frames.artifact_hash(reconstructed) == frames.artifact_hash(sent)
    assert frames.what_rendered(frozen_header, []) == (False, 0)
    assert frozen_header == before


def test_a_version_two_header_uses_the_visible_template(
    frozen_header, visible_header,
):
    frozen_header["frame_version"] = 2
    frozen_header["modules"][0]["variables"]["logo_url"] = "https://example.invalid/logo.png"
    rendered = frames.render_frame(None, frozen_header, picks=[])[0]

    assert "Visible logo" in rendered.body
    assert "https://example.invalid/logo.png" in rendered.body
    assert "Frozen inbox text" not in rendered.body


@pytest.mark.parametrize("version, expected", [
    (1, []),
    (2, [(17, "header", "logo_url")]),
])
def test_required_fields_follow_the_frames_version(
    frozen_header, visible_header, version, expected,
):
    frozen_header["frame_version"] = version
    assert frames.missing_required_in_frame(frozen_header) == expected


def test_migration_changes_only_live_email_rows_and_is_repeatable(db, world, frozen_header):
    from pathlib import Path

    from sqlalchemy import text

    from app.campaigns.db_models import ModuleInstanceDB
    from app.snapshots.db_models import SnapshotDB

    email = world["variant"](static=True, slots=0)
    push = world["variant"]("push", slots=0)
    old_email = db.query(ModuleInstanceDB).filter_by(
        variant_id=email.id, module_type="envelope",
    ).one()
    old_email.module_type = "header"
    other_channel = ModuleInstanceDB(
        variant_id=push.id, module_type="header", position=0, module_data={},
    )
    db.add(other_channel)
    snapshot = SnapshotDB(variant_id=email.id, render_context=frozen_header)
    db.add(snapshot)
    db.commit()
    world["made"]["snapshots"].append(snapshot.id)
    ids = [old_email.id, other_channel.id]
    frozen_sql = text("SELECT render_context::text FROM snapshots WHERE id = :id")
    frozen_bytes = db.execute(frozen_sql, {"id": snapshot.id}).scalar_one()
    before = {
        row.id: (row.module_type, row.module_data)
        for row in db.query(ModuleInstanceDB).filter_by(variant_id=email.id)
        if row.id != old_email.id
    }
    migration = (Path(__file__).resolve().parents[1] /
                 "scripts/migrate_0043_envelope_module_rows.sql").read_text()
    # Execute the actual script, including its transaction, on the isolated
    # suite engine. Fixtures own every row above and remove them on teardown.
    assert "_test_" in db.bind.url.database
    for _ in range(2):
        connection = db.bind.raw_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(migration)
        finally:
            connection.close()
        db.expire_all()
        assert [db.get(ModuleInstanceDB, i).module_type for i in ids] == ["envelope", "header"]
        assert db.execute(frozen_sql, {"id": snapshot.id}).scalar_one() == frozen_bytes
        assert {
            row.id: (row.module_type, row.module_data)
            for row in db.query(ModuleInstanceDB).filter_by(variant_id=email.id)
            if row.id != ids[0]
        } == before
