"""Dictionary startup and brand boundaries (task-365; ADR-199 points 3/5/14)."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
import uuid

from app.auth.db_models import BrandDB
from app.content.db_models import ContentRecordDB
from app.database import SessionLocal
from app.expressions import service
from tests.test_brand_profile_api import admin


def test_two_first_uses_copy_one_dictionary(db, temp_brand, monkeypatch):
    brand = temp_brand("expression-overlap")
    brand_id = brand.id
    inside_starters, second_started, second_inside = Event(), Event(), Event()
    guard = Lock()
    calls = 0
    original = service.starters

    def overlapping_starters():
        nonlocal calls
        with guard:
            calls += 1
            first = calls == 1
        if first:
            inside_starters.set()
            assert second_started.wait(5), "second reader never started"
            # A serialized second reader cannot enter until the first commits.
            # Without serialization it races the first starter insertion.
            second_inside.wait(1)
        else:
            second_inside.set()
        return original()

    def read(second=False):
        with SessionLocal() as session:
            if second:
                second_started.set()
            return {entry.name: entry.id for entry in service.entries_of(session, brand_id)}

    monkeypatch.setattr(service, "starters", overlapping_starters)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(read)
        assert inside_starters.wait(5)
        second = pool.submit(read, True)
        first_result, second_result = first.result(timeout=10), second.result(timeout=10)
    assert first_result == second_result
    assert set(first_result) == set(original())
    assert calls == 1, "the brand must copy its starters exactly once"
    db.refresh(brand)
    assert brand.expressions_started_at is not None


def test_first_use_does_not_commit_or_rollback_the_callers_work(db, temp_brand, default_brand):
    brand = temp_brand("expression-transaction")
    title = "uncommitted-" + uuid.uuid4().hex
    brand_id = brand.id
    # Unrelated work is already flushed but uncommitted in the caller's session.
    record = ContentRecordDB(brand_id=default_brand.id, title=title, content={})
    db.add(record)
    db.flush()
    try:
        assert service.entries_of(db, brand_id)
        assert db.query(ContentRecordDB).filter_by(title=title).one().title == title
        with SessionLocal() as observer:
            assert observer.query(ContentRecordDB).filter_by(title=title).count() == 0
    finally:
        db.rollback()
    with SessionLocal() as observer:
        assert observer.query(ContentRecordDB).filter_by(title=title).count() == 0
        assert observer.get(BrandDB, brand_id).expressions_started_at is not None
        assert service.entries_of(observer, brand_id, start=False)


def test_foreign_entries_are_not_listed_changed_or_deleted(db, foreign_brand):
    name = "foreign_" + uuid.uuid4().hex[:8]
    languages = {"de": {"cases": [], "fallback": "Private greeting"}}
    entry = service.create_entry(db, foreign_brand.id, name=name, label="Other brand", languages=languages)
    entry_id = entry.id
    with admin(db) as (client, headers):
        listing = client.get("/expressions")
        changed = client.put(f"/expressions/{entry_id}", headers=headers,
                             json={"label": "Wrong brand", "languages": languages})
        deleted = client.delete(f"/expressions/{entry_id}", headers=headers)
    assert listing.status_code == 200
    assert name not in {item["name"] for item in listing.json()["items"]}
    assert [changed.status_code, deleted.status_code] == [404, 404]
    db.refresh(entry)
    assert (entry.brand_id, entry.label, entry.languages) == (foreign_brand.id, "Other brand", languages)
