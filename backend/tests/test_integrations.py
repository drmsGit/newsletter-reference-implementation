"""Machine principals — ADR-166 stage 2 (the model), accepted 2026-09-18.

**The test that carries the ADR's central claim** is the last one in
`TestOnePrincipalModel`: a person and an integration granted the same
permission on the same brand must be indistinguishable to `has_permission`.
Point 1 refuses a parallel authorization system, and the way that promise dies
is not with a second system announced as such — it dies with the two shapes
drifting until each answers "may this caller do this here" its own way. The
assertion is cheap and it is the one that would notice.

Everything else here is the failure surface: one return value for every kind of
authentication failure, a secret that exists exactly once, and revocation that
takes effect now rather than at an expiry.

Runs against the shared dev database like the rest of the suite, and removes
everything it creates.
"""
import uuid

import pytest

from app.auth import integrations as ints
from app.auth import service as auth
from app.auth.db_models import (
    BrandDB, IntegrationCredentialDB, IntegrationDB, IntegrationGrantDB,
    RoleAssignmentDB, RoleDB, UserDB,
)
from app.auth.permissions import (
    INSIGHT_WRITE, RECIPIENTS_CONSENT, SENDS_EXECUTE, VIEW,
)
from app.database import SessionLocal

TAG = "inttest"


@pytest.fixture
def session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def brand(session):
    b = BrandDB(key=f"{TAG}-{uuid.uuid4().hex[:8]}", name="Integration test brand")
    session.add(b)
    session.commit()
    session.refresh(b)
    try:
        yield b
    finally:
        # Roll back first: a test that failed mid-statement leaves the
        # transaction aborted, and Postgres then refuses the cleanup too.
        # Learned the hard way in the permission-split fixture, which leaked
        # thirteen roles by running a teardown that could not do anything.
        session.rollback()
        session.query(IntegrationGrantDB).filter(
            IntegrationGrantDB.brand_id == b.id
        ).delete()
        session.query(RoleAssignmentDB).filter(
            RoleAssignmentDB.brand_id == b.id
        ).delete()
        session.query(BrandDB).filter(BrandDB.id == b.id).delete()
        session.commit()


@pytest.fixture
def integration(session):
    made = ints.create_integration(
        session, name=f"{TAG} n8n {uuid.uuid4().hex[:6]}",
        description="A test orchestrator.",
    )
    try:
        yield made
    finally:
        session.rollback()
        session.query(IntegrationCredentialDB).filter(
            IntegrationCredentialDB.integration_id == made.id
        ).delete()
        session.query(IntegrationGrantDB).filter(
            IntegrationGrantDB.integration_id == made.id
        ).delete()
        session.query(IntegrationDB).filter(IntegrationDB.id == made.id).delete()
        session.commit()


class TestCredentials:

    def test_the_secret_is_returned_once_and_stored_only_as_a_hash(
        self, session, integration
    ):
        credential, secret = ints.issue_credential(session, integration.id, "primary")

        assert secret and len(secret) >= 40
        assert credential.key_id.startswith(ints.KEY_PREFIX)
        assert credential.secret_hash != secret, "the secret itself must not be stored"
        assert secret not in credential.secret_hash

        # ADR-152 §4: nothing may hand a stored credential back, including to
        # the Admin who set it. There is no read path, so the assertion is that
        # the row does not carry one.
        stored = session.query(IntegrationCredentialDB).filter(
            IntegrationCredentialDB.id == credential.id
        ).first()
        assert not hasattr(stored, "secret"), "a plaintext column would defeat the rule"

    def test_two_credentials_under_one_integration_are_distinguishable(
        self, session, integration
    ):
        first, _ = ints.issue_credential(session, integration.id, "old")
        second, _ = ints.issue_credential(session, integration.id, "new")
        assert first.key_id != second.key_id

    def test_a_deactivated_integration_issues_nothing(self, session, integration):
        ints.deactivate_integration(session, integration.id)
        assert ints.issue_credential(session, integration.id) is None


class TestAuthentication:

    def test_a_valid_pair_resolves_to_the_integration(self, session, integration):
        credential, secret = ints.issue_credential(session, integration.id)
        resolved = ints.authenticate(session, credential.key_id, secret)
        assert resolved is not None and resolved.id == integration.id

    def test_success_stamps_last_used(self, session, integration):
        credential, secret = ints.issue_credential(session, integration.id)
        assert credential.last_used_at is None
        ints.authenticate(session, credential.key_id, secret)
        session.refresh(credential)
        assert credential.last_used_at is not None

    def test_a_failure_stamps_nothing(self, session, integration):
        """Anyone can name a key they do not hold.

        If a failed attempt wrote to this row, an outsider could keep a
        revoked-looking key permanently 'recently used'.
        """
        credential, _ = ints.issue_credential(session, integration.id)
        ints.authenticate(session, credential.key_id, "not-the-secret")
        session.refresh(credential)
        assert credential.last_used_at is None

    @pytest.mark.parametrize("case", ["wrong_secret", "unknown_key", "empty"])
    def test_every_kind_of_failure_answers_the_same(self, session, integration, case):
        """One return value, so nothing tells a caller which guess was closest.

        Distinguishing them is the enumeration oracle gate 4b closed on the
        human side, re-opened for machines.
        """
        credential, secret = ints.issue_credential(session, integration.id)
        attempts = {
            "wrong_secret": (credential.key_id, secret + "x"),
            "unknown_key": ("nri_deadbeefdeadbeef", secret),
            "empty": ("", ""),
        }
        assert ints.authenticate(session, *attempts[case]) is None

    def test_revocation_takes_effect_immediately(self, session, integration):
        credential, secret = ints.issue_credential(session, integration.id)
        assert ints.authenticate(session, credential.key_id, secret) is not None

        assert ints.revoke_credential(session, credential.id) is True
        assert ints.authenticate(session, credential.key_id, secret) is None

    def test_deactivating_the_integration_kills_every_key_beneath_it(
        self, session, integration
    ):
        first, secret_a = ints.issue_credential(session, integration.id)
        second, secret_b = ints.issue_credential(session, integration.id)

        ints.deactivate_integration(session, integration.id)

        assert ints.authenticate(session, first.key_id, secret_a) is None
        assert ints.authenticate(session, second.key_id, secret_b) is None


class TestRotationKeepsTheActor:

    def test_the_integration_survives_its_credentials(self, session, integration, brand):
        """Point 3's whole reason for two tables.

        Attribution has to still read "n8n triggered this" a year and three
        rotations later. If the credential were the actor, revoking it would
        leave the history pointing at nothing.
        """
        ints.grant(session, integration.id, SENDS_EXECUTE, brand.id)
        old, _ = ints.issue_credential(session, integration.id, "old")
        new, secret = ints.issue_credential(session, integration.id, "new")
        ints.revoke_credential(session, old.id)

        still = ints.authenticate(session, new.key_id, secret)
        assert still is not None and still.id == integration.id
        assert auth.has_permission(session, still, SENDS_EXECUTE, brand_id=brand.id)


class TestGrants:

    def test_a_grant_is_scoped_to_its_brand(self, session, integration, brand):
        ints.grant(session, integration.id, SENDS_EXECUTE, brand.id)
        session.refresh(integration)

        assert auth.has_permission(session, integration, SENDS_EXECUTE, brand_id=brand.id)
        assert not auth.has_permission(
            session, integration, SENDS_EXECUTE, brand_id=brand.id + 9999
        )

    def test_a_permission_outside_the_vocabulary_is_refused(
        self, session, integration, brand
    ):
        """A key names a code path. An invented one would guard nothing and sit
        in the table looking like access."""
        assert ints.grant(session, integration.id, "sends.obliterate", brand.id) is False
        assert auth.permissions_for(session, integration) == set()

    def test_view_is_not_implied_for_a_machine(self, session, integration, brand):
        """Every *role* implies `view`, because a person who may edit and not
        read is not worth modelling. For a machine it is the ordinary case —
        n8n triggers a send and reads nothing. Implying it would hand every
        integration the recipient list, which is one of the four routes
        ADR-166's Context names as the reason the feature exists.
        """
        ints.grant(session, integration.id, INSIGHT_WRITE, brand.id)
        held = auth.permissions_for(session, integration)
        assert held == {INSIGHT_WRITE}
        assert VIEW not in held

    def test_importing_a_contact_does_not_imply_asserting_consent(
        self, session, integration, brand
    ):
        ints.grant(session, integration.id, "recipients.manage", brand.id)
        assert not auth.has_permission(session, integration, RECIPIENTS_CONSENT)

    def test_revoking_a_grant_removes_it(self, session, integration, brand):
        ints.grant(session, integration.id, SENDS_EXECUTE, brand.id)
        assert ints.revoke_grant(session, integration.id, SENDS_EXECUTE, brand.id)
        assert not auth.has_permission(session, integration, SENDS_EXECUTE)

    def test_granting_twice_is_not_an_error(self, session, integration, brand):
        assert ints.grant(session, integration.id, SENDS_EXECUTE, brand.id)
        assert ints.grant(session, integration.id, SENDS_EXECUTE, brand.id)
        assert len(session.query(IntegrationGrantDB).filter(
            IntegrationGrantDB.integration_id == integration.id
        ).all()) == 1


class TestOnePrincipalModel:
    """ADR-166 point 1, as an assertion rather than an intention."""

    @pytest.fixture
    def user_with_sends(self, session, brand):
        user = UserDB(email=f"{TAG}-{uuid.uuid4().hex[:8]}@example.test", is_active=True)
        session.add(user)
        session.commit()
        session.refresh(user)
        role = session.query(RoleDB).filter(RoleDB.key == "manager").first()
        session.add(RoleAssignmentDB(user_id=user.id, role_id=role.id, brand_id=brand.id))
        session.commit()
        try:
            yield user
        finally:
            session.rollback()
            session.query(RoleAssignmentDB).filter(
                RoleAssignmentDB.user_id == user.id
            ).delete()
            session.query(UserDB).filter(UserDB.id == user.id).delete()
            session.commit()

    def test_a_person_and_a_machine_with_the_same_grant_answer_the_same(
        self, session, integration, brand, user_with_sends
    ):
        ints.grant(session, integration.id, SENDS_EXECUTE, brand.id)

        for principal in (user_with_sends, integration):
            assert auth.has_permission(
                session, principal, SENDS_EXECUTE, brand_id=brand.id
            ) is True, principal
            assert auth.has_permission(
                session, principal, SENDS_EXECUTE, brand_id=brand.id + 9999
            ) is False, principal

    def test_an_inactive_principal_holds_nothing_in_either_shape(
        self, session, integration, brand, user_with_sends
    ):
        ints.grant(session, integration.id, SENDS_EXECUTE, brand.id)
        user_with_sends.is_active = False
        ints.deactivate_integration(session, integration.id)
        session.commit()
        session.refresh(integration)

        for principal in (user_with_sends, integration):
            assert auth.permissions_for(session, principal) == set(), principal

    def test_no_principal_holds_nothing(self, session):
        assert auth.permissions_for(session, None) == set()


class TestUnattendedSending:

    def test_it_defaults_to_requiring_approval(self, session, integration):
        """ADR-166 point 5: the most destructive capability in the system is
        not the one that defaults open."""
        assert integration.may_send_unattended is False

    def test_it_can_be_switched_on_deliberately(self, session, integration):
        assert ints.set_unattended_sending(session, integration.id, True)
        session.refresh(integration)
        assert integration.may_send_unattended is True
