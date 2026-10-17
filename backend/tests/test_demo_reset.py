"""The Grathaus demo reset (task-71).

What these pin: the catalogue reads what the external model writes and
reports, never guesses, what it cannot use; the category tree and the
readers' interests fit the send cap, which stays 200; every table is either
kept or emptied, so a new table cannot slip through unclassified; the command
asks for --yes and refuses the test database; and one full run builds the two
brands, their profiles, the linked translations, the readers and the
editions sent through the real path — then the suite's baseline is restored.
"""
import csv
from pathlib import Path

import pytest

from app.demo import catalogue, editions, people
from app.demo.reset import EMPTIED, KEPT, TOUREN_KEY

HEADER = list(catalogue.COLUMNS)


def _row(**values) -> dict:
    row = {c: "" for c in HEADER}
    row.update(brand="outdoor", language="de", title="Zur Kampenwand", description="Eine Tagestour.",
               headline_medium="Zur Kampenwand", body_medium="Vier Stunden, 900 Höhenmeter.",
               button_label="Zur Route", button_url="https://www.grathaus.example/kampenwand",
               image="wanderweg_herbst", image_alt="Ein Pfad im Herbstwald", categories="Tagestouren:9|Wandern:5")
    row.update(values)
    return row


def _write(path: Path, rows: list[dict]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    return path


# --- reading what the external model wrote -------------------------------------------------

def test_a_batch_row_is_read_with_its_content_scores_and_image(tmp_path):
    read = catalogue.read_csv(_write(tmp_path / "batch-1.csv", [_row(push_title="Kampenwand", push_body="Los.")]))
    assert read.problems == []
    [row] = read.rows
    assert row.scores == {"Tagestouren": 9, "Wandern": 5} and row.image == "wanderweg_herbst"
    assert row.content["headline_medium"] == "Zur Kampenwand" and row.content["push_title"] == "Kampenwand"
    assert "image" not in row.content and "categories" not in row.content


@pytest.mark.parametrize("change, problem", [
    ({"categories": "Tagestouren:9|Strand:7"}, "unknown category 'Strand'"),
    ({"categories": "Tagestouren:12"}, "not a score from 1 to 10"),
    ({"brand": "shop"}, "unknown brand"),
    ({"language": "fr"}, "unknown language"),
    ({"image": "sonnenuntergang"}, "unknown image key"),
])
def test_what_cannot_be_used_is_reported_not_guessed(tmp_path, change, problem):
    read = catalogue.read_csv(_write(tmp_path / "batch-1.csv", [_row(**change)]))
    assert any(problem in p for p in read.problems), read.problems


def test_smart_quotes_from_a_chat_answer_are_read(tmp_path):
    path = _write(tmp_path / "batch-1.csv", [_row()])
    path.write_text(path.read_text(encoding="utf-8").replace('"', "“"), encoding="utf-8")
    assert len(catalogue.read_csv(path).rows) == 1


def test_english_rows_come_last_and_a_doubled_title_is_skipped(tmp_path):
    _write(tmp_path / "english.csv", [_row(language="en", title="To the Kampenwand")])
    _write(tmp_path / "batch-1.csv", [_row(), _row()])
    read = catalogue.read_all(tmp_path)
    assert [r.language for r in read.rows] == ["de", "en"]
    assert any("appears twice" in p for p in read.problems)


# --- shapes that must fit ---------------------------------------------------------------------

def test_the_tree_has_three_subs_under_two_parents_and_only_known_parents():
    names = {name for name, _t, _p in catalogue.TREE}
    assert all(parent in names for _n, _t, parents in catalogue.TREE for parent in parents)
    assert {n for n, _t, parents in catalogue.TREE if len(parents) == 2} == {
        "Klettersteige", "Familienwandern", "Lawinenkunde"}


def test_every_main_interest_fits_one_send_and_the_readers_are_about_a_thousand():
    assert all(count < 200 for count in people.MAIN_INTERESTS.values())
    assert people.TOTAL == 1000
    assert set(people.SUBS_OF) == set(people.MAIN_INTERESTS)


def test_every_table_is_kept_or_emptied():
    import main  # noqa: F401 — registers every model
    from app.database import Base

    assert set(EMPTIED) & set(KEPT) == set()
    assert set(EMPTIED) | set(KEPT) == set(Base.metadata.tables)


def test_the_command_asks_first_and_refuses_the_test_database(capsys):
    from scripts import demo_reset

    assert demo_reset.main([]) == 2
    assert demo_reset.main(["--yes"]) == 3
    assert "Refused" in capsys.readouterr().out


# --- one full run -----------------------------------------------------------------------------

def _fixture(tmp_path: Path) -> Path:
    content = tmp_path / "content"
    content.mkdir()
    rows = []
    for name, _type, _parents in catalogue.TREE:
        for n in range(3):
            slug = f"{name}-{n}".lower().replace(" ", "-").replace("&", "und")
            rows.append(_row(title=f"{name} {n}", headline_medium=f"{name} {n}", headline_hero=f"{name} {n}",
                             button_url=f"https://www.grathaus.example/{slug}", categories=f"{name}:9",
                             push_title=f"{name}", push_body="Jetzt im Laden."))
    rows.append(_row(brand="touren", title="Hüttenwochenende", categories="Hüttentouren:9",
                     button_url="https://touren.grathaus.example/huetten"))
    _write(content / "batch-1.csv", rows)
    _write(content / "english.csv", [_row(language="en", title="Day hikes 0", headline_medium="Day hikes 0",
                                          button_url="https://www.grathaus.example/tagestouren-0",
                                          categories="Tagestouren:9")])
    with (content / "editions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
        writer.writerow(["kind", "key", "brand", "subject", "preheader", "editorial"])
        for edition in editions.EDITIONS:
            writer.writerow(["edition", edition.key, edition.brand, f"Betreff {edition.key}", "Vorschau",
                             "{{salutation_formal}},\nHerzlich willkommen."])
        writer.writerow(["transactional", "bestellbestaetigung", "outdoor", "Ihre Bestellung", "", "Danke."])
        writer.writerow(["transactional", "buchungsbestaetigung", "touren", "Ihre Buchung", "", "Danke."])
    return content


def test_a_full_run_builds_grathaus_and_keeps_people_and_settings(tmp_path):
    from app.audit.db_models import AuditEventDB
    from app.auth.db_models import BrandDB, UserDB
    from app.auth.service import ensure_default_brand
    from app.brand_profiles.db_models import BrandProfileDB
    from app.content.db_models import ContentRecordDB
    from app.database import SessionLocal
    from app.delivery.db_models import DeliveryExecutionDB, SendInstanceDB
    from app.demo.reset import run
    from app.recipients.db_models import ConsentEventDB, RecipientDB
    from app.settings.db_models import AppConfigDB

    db = SessionLocal()
    users_before = db.query(UserDB).count()
    config_before = {c.key: c.value for c in db.query(AppConfigDB)}
    default_name = ensure_default_brand(db).name
    try:
        outcome = run(db, content_dir=_fixture(tmp_path), images_dir=tmp_path / "no-images", send_cap=200)
        db.expire_all()
        brands = {b.key: b.name for b in db.query(BrandDB)}
        outdoor = ensure_default_brand(db)
        assert outdoor.name == "Grathaus Outdoor" and brands[TOUREN_KEY] == "Grathaus Touren" and len(brands) == 2
        assert {(p.language, p.kind) for p in db.query(BrandProfileDB).filter_by(brand_id=outdoor.id)} == {
            ("de", "marketing"), ("en", "marketing"), ("de", "transactional")}
        english = db.query(ContentRecordDB).filter_by(language="en").one()
        assert db.get(ContentRecordDB, english.translation_of_id).title == "Tagestouren 0"
        assert db.query(RecipientDB).count() == 1000
        sends = db.query(SendInstanceDB).all()
        assert len(sends) == sum(1 for e in editions.EDITIONS if e.sent)
        for send in sends:
            delivered = db.query(DeliveryExecutionDB).filter_by(send_instance_id=send.id, status="sent").count()
            assert 0 < delivered <= 200
        assert db.query(ConsentEventDB).filter_by(source="unsubscribe").count() == 1
        assert db.query(UserDB).count() == users_before
        assert {c.key: c.value for c in db.query(AppConfigDB)} == config_before
        assert db.query(AuditEventDB).filter_by(action="demo.reset").count() >= 1
        assert any("no file" in p for p in outcome.problems)   # no images given: said, not faked
    finally:
        # The suite's baseline again: empty what the run made (its own step),
        # take the Touren brand away, and seed as conftest does.
        from app.auth.db_models import RoleAssignmentDB
        from app.demo.reset import empty, remove_image_files
        from scripts import seed_demo_data

        db.rollback()
        remove_image_files(empty(db))
        touren = db.query(BrandDB).filter_by(key=TOUREN_KEY).first()
        if touren is not None:
            db.query(RoleAssignmentDB).filter_by(brand_id=touren.id).delete()
            db.query(BrandDB).filter_by(id=touren.id).delete()
        brand = ensure_default_brand(db)
        brand.name = default_name
        brand.expressions_started_at = None
        db.commit()
        db.close()
        # The seed draws from the module-level random stream it seeds once at
        # import; seeding again here gives the same baseline the suite started with.
        import random

        random.seed(42)
        seed_demo_data.seed()


def test_a_prefixed_batch_name_from_a_download_is_read(tmp_path):
    _write(tmp_path / "grathaus-outdoor-batch-1.csv", [_row()])
    assert len(catalogue.read_all(tmp_path).rows) == 1


def test_a_brand_someone_is_signed_in_to_is_still_removed():
    """Found running the reset on the dev database (2026-10-17): a session
    whose working brand was one of the removed ones stopped the reset with a
    foreign-key error. The session stays and falls back to no working brand,
    the state the column documents; its owner is not signed out."""
    import uuid
    from datetime import timedelta

    from app.auth.db_models import BrandDB, SessionDB, UserDB
    from app.database import SessionLocal
    from app.demo.reset import remove_brands
    from app.auth.service import now

    db = SessionLocal()
    tag = uuid.uuid4().hex[:8]
    try:
        brand = BrandDB(key=f"gone-{tag}", name=f"Gone {tag}")
        user = UserDB(email=f"reset-{tag}@example.invalid", is_active=True)
        db.add_all([brand, user])
        db.flush()
        session = SessionDB(user_id=user.id, token_hash=f"h-{tag}".ljust(64, "0"), brand_id=brand.id,
                            expires_at=now() + timedelta(hours=1))
        db.add(session)
        db.commit()
        brand_id, session_id = brand.id, session.id

        remove_brands(db, [brand_id])
        db.commit()
        db.expunge_all()

        assert db.get(BrandDB, brand_id) is None
        kept = db.get(SessionDB, session_id)
        assert kept is not None and kept.brand_id is None
    finally:
        db.rollback()
        db.query(SessionDB).filter(SessionDB.token_hash == f"h-{tag}".ljust(64, "0")).delete()
        db.query(UserDB).filter(UserDB.email == f"reset-{tag}@example.invalid").delete()
        db.query(BrandDB).filter(BrandDB.key == f"gone-{tag}").delete()
        db.commit()
        db.close()
