"""
Tests for the signal layer (ADR-132): decay-on-read over the contribution log.

Assertions are made against contributions these tests create and then remove,
never against seeded values. Signals decay in real calendar time, so a test that
asserts "the seed's Beach signal is 90" passes the week it is written and fails
a month later without anything actually being broken.

Recipient id=1 (Anna) and category id=1 (Beach) are stable handles for *where* to
write, not a source of expected values.
"""
from datetime import datetime, timezone, timedelta

from app.database import SessionLocal
from app.insight.signals import (
    _decayed_weight,
    record_contribution,
    get_operational_signal,
    operational_signals_for_recipient,
    operational_signals_for_category,
    HALF_LIFE_DAYS,
)
from app.recipients.db_models import SignalContributionDB

# Registers every table in SQLAlchemy's metadata. Without it this module passes
# only when another test file happens to import `main` first: run alone, the
# signal_contributions -> categories foreign key cannot resolve and every test
# touching the DB errors. Order-dependent suites hide real failures.
import app.content.db_models  # noqa: F401
import app.campaigns.db_models  # noqa: F401
import app.delivery.db_models  # noqa: F401
import app.audience.db_models  # noqa: F401
import app.snapshots.db_models  # noqa: F401
import app.providers.db_models  # noqa: F401
import app.settings.db_models  # noqa: F401
import app.insight.db_models  # noqa: F401
import app.overrides.db_models  # noqa: F401
import app.ai.db_models  # noqa: F401

ANNA = 1
BEACH = 1


def _cleanup(contribution_id):
    db = SessionLocal()
    try:
        db.query(SignalContributionDB).filter(SignalContributionDB.id == contribution_id).delete()
        db.commit()
    finally:
        db.close()


class TestDecay:
    def test_no_decay_at_zero_age(self):
        now = datetime.now(timezone.utc)
        assert _decayed_weight(10.0, now, "click", now) == 10.0

    def test_halves_at_one_half_life(self):
        now = datetime.now(timezone.utc)
        age = timedelta(days=HALF_LIFE_DAYS["click"])
        assert abs(_decayed_weight(10.0, now - age, "click", now) - 5.0) < 1e-6

    def test_quarter_at_two_half_lives(self):
        now = datetime.now(timezone.utc)
        age = timedelta(days=2 * HALF_LIFE_DAYS["manual"])
        assert abs(_decayed_weight(80.0, now - age, "manual", now) - 20.0) < 1e-6

    def test_negative_contribution_stays_negative(self):
        now = datetime.now(timezone.utc)
        w = _decayed_weight(-50.0, now - timedelta(days=30), "unsubscribe", now)
        assert w < 0


class TestOperationalSignal:
    def test_fresh_manual_contribution_counts_at_full_weight(self):
        # A contribution recorded now should reach the signal essentially
        # undecayed. Written against a contribution this test creates, because
        # asserting on the seed's value silently rots: the seed ages in real
        # calendar time, so "90" became 37 without anything being broken.
        db = SessionLocal()
        c = None
        try:
            before = get_operational_signal(db, ANNA, BEACH)
            c = record_contribution(db, ANNA, BEACH, "manual", base_weight=90.0)
            after = get_operational_signal(db, ANNA, BEACH)
            assert abs((after - before) - 90.0) < 1.0
        finally:
            db.close()
            if c is not None:
                _cleanup(c.id)

    def test_signals_for_recipient_ranks_by_value(self):
        # Ranking is asserted against a contribution large enough to dominate
        # whatever else the database holds, rather than against a seeded
        # category that later data can overtake.
        db = SessionLocal()
        c = None
        try:
            existing = operational_signals_for_recipient(db, ANNA)
            dominant = max(existing.values(), default=0.0) + 100.0
            c = record_contribution(db, ANNA, BEACH, "manual", base_weight=dominant)
            sigs = operational_signals_for_recipient(db, ANNA)
            assert max(sigs, key=sigs.get) == BEACH
        finally:
            db.close()
            if c is not None:
                _cleanup(c.id)

    def test_new_contribution_raises_signal(self):
        db = SessionLocal()
        try:
            before = get_operational_signal(db, ANNA, BEACH)
            c = record_contribution(db, ANNA, BEACH, "click", base_weight=5.0)
            after = get_operational_signal(db, ANNA, BEACH)
            assert abs((after - before) - 5.0) < 1e-3
        finally:
            db.close()
        _cleanup(c.id)

    def test_signals_for_category_includes_recipient(self):
        db = SessionLocal()
        try:
            by_recipient = operational_signals_for_category(db, BEACH)
            assert by_recipient.get(ANNA, 0.0) > 0
        finally:
            db.close()


class TestConfigAffectsSignals:
    def test_half_life_override_changes_signal(self):
        from app.settings.service import set_config, HALF_LIFE_DAYS_KEY
        db = SessionLocal()
        try:
            baseline = get_operational_signal(db, ANNA, BEACH)
            # A tiny manual half-life makes even a fresh contribution decay hard.
            set_config(db, HALF_LIFE_DAYS_KEY, {"manual": 0.001})
            collapsed = get_operational_signal(db, ANNA, BEACH)
            assert collapsed < baseline
            # Clearing the override restores the code default.
            set_config(db, HALF_LIFE_DAYS_KEY, {})
            restored = get_operational_signal(db, ANNA, BEACH)
            assert abs(restored - baseline) < 1.0
        finally:
            db.close()
