"""A machine principal for tests that drive the JSON API (ADR-166).

Since 2026-09-18 the JSON routers take a platform-issued integration credential
and nothing else — no session cookie, deliberately, because that is what makes
CSRF a non-question on the machine plane. Tests that call those routes have to
authenticate like the machines they stand in for, which is better coverage than
they had: before this, `test_overrides.py` proved the override API worked for
*anybody*, which was the defect.

Each context manager mints its own integration and removes it, so a test file
cannot leave a working credential behind in the shared dev database.
"""
import uuid
from contextlib import contextmanager

from app.auth import integrations as ints
from app.auth.db_models import (
    IntegrationCredentialDB, IntegrationDB, IntegrationGrantDB,
)
from app.auth.service import ensure_default_brand
from app.database import SessionLocal

TAG = "apitest"


@contextmanager
def machine(permissions, brand_id: int | None = None):
    """Yield request headers for an integration holding `permissions`.

    The `X-Brand` header is always sent, because a brand-scoped permission with
    no declared brand is refused (ADR-166 point 8) and a test that forgot it
    would fail for a reason unrelated to what it is testing. The one test that
    *should* omit it asserts the refusal directly instead.
    """
    db = SessionLocal()
    integration = None
    try:
        brand = brand_id or ensure_default_brand(db).id
        integration = ints.create_integration(
            db, name=f"{TAG}-{uuid.uuid4().hex[:8]}",
            description="Minted by the test suite.",
        )
        for permission in permissions:
            assert ints.grant(db, integration.id, permission, brand), permission
        credential, secret = ints.issue_credential(db, integration.id, "test")
        yield {
            "Authorization": f"Bearer {credential.key_id}.{secret}",
            "X-Brand": str(brand),
        }
    finally:
        # Roll back before cleaning up: a test that failed mid-statement leaves
        # the transaction aborted, and Postgres refuses the cleanup too.
        db.rollback()
        if integration is not None:
            for model in (IntegrationCredentialDB, IntegrationGrantDB):
                db.query(model).filter(
                    model.integration_id == integration.id
                ).delete()
            db.query(IntegrationDB).filter(
                IntegrationDB.id == integration.id
            ).delete()
            db.commit()
        db.close()
