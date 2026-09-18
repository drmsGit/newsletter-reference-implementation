"""The nine-to-sixteen permission split — ADR-166 point 2, ADR-150 point 5.

Two properties are worth pinning here, and they pull in opposite directions.

**The vocabulary must stay completely classified.** A permission is checked
against the working brand or across every grant, and ADR-150's addendum makes
that a property of the permission rather than of the role. A key nobody
classified answers "not brand-scoped", which is the fail-open direction — so
the test is that the classification covers the vocabulary exactly, not that it
contains the keys someone remembered.

**A split must not quietly take capability away.** Naming things more precisely
looks additive and is not: the moment `audiences.pin` exists, `audiences.manage`
stops implying it. The preset roles re-sync from code, so they heal themselves.
A company's own roles do not, which is what `migrate_0014_permission_split.sql`
is for — and what the last class here checks, against a role the sync is
designed never to touch.

Runs against the shared dev database like the rest of the suite, and removes
everything it creates.
"""
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from app.auth.db_models import RoleDB, RolePermissionDB
from app.auth.permissions import (
    ADMIN, ALL_PERMISSIONS, AUDIENCES_MANAGE, AUDIENCES_PIN, BRAND_SCOPED,
    BUILTIN_ROLES, CAMPAIGNS_MANAGE, INSIGHT_WRITE, INTEGRATIONS_MANAGE,
    MANAGER, OVERRIDES_MANAGE, RECIPIENTS_CONSENT, RECIPIENTS_MANAGE,
    SENDS_EXECUTE, SENDS_PLAN, is_brand_scoped,
)
from app.database import SessionLocal

MIGRATION = Path("scripts/migrate_0014_permission_split.sql")


@pytest.fixture
def session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestTheVocabularyIsComplete:

    def test_sixteen_keys(self):
        assert len(ALL_PERMISSIONS) == 16, sorted(ALL_PERMISSIONS)

    def test_every_key_is_classified_exactly_once(self):
        """ADR-150 point 5 lists 7 brand-scoped and 9 platform-level.

        Asserted as a partition of the vocabulary rather than as two lists, so
        adding a key without classifying it fails here instead of silently
        answering "platform-level" — which is the permissive answer.
        """
        brand_scoped = {k for k in ALL_PERMISSIONS if is_brand_scoped(k)}
        platform = set(ALL_PERMISSIONS) - brand_scoped

        assert brand_scoped == {
            "content.manage", "campaigns.manage", "audiences.manage",
            "audiences.pin", "sends.plan", "sends.execute", "overrides.manage",
        }
        assert len(platform) == 9
        assert brand_scoped | platform == set(ALL_PERMISSIONS)

    def test_brand_scoped_contains_nothing_unknown(self):
        """The three pre-classified keys were strings before their guards
        existed. If one were misspelled, it would sit in BRAND_SCOPED forever
        matching nothing, and its real key would be platform-level by default.
        """
        assert BRAND_SCOPED <= set(ALL_PERMISSIONS), BRAND_SCOPED - set(ALL_PERMISSIONS)

    def test_recipient_import_does_not_imply_asserting_consent(self):
        assert RECIPIENTS_CONSENT != RECIPIENTS_MANAGE
        assert RECIPIENTS_CONSENT in ALL_PERMISSIONS


class TestThePresetRolesKeepWhatTheyHad:

    def test_manager_still_holds_every_act_it_could_perform_before(self):
        """Each of these was reachable under a coarser key the Manager held."""
        manager = set(BUILTIN_ROLES[MANAGER]["permissions"])
        assert AUDIENCES_PIN in manager, "could pin under audiences.manage"
        assert SENDS_PLAN in manager, "could plan under sends.execute"
        assert OVERRIDES_MANAGE in manager, "could override under campaigns.manage"
        assert {AUDIENCES_MANAGE, SENDS_EXECUTE, CAMPAIGNS_MANAGE} <= manager

    def test_manager_gains_nothing_that_guards_no_ui(self):
        """The split is not an excuse to hand out the new machine-facing keys."""
        manager = set(BUILTIN_ROLES[MANAGER]["permissions"])
        for key in (RECIPIENTS_MANAGE, RECIPIENTS_CONSENT, INSIGHT_WRITE,
                    INTEGRATIONS_MANAGE):
            assert key not in manager, key

    def test_admin_holds_the_whole_vocabulary(self):
        assert set(BUILTIN_ROLES[ADMIN]["permissions"]) == set(ALL_PERMISSIONS)


class TestTheMigrationCoversWhatTheSyncWillNot:
    """`ensure_builtin_roles` re-syncs the presets on every startup and
    deliberately skips a customised built-in and a company's own roles. Those
    are exactly the rows that would silently lose capability, so they are the
    rows tested here."""

    @pytest.fixture
    def custom_role(self, session):
        role = RoleDB(
            key=f"permtest-{uuid.uuid4().hex[:8]}",
            name="Permission split test role",
            description="A company's own role — the sync never touches it.",
            is_builtin=False,
        )
        session.add(role)
        session.commit()
        session.refresh(role)
        for permission in (AUDIENCES_MANAGE, SENDS_EXECUTE, CAMPAIGNS_MANAGE):
            session.add(RolePermissionDB(role_id=role.id, permission=permission))
        session.commit()
        try:
            yield role
        finally:
            # Roll back FIRST. A test that fails on a bad statement leaves the
            # transaction aborted, and Postgres then refuses every further
            # command on that connection — including this cleanup. The first
            # version of this fixture skipped the rollback and leaked fourteen
            # roles across one broken migration and four mutation runs: the
            # teardown ran, and could not do anything. Reaching the teardown is
            # not the same as the teardown working.
            session.rollback()
            session.query(RolePermissionDB).filter(
                RolePermissionDB.role_id == role.id
            ).delete()
            session.query(RoleDB).filter(RoleDB.id == role.id).delete()
            session.commit()

    def _run_migration(self, session):
        """Strip comments BEFORE splitting on semicolons.

        The naive order — split, then skip chunks that start with `--` — was
        written first and broke on a semicolon inside a prose comment: it cut
        the sentence in half and handed the remainder to Postgres as SQL. Any
        correct runner removes comments first, and so does this one, because
        the next migration will have prose with punctuation in it too.
        """
        sql = "\n".join(
            line for line in MIGRATION.read_text().splitlines()
            if not line.strip().startswith("--")
        )
        for statement in sql.split(";"):
            if statement.strip():
                session.execute(text(statement))
        session.commit()

    def _held(self, session, role):
        return {
            row.permission
            for row in session.query(RolePermissionDB).filter(
                RolePermissionDB.role_id == role.id
            ).all()
        }

    def test_the_split_off_keys_arrive(self, session, custom_role):
        assert AUDIENCES_PIN not in self._held(session, custom_role)

        self._run_migration(session)

        held = self._held(session, custom_role)
        assert AUDIENCES_PIN in held, "a role that could pin yesterday cannot today"
        assert SENDS_PLAN in held, "a role that could plan yesterday cannot today"
        assert OVERRIDES_MANAGE in held, "a role that could override yesterday cannot"

    def test_nothing_is_revoked(self, session, custom_role):
        """Grant-only. Splitting is a chance to grant less, and taking it inside
        a migration would be a security decision made by a refactor."""
        before = self._held(session, custom_role)
        self._run_migration(session)
        assert before <= self._held(session, custom_role)

    def test_the_unguarded_keys_are_not_handed_out(self, session, custom_role):
        """These guard routes that had no guard at all — the defect ADR-166
        closes. Granting them on the way past would hand out access nobody has
        today."""
        self._run_migration(session)
        held = self._held(session, custom_role)
        for key in (RECIPIENTS_MANAGE, RECIPIENTS_CONSENT, INSIGHT_WRITE,
                    INTEGRATIONS_MANAGE):
            assert key not in held, key

    def test_it_is_idempotent(self, session, custom_role):
        self._run_migration(session)
        once = self._held(session, custom_role)
        self._run_migration(session)
        assert self._held(session, custom_role) == once
