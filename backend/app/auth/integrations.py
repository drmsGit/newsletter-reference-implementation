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
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.auth.db_models import (
    IntegrationAuthFailureDB, IntegrationCredentialDB, IntegrationDB,
    IntegrationGrantDB,
)
from app.auth.permissions import ALL_PERMISSIONS
from app.auth.service import has_permission, hash_secret, list_brands, now

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
    created_by_user_id: int | None = None,
) -> IntegrationDB | None:
    label = (name or "").strip()
    if not label:
        return None
    integration = IntegrationDB(
        name=label,
        description=(description or "").strip() or None,
        created_by_user_id=created_by_user_id,
        # ADR-166 point 5: safe by default, a ceiling of 0; somebody has to
        # raise it on purpose, and that is gated and logged.
        unattended_ceiling=0,
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


#: What the screen suggests when unattended sending is switched on (task-341).
SUGGESTED_UNATTENDED_CEILING = 100


def unattended_ceiling(integration) -> int:
    """How many recipients this integration may send to without a person
    (ADR-166, addenda of 2026-10-09 and 2026-10-11). 0: never."""
    return int(getattr(integration, "unattended_ceiling", 0) or 0)


def set_unattended_ceiling(db: Session, integration_id: int, ceiling: int) -> bool:
    """Set the ceiling, 0 to the company-wide cap (task-341). Raises
    ValueError outside that range. The change is the control, so the caller
    logs it (`record_change`)."""
    from app.settings.service import get_max_send_recipients

    cap = get_max_send_recipients(db)
    if not isinstance(ceiling, int) or isinstance(ceiling, bool) or ceiling < 0:
        raise ValueError("The ceiling is a whole number of recipients, 0 or more.")
    if ceiling > cap:
        raise ValueError(f"The ceiling cannot be above the company-wide cap of {cap} recipients.")
    integration = db.query(IntegrationDB).filter(IntegrationDB.id == integration_id).first()
    if integration is None:
        return False
    integration.unattended_ceiling = ceiling
    db.commit()
    logger.info("integration %s: unattended ceiling %s", integration.id, ceiling)
    return True


def record_change(request, db: Session, action: str, integration_id: int, **detail) -> None:
    """Audit one change to an integration, for both planes (task-50).

    The integration is the subject. The brand is the grant's when the change
    names one; otherwise none, since an integration is platform-level. Never a
    secret — `key_id` is the public half.
    """
    from app.audit import service as audit

    audit.record_from_request(
        request, db, action, subject_type="integration", subject_id=integration_id,
        brand_id=detail.get("brand_id"), detail=detail or None,
    )


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


class GrantForbidden(ValueError):
    """The person granting does not hold what they were asked to give."""


def grant_by_person(
    db: Session, actor, integration_id: int, permission: str, brand_id: int,
    *, enforced: bool = True,
) -> bool:
    """`grant`, for a person: **they may give only what they hold** (task-50).

    ADR-166's addendum of 2026-10-02. Until then any holder of
    `integrations.manage` could grant any permission on any brand, so an Admin
    of brand A could hand a machine `sends.execute` on brand B — a power they
    did not themselves have. Now `permission` on `brand_id` must be one the
    actor holds on THAT brand — for platform-level permissions too. A grant row
    on a brand lets the machine declare that brand in `X-Brand` (the guard's
    "holds no grant on it" check), so even `view`, which is not brand-scoped,
    would otherwise let someone with nothing on brand B open it to a machine.

    **A brand that does not exist and a brand the actor holds nothing on answer
    identically**, for the reason `duplication.require_target_access` gives.
    `grant` itself stays the unchecked primitive the test harness and the
    bootstrap use; a route handling a person must come through here.

    `enforced=False` is the auth-off posture, where nobody is signed in.
    """
    if enforced:
        known = any(b.id == brand_id for b in list_brands(db))
        if not known or not has_permission(db, actor, permission, brand_id=brand_id):
            raise GrantForbidden(
                f"You cannot grant {permission} on that brand: you do not hold it there."
            )
    return grant(db, integration_id, permission, brand_id)


def unheld_grants(db: Session, actor, integration_id: int) -> list[tuple[str, int]]:
    """The `(permission, brand_id)` grants of this integration the actor does
    not hold themselves, in a stable order. Empty means the actor could have
    granted every one of them."""
    grants = db.query(IntegrationGrantDB).filter(
        IntegrationGrantDB.integration_id == integration_id
    ).order_by(IntegrationGrantDB.brand_id, IntegrationGrantDB.permission).all()
    return [
        (g.permission, g.brand_id)
        for g in grants
        if not has_permission(db, actor, g.permission, brand_id=g.brand_id)
    ]


def require_holds_integration(
    db: Session, actor, integration_id: int, *, enforced: bool = True,
) -> None:
    """Refuse an actor who does not hold everything this integration may do.

    **The other half of "no escalation"** (ADR-166 addendum 2026-10-02,
    corrected the same day). `grant_by_person` stops a person *giving* what
    they lack; this stops them *using* what somebody else gave. Issuing a key
    hands the caller the integration's whole power, and `integrations.manage`
    is platform-level — so without this an Admin of brand A could mint a key
    for an integration holding `sends.execute` on brand B and send there.
    Enabling unattended sending widens that power the same way.

    Reductions are not gated: revoking a key, disabling unattended sending
    and deactivating can only take power away.
    """
    if not enforced:
        return
    missing = unheld_grants(db, actor, integration_id)
    if missing:
        permission, brand_id = missing[0]
        raise GrantForbidden(
            "You cannot do that to this integration: it holds "
            f"{permission} on brand {brand_id}, which you do not."
        )


def issue_credential_by_person(
    db: Session, actor, integration_id: int, label: str | None = None,
    *, enforced: bool = True, expires_in_days: int | None = None,
):
    """`issue_credential`, refused unless the actor holds all the integration may do."""
    require_holds_integration(db, actor, integration_id, enforced=enforced)
    return issue_credential(db, integration_id, label=label, expires_in_days=expires_in_days)


# --- key expiry (task-344; ADR-166 second addenda of 2026-10-09 and 2026-10-11) ---

#: A key's expiry is between one day and ten years from when it is set.
EXPIRY_DAYS_RANGE = (1, 3650)
#: A key expiring within this many days is marked in the list, and so is its
#: integration. The only warning: no mail is sent (the user, 2026-10-11).
EXPIRING_SOON_DAYS = 14


def _expiry_for(days: int | None):
    if days is None:
        return None
    low, high = EXPIRY_DAYS_RANGE
    if isinstance(days, bool) or not isinstance(days, int) or not low <= days <= high:
        raise ValueError(f"A key expires after {low} to {high} days, or never.")
    return now() + timedelta(days=days)


def is_live(credential) -> bool:
    """Neither revoked nor expired."""
    return credential.revoked_at is None and (credential.expires_at is None or credential.expires_at > now())


def is_expiring_soon(credential) -> bool:
    return (is_live(credential) and credential.expires_at is not None
            and credential.expires_at <= now() + timedelta(days=EXPIRING_SOON_DAYS))


def suggested_expiry_days(db: Session, integration_id: int) -> int | None:
    """What the next key's form is pre-filled with: the days the newest key
    was given (rotation keeps its rhythm unless someone changes it)."""
    newest = (db.query(IntegrationCredentialDB)
              .filter(IntegrationCredentialDB.integration_id == integration_id)
              .order_by(IntegrationCredentialDB.created_at.desc(), IntegrationCredentialDB.id.desc())
              .first())
    return newest.expires_in_days if newest else None


def set_credential_expiry(db: Session, integration_id: int, credential_id: int, days: int | None):
    """Set a key's expiry to `days` from now, or remove it (None). Returns
    `(old, new)` expiry, or None for a key not under this integration."""
    credential = db.query(IntegrationCredentialDB).filter(
        IntegrationCredentialDB.id == credential_id,
        IntegrationCredentialDB.integration_id == integration_id,
    ).first()
    if credential is None:
        return None
    old, new = credential.expires_at, _expiry_for(days)
    credential.expires_at, credential.expires_in_days = new, days
    db.commit()
    return old, new


def set_credential_expiry_by_person(
    db: Session, actor, integration_id: int, credential_id: int, days: int | None,
    *, enforced: bool = True,
):
    """Bringing an expiry forward, or adding one, only takes power away and is
    not gated, like revoking. Pushing it later or removing it hands out more
    time, and is gated like issuing a key (ADR-166 addendum 2026-10-11, second)."""
    credential = db.query(IntegrationCredentialDB).filter(
        IntegrationCredentialDB.id == credential_id,
        IntegrationCredentialDB.integration_id == integration_id,
    ).first()
    if credential is None:
        return None
    new = _expiry_for(days)
    lengthens = (new is None and credential.expires_at is not None) or (
        new is not None and credential.expires_at is not None and new > credential.expires_at)
    if lengthens:
        require_holds_integration(db, actor, integration_id, enforced=enforced)
    return set_credential_expiry(db, integration_id, credential_id, days)


def set_unattended_by_person(
    db: Session, actor, integration_id: int, ceiling: int, *, enforced: bool = True,
) -> bool:
    """Raising the ceiling is gated like issuing a key (it widens what the
    integration does without a person); lowering it, to 0, never is."""
    current = db.query(IntegrationDB).filter(IntegrationDB.id == integration_id).first()
    if current is None:
        return False
    if ceiling > unattended_ceiling(current):
        require_holds_integration(db, actor, integration_id, enforced=enforced)
    return set_unattended_ceiling(db, integration_id, ceiling)


def revoke_grant_by_person(
    db: Session, actor, integration_id: int, permission: str, brand_id: int,
    *, enforced: bool = True,
) -> bool:
    """Removing a grant needs the same holding as giving it: without this, an
    Admin of brand A could strip brand B's integrations of what B's own people
    gave them."""
    if enforced and not has_permission(db, actor, permission, brand_id=brand_id):
        raise GrantForbidden(
            f"You cannot remove {permission} on that brand: you do not hold it there."
        )
    return revoke_grant(db, integration_id, permission, brand_id)


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
    db: Session, integration_id: int, label: str | None = None, *, expires_in_days: int | None = None,
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

    expires_at = _expiry_for(expires_in_days)   # refused before anything is written
    secret = new_secret()
    credential = IntegrationCredentialDB(
        integration_id=integration_id,
        key_id=new_key_id(),
        secret_hash=hash_secret(secret),
        label=(label or "").strip() or None,
        expires_at=expires_at,
        expires_in_days=expires_in_days,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    logger.info(
        "integration %s: credential %s issued", integration_id, credential.key_id,
    )
    return credential, secret


def revoke_credential(
    db: Session, credential_id: int, at: datetime | None = None,
    *, integration_id: int | None = None,
) -> bool:
    """`integration_id`, when given, must own the credential — otherwise a
    route naming one integration could revoke another's key."""
    query = db.query(IntegrationCredentialDB).filter(
        IntegrationCredentialDB.id == credential_id,
        IntegrationCredentialDB.revoked_at.is_(None),
    )
    if integration_id is not None:
        query = query.filter(IntegrationCredentialDB.integration_id == integration_id)
    credential = query.first()
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

#: The bucket every claimed key that names no credential shares (task-33).
#: Not a shape `issue_credential` can produce, so it cannot collide with a real
#: key and read as one.
UNKNOWN_KEY = "(no such key)"


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
        # **Bucket on something the caller cannot vary** (task-33). The claimed
        # key comes straight off the Authorization header, so bucketing on it
        # meant an attacker who changed the key per request wrote one row per
        # attempt — the unbounded growth ADR-153 §6's aggregate rule exists to
        # prevent. A key that names a real credential keeps its own bucket,
        # because "someone is guessing the secret for this key" is the useful
        # evidence; every key that names nothing shares one, so the rows an
        # attacker can create are bounded by the credentials that exist, plus
        # one. Hashing the claimed key would not have helped: a hash varies as
        # freely as its input. The lookup runs on every failure and changes
        # nothing about the response, so it is not an oracle either.
        if not db.query(IntegrationCredentialDB.id).filter(
            IntegrationCredentialDB.key_id == claimed
        ).first():
            claimed = UNKNOWN_KEY
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
    # Expired is refused on the revoked path, with the same answer (ADR-166
    # second addendum of 2026-10-09, point 3): the caller cannot tell them apart.
    if credential.expires_at is not None and credential.expires_at <= now():
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
