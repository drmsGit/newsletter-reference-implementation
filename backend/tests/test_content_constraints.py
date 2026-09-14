"""Two check-then-insert races in the content module, and their backstops.

Both were flagged in the 2026-08-21 code-slimmer sweep (Cluster 3 C1 + C5) as
races already closed elsewhere — `uq_audience_group_members_group_recipient`
and `uq_module_instances_variant_position` were added for the identical
ambiguity on 2026-07-12. Content was missed.

**A race cannot be tested by hoping to hit it.** Each test here reproduces the
interleaving deliberately: the racing write is made from a *second* database
session at the exact moment the function under test is between its read and its
commit, which is the window the defect lives in. Without the constraint the
racing write simply succeeds alongside ours and the assertions below fail.

Runs against the shared dev database like the rest of the suite, and removes
everything it creates.
"""
import uuid

import pytest

from app.content import service as content_service
from app.content.db_models import (
    CategoryDB, ContentCategoryAssignmentDB, ContentRecordDB, ContentVersionDB,
)
from app.database import SessionLocal


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def temp_record(db):
    """A throwaway content record, removed with everything hanging off it."""
    created: list[int] = []

    def make() -> ContentRecordDB:
        record = ContentRecordDB(
            title=f"test-{uuid.uuid4().hex[:12]}",
            content={"headline_medium": "x"},
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        created.append(record.id)
        return record

    yield make

    for record_id in created:
        db.query(ContentVersionDB).filter(
            ContentVersionDB.content_record_id == record_id
        ).delete()
        db.query(ContentCategoryAssignmentDB).filter(
            ContentCategoryAssignmentDB.content_id == record_id
        ).delete()
        db.query(ContentRecordDB).filter(ContentRecordDB.id == record_id).delete()
    db.commit()


@pytest.fixture
def temp_category(db):
    category = CategoryDB(name=f"test-cat-{uuid.uuid4().hex[:8]}")
    db.add(category)
    db.commit()
    db.refresh(category)
    yield category
    db.query(ContentCategoryAssignmentDB).filter(
        ContentCategoryAssignmentDB.category_id == category.id
    ).delete()
    db.query(CategoryDB).filter(CategoryDB.id == category.id).delete()
    db.commit()


def _race_on_commit(monkeypatch, db, insert_conflicting_row):
    """Run a competing write from another session inside our commit.

    That is the TOCTOU window precisely: our caller has already read, decided,
    and called `db.add`, and has not yet committed. Patching `commit` is the
    only way to land another transaction in that gap deterministically.
    """
    original_commit = db.commit
    fired = {"once": False}

    def racing_commit():
        if not fired["once"]:
            fired["once"] = True
            with SessionLocal() as other:
                insert_conflicting_row(other)
                other.commit()
        return original_commit()

    monkeypatch.setattr(db, "commit", racing_commit)
    return fired


class TestDuplicateCategoryAssignment:

    def test_losing_the_race_answers_like_the_fast_path(
        self, db, temp_record, temp_category, monkeypatch
    ):
        """A caller must not be able to tell it lost a race.

        `assign_category` returns None when the assignment already exists. The
        racing case has to return None too — anything else (an exception, a
        row) makes the outcome depend on timing.
        """
        record = temp_record()

        _race_on_commit(monkeypatch, db, lambda other: other.add(
            ContentCategoryAssignmentDB(
                content_id=record.id, category_id=temp_category.id, score=5,
            )
        ))

        result = content_service.assign_category_to_content(
            db, content_id=record.id, category_id=temp_category.id, score=10,
        )

        assert result is None, (
            "a lost race did not answer like the fast path — without the unique "
            "constraint the duplicate row was simply stored"
        )

        rows = db.query(ContentCategoryAssignmentDB).filter(
            ContentCategoryAssignmentDB.content_id == record.id,
            ContentCategoryAssignmentDB.category_id == temp_category.id,
        ).count()
        assert rows == 1, f"{rows} assignment rows for one (content, category) pair"

    def test_the_ordinary_duplicate_path_still_works(
        self, db, temp_record, temp_category
    ):
        """The SELECT fast path, unraced — so the test above proves something."""
        record = temp_record()
        first = content_service.assign_category_to_content(
            db, content_id=record.id, category_id=temp_category.id, score=10,
        )
        assert first is not None
        assert content_service.assign_category_to_content(
            db, content_id=record.id, category_id=temp_category.id, score=10,
        ) is None


class TestConcurrentPublishVersionNumbers:

    def test_two_publishes_cannot_share_a_version_number(
        self, db, temp_record, monkeypatch
    ):
        """ADR-128: a version is the audit answer to "what did they receive?".

        Two rows sharing a number make `resolve_renderable_content`'s
        `ORDER BY version_number DESC ... .first()` pick one arbitrarily, so
        the audit answer becomes a coin toss. The constraint turns that silent
        corruption into a conflict, and the retry resolves it.
        """
        record = temp_record()
        first = content_service.create_content_version(db, record.id)
        assert first is not None and first.version_number == 1

        # Somebody else publishes version 2 while we are deciding to.
        _race_on_commit(monkeypatch, db, lambda other: other.add(
            ContentVersionDB(
                content_record_id=record.id, version_number=2, content={},
            )
        ))

        ours = content_service.create_content_version(db, record.id)

        assert ours is not None, "the retry gave up on an ordinary conflict"
        assert ours.version_number == 3, (
            f"got version {ours.version_number}, expected 3 — we took the number "
            "the concurrent publish had already used, which is exactly the "
            "ambiguity ADR-128's audit trail cannot tolerate"
        )

        numbers = [
            v.version_number
            for v in db.query(ContentVersionDB).filter(
                ContentVersionDB.content_record_id == record.id
            ).all()
        ]
        assert sorted(numbers) == [1, 2, 3], f"version numbers are {sorted(numbers)}"
        assert len(numbers) == len(set(numbers)), "a version number was reused"

    def test_uncontended_publishing_still_numbers_sequentially(self, db, temp_record):
        """The retry loop must not disturb the ordinary path."""
        record = temp_record()
        numbers = [
            content_service.create_content_version(db, record.id).version_number
            for _ in range(3)
        ]
        assert numbers == [1, 2, 3]
