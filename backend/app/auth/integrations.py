"""Machine principals: integrations, their credentials, their grants (ADR-166).

This sits in `app/auth/` rather than a package of its own, because ADR-166
point 1 makes a machine caller "a principal inside ADR-150's access model, not
a parallel authorization system" — and a second package is how a parallel
system starts.

**What this module does not do:** decide whether a request is allowed. That is
`policy.py` and `dependencies.py`, unchanged, for people and machines alike.
This module answers *who is calling*; the existing guard answers *may they*.
"""

import logging
import secrets
from datetime import datetime

from sqlalchemy.orm import Session

from app.auth.db_models import (
    IntegrationAuthFailureDB, IntegrationCredentialDB, IntegrationDB,
    IntegrationGrantDB,
)
from app.auth.permissions import ALL_PERMISSIONS
from app.auth.service import hash_secret, now

logger = logging.getLogger(__name__)

# The public half is prefixed so it is recognisable in a log line and in a
# customer's own configuration screen — "nri_" says what kind of thing this is
# without anyone having to look it up.
KEY_PREFIX = "nri_"


def new_key_id() -> str:
    return KEY_PREFIX + secrets.token_hex(8)


def new_secret() -> str:
    """256 bits from the system CSPRNG.

    **Why sha256 is the right hash for this and would not be for a password.**
    bcrypt and argon2 exist to make guessing expensive when the input is
    low-entropy — a human chose it, so the search space is small enough to walk.
    Nothing here is guessable: the secret is 32 random bytes, and there is no
    dictionary of those. A slow hash would buy nothing and would put a KDF on
    the hot path of every machine request.
    """
    return secrets.token_urlsafe(32)


# --- integrations -----------------------------------------------------------

def create_integration(
    db: Session, name: str, description: str | None = None,
    created_by_user_id: int | None = None, may_send_unattended: bool = False,
) -> IntegrationDB | None:
    label = (name or "").strip()
    if not label:
        return None
    integration = IntegrationDB(
        name=label,
        description=(description or "").strip() or None,
        created_by_user_id=created_by_user_id,
        # ADR-166 point 5: safe by default, and the caller has to say otherwise.
        may_send_unattended=bool(may_send_unattended),
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def deactivate_integration(db: Session, integration_id: int) -> bool:
    """Immediate, and it takes every credential beneath it with it.

    Nothing is deleted: the integration remains the audit actor for everything
    it already did, which is the whole reason history hangs off it rather than
    off a credential (point 3).
    """
    integration = db.query(IntegrationDB).filter(
        IntegrationDB.id == integration_id
    ).first()
    if integration is None:
        return False
    integration.is_active = False
    db.commit()
    return True


def set_unattended_sending(db: Session, integration_id: int, allowed: bool) -> bool:
    """ADR-166 point 5. The switch itself is the control, so it is logged.

    "The integration where someone switched it off is by construction the one
    with the least oversight. Logging the change is the whole control."
    """
    integration = db.query(IntegrationDB).filter(
        IntegrationDB.id == integration_id
    ).first()
    if integration is None:
        return False
    integration.may_send_unattended = bool(allowed)
    db.commit()
    logger.info(
        "integration %s: unattended sending %s",
        integration.id, "ENABLED" if allowed else "disabled",
    )
    return True


# --- grants -----------------------------------------------------------------

def grant(db: Session, integration_id: int, permission: str, brand_id: int) -> bool:
    """Grant one permission on one brand.

    A permission outside the vocabulary is refused rather than stored. Per
    `permissions.py`'s own rule a key names a code path, so an unknown key
    would guard nothing and would sit in the table looking like access.
    """
    if permission not in ALL_PERMISSIONS:
        logger.warning("integration grant refused: %r is not a permission", permission)
        return False
    existing = db.query(IntegrationGrantDB).filter(
        IntegrationGrantDB.integration_id == integration_id,
        IntegrationGrantDB.permission == permission,
        IntegrationGrantDB.brand_id == brand_id,
    ).first()
    if existing is not None:
        return True
    db.add(IntegrationGrantDB(
        integration_id=integration_id, permission=permission, brand_id=brand_id,
    ))
    db.commit()
    return True


def revoke_grant(db: Session, integration_id: int, permission: str, brand_id: int) -> bool:
    removed = db.query(IntegrationGrantDB).filter(
        IntegrationGrantDB.integration_id == integration_id,
        IntegrationGrantDB.permission == permission,
        IntegrationGrantDB.brand_id == brand_id,
    ).delete()
    db.commit()
    return bool(removed)


# --- credentials ------------------------------------------------------------

def issue_credential(
    db: Session, integration_id: int, label: str | None = None,
) -> tuple[IntegrationCredentialDB, str] | None:
    """Mint a key + secret. **The secret is returned once and never again.**

    ADR-152 §4 forbids the API returning a stored credential "under any
    circumstance, including to the Admin who set it", and a credential the
    platform issues is not an exception to that rule. The plaintext exists in
    this return value and nowhere else; what is stored is its hash.
    """
    integration = db.query(IntegrationDB).filter(
        IntegrationDB.id == integration_id
    ).first()
    if integration is None or not integration.is_active:
        return None

    secret = new_secret()
    credential = IntegrationCredentialDB(
        integration_id=integration_id,
        key_id=new_key_id(),
        secret_hash=hash_secret(secret),
        label=(label or "").strip() or None,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    logger.info(
        "integration %s: credential %s issued", integration_id, credential.key_id,
    )
    return credential, secret


def revoke_credential(db: Session, credential_id: int, at: datetime | None = None) -> bool:
    credential = db.query(IntegrationCredentialDB).filter(
        IntegrationCredentialDB.id == credential_id,
        IntegrationCredentialDB.revoked_at.is_(None),
    ).first()
    if credential is None:
        return False
    credential.revoked_at = at or now()
    db.commit()
    logger.info("integration credential %s revoked", credential.key_id)
    return True


def credentials_for(db: Session, integration_id: int) -> list[IntegrationCredentialDB]:
    return db.query(IntegrationCredentialDB).filter(
        IntegrationCredentialDB.integration_id == integration_id
    ).order_by(IntegrationCredentialDB.id).all()


# --- authentication ---------------------------------------------------------

def record_auth_failure(db: Session, key_id: str, client: str | None) -> None:
    """Count a failed attempt into its hour bucket (ADR-153 §6).

    Aggregated rather than one row per attempt, because these routes are
    reachable by an unauthenticated caller who can generate failures at will —
    a row-per-attempt table hands them a write primitive.

    **Never raises.** A failure to record a failure must not become a different
    failure for the caller: the request is being refused either way, and an
    exception here would turn a 401 into a 500 and tell an attacker that their
    input reached something.
    """
    try:
        window = now().replace(minute=0, second=0, microsecond=0)
        claimed = (key_id or "")[:64]
        client_hash = hash_secret(client or "unknown")
        row = db.query(IntegrationAuthFailureDB).filter(
            IntegrationAuthFailureDB.key_id == claimed,
            IntegrationAuthFailureDB.client_hash == client_hash,
            IntegrationAuthFailureDB.window_start == window,
        ).first()
        if row is None:
            db.add(IntegrationAuthFailureDB(
                key_id=claimed, client_hash=client_hash,
                window_start=window, attempts=1,
            ))
        else:
            row.attempts += 1
        db.commit()
    except Exception:  # pragma: no cover - defensive, see docstring
        db.rollback()
        logger.warning("integration auth: could not record a failed attempt")


def authenticate(db: Session, key_id: str, secret: str) -> IntegrationDB | None:
    """Resolve a key + secret to the integration behind it, or None.

    **One return value for every kind of failure** — unknown key, wrong secret,
    revoked credential, deactivated integration. Distinguishing them would tell
    an unauthenticated caller which of their guesses was closest, which is the
    enumeration oracle gate 4b closed on the human side, re-opened for machines.

    The comparison is constant-time. Comparing hashes with `==` leaks their
    common prefix through timing, and although deriving a 256-bit secret that
    way is not realistic, the constant-time call costs nothing and removes the
    need to argue about it.
    """
    if not key_id or not secret:
        return None

    credential = db.query(IntegrationCredentialDB).filter(
        IntegrationCredentialDB.key_id == key_id
    ).first()
    if credential is None:
        return None
    if credential.revoked_at is not None:
        return None
    if not secrets.compare_digest(credential.secret_hash, hash_secret(secret)):
        return None

    integration = db.query(IntegrationDB).filter(
        IntegrationDB.id == credential.integration_id
    ).first()
    if integration is None or not integration.is_active:
        return None

    # Written only on success. A failed attempt proves nothing about who holds
    # the key — anyone can name one — so recording it here would let an
    # outsider write to this row. Failures are counted in aggregate instead
    # (ADR-153 §6), which is stage 3's work alongside the guard.
    credential.last_used_at = now()
    db.commit()
    return integration
