"""Asset writes preserve isolation and survive overlap (ADR-197)."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock

import pytest

from app.assets import service
from app.assets.db_models import AssetDB
from app.assets.store import LocalAssetStore
from tests.test_api_guard import signed_in
from tests.test_assets import _upload, anonymous, db, made, png, store  # noqa: F401


def test_overlapping_replacements_of_one_address_both_finish(tmp_path, monkeypatch):
    disk = LocalAssetStore(tmp_path)
    token = "a" * 32
    disk.put("brand", token, b"original")
    original = Path.replace
    first_ready, second_ready, first_finished = Event(), Event(), Event()
    lock = Lock()
    calls = 0

    def ordered_replace(path, target):
        nonlocal calls
        with lock:
            position = calls
            calls += 1
        if position == 0:
            first_ready.set()
            # A serialized implementation can finish without a second rename.
            second_ready.wait(2)
            try:
                return original(path, target)
            finally:
                first_finished.set()
        second_ready.set()
        assert first_finished.wait(5), "the first replacement did not finish"
        return original(path, target)

    monkeypatch.setattr(Path, "replace", ordered_replace)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(disk.put, "brand", token, b"first complete image")
        assert first_ready.wait(5)
        second = pool.submit(disk.put, "brand", token, b"second complete image")
        failures = [future.exception(timeout=10) for future in (first, second)]
    assert failures == [None, None], "overlapping replacements must not share temporary-file ownership"
    assert disk.get("brand", token) in (b"first complete image", b"second complete image")


def test_a_failed_disk_write_keeps_the_previous_image_and_metadata(db, made, store, monkeypatch):  # noqa: F811
    with signed_in(db) as (client, _token, csrf):
        before = _upload(client, csrf, made).json()
        class UnavailableStore:
            def put(self, *args):
                raise OSError("test disk unavailable")
        monkeypatch.setattr(service, "get_store", UnavailableStore)
        response = client.post(
            f"/assets/{before['id']}/replace",
            files={"file": ("replacement", png(600, 400), "image/png")},
            headers={"X-CSRF-Token": csrf},
        )
    assert response.status_code == 500
    db.expire_all()
    row = db.get(AssetDB, before["id"])
    assert (row.name, row.width, row.height, row.size_bytes) == (
        before["name"], before["width"], before["height"], before["size_bytes"],
    )
    assert anonymous.get("/media/" + row.token).content == png()


def test_another_brands_image_cannot_be_replaced_described_or_hidden(db, foreign_brand, made, store):  # noqa: F811
    image = service.upload(db, brand_id=foreign_brand.id, data=png(), label="Foreign", alt_text="Unchanged")
    made["assets"].append(image.id)
    with signed_in(db) as (client, _token, csrf):
        headers = {"X-CSRF-Token": csrf}
        replaced = client.post(f"/assets/{image.id}/replace",
                               files={"file": ("new", png(900, 500), "image/png")}, headers=headers)
        described = client.put(f"/assets/{image.id}/alt", json={"alt_text": "Wrong brand"}, headers=headers)
        hidden = client.post(f"/assets/{image.id}/hide", headers=headers)
    assert [r.status_code for r in (replaced, described, hidden)] == [404, 404, 404]
    db.refresh(image)
    assert (image.alt_text, image.width, image.height, image.hidden_at) == ("Unchanged", 120, 80, None)
    assert LocalAssetStore(store).get(foreign_brand.key, image.token) == png()


# Added with the fix (task-383): the two halves Codex's overlap case does not reach.

def test_a_failed_write_leaves_no_temporary_file_and_keeps_the_image(tmp_path, monkeypatch):
    disk = LocalAssetStore(tmp_path)
    token = "b" * 32
    disk.put("brand", token, b"original")

    def broken_replace(path, target):
        raise OSError("test rename refused")

    monkeypatch.setattr(Path, "replace", broken_replace)
    with pytest.raises(OSError):
        disk.put("brand", token, b"never stored")
    assert disk.get("brand", token) == b"original"
    assert [p.name for p in (tmp_path / "brand").iterdir()] == [token], "no temporary file left behind"


def test_replacements_of_one_image_take_turns_so_file_and_row_agree(db, made, store, default_brand):  # noqa: F811
    """While one replacement writes, the image's row is locked: a second one
    waits, so the stored file and the row's size and dimensions always come
    from the same replacement."""
    from sqlalchemy.exc import OperationalError

    from app.database import SessionLocal

    image = service.upload(db, brand_id=default_brand.id, data=png(), label="Turns", alt_text="")
    made["assets"].append(image.id)
    writing, release = Event(), Event()
    real_store = service.get_store()

    class SlowStore:
        def put(self, *args):
            writing.set()
            assert release.wait(5)
            real_store.put(*args)

    def replace_in_its_own_session():
        session = SessionLocal()
        try:
            asset = session.get(AssetDB, image.id)
            service.replace(session, asset, png(300, 300))
        finally:
            session.close()

    other = SessionLocal()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            original_get_store = service.get_store
            service.get_store = SlowStore
            try:
                running = pool.submit(replace_in_its_own_session)
                assert writing.wait(5)
                with pytest.raises(OperationalError):
                    other.query(AssetDB).filter(AssetDB.id == image.id).with_for_update(nowait=True).one()
            finally:
                # Before releasing: should the probe have got the lock, it
                # must not hold it while the replacement finishes.
                other.rollback()
                release.set()
                service.get_store = original_get_store
            running.result(timeout=10)
    finally:
        other.close()
    db.expire_all()
    row = db.get(AssetDB, image.id)
    assert (row.width, row.height) == (300, 300)
