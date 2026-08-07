"""Passwordless sign-in, sessions, and permission resolution (ADR-150/151).

The login flow is deliberately boring: request a code, type it back, get a
session. What is *not* boring, and is written out here rather than assumed:

  - **A code, not a link** (ADR-151 §1). Corporate scanners and Apple MPP
    pre-fetch links and would consume a single-use token before the human
    clicks it — the same pre-fetch behaviour the signal layer already accounts
    for, arriving in a different place.
  - **The login form must not be an account-enumeration oracle** (§2), so
    requesting a code answers identically whether or not the address exists.
  - **Sessions are revocable** (§3), which is what makes deactivating a user
    take effect now rather than at next expiry.
  - **Login depends on the send layer**, so a misconfigured sender would lock
    everyone out — including the Admin who would fix it. Hence the dev path in
    `deliver_code`.
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth.db_models import (
    BrandDB, LoginCodeDB, RoleAssignmentDB, RoleDB, RolePermissionDB, SessionDB, UserDB,
)
from app.auth.permissions import ALL_PERMISSIONS, BUILTIN_ROLES, IMPLIED, ADMIN

logger = logging.getLogger(__name__)

CODE_TTL_MINUTES = 10
CODE_MAX_ATTEMPTS = 5
SESSION_ABSOLUTE_HOURS = 12
SESSION_IDLE_MINUTES = 60
SESSION_COOKIE = "nra_session"

DEFAULT_BRAND_KEY = "default"


def now() -> datetime:
    return datetime.now(timezone.utc)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalise_email(email: str) -> str:
    return (email or "").strip().lower()


# --- seeding ---------------------------------------------------------------

def ensure_default_brand(db: Session) -> BrandDB:
    """One brand always exists (ADR-150 §4) — invisible until a second appears."""
    brand = db.query(BrandDB).filter(BrandDB.key == DEFAULT_BRAND_KEY).first()
    if brand is None:
        brand = BrandDB(key=DEFAULT_BRAND_KEY, name="Default")
        db.add(brand)
        db.commit()
        db.refresh(brand)
    return brand


def ensure_builtin_roles(db: Session) -> None:
    """Seed the three preset roles, and keep their permissions in step.

    Built-in permissions are re-synced on every startup so that adding a
    permission key in code reaches the shipped roles without a migration. A
    company's *own* roles are never touched.
    """
    for key, spec in BUILTIN_ROLES.items():
        role = db.query(RoleDB).filter(RoleDB.key == key).first()
        if role is None:
            role = RoleDB(
                key=key, name=spec["name"],
                description=spec["description"], is_builtin=True,
            )
            db.add(role)
            db.commit()
            db.refresh(role)

        wanted = set(spec["permissions"]) | IMPLIED
        held = {
            row.permission
            for row in db.query(RolePermissionDB).filter(
                RolePermissionDB.role_id == role.id
            ).all()
        }
        for permission in wanted - held:
            db.add(RolePermissionDB(role_id=role.id, permission=permission))
        for stale in held - wanted:
            db.query(RolePermissionDB).filter(
                RolePermissionDB.role_id == role.id,
                RolePermissionDB.permission == stale,
            ).delete()
    db.commit()


def ensure_initial_admin(db: Session) -> UserDB | None:
    """Bootstrap the first Admin, or nobody can ever sign in.

    Address comes from INITIAL_ADMIN_EMAIL. Runs only while the user table is
    empty, so it can never quietly re-grant admin to an address that was
    deliberately deactivated later.
    """
    if db.query(UserDB).count() > 0:
        return None

    email = normalise_email(os.environ.get("INITIAL_ADMIN_EMAIL", ""))
    if not email:
        logger.warning(
            "auth: no users exist and INITIAL_ADMIN_EMAIL is not set — "
            "nobody can sign in. Set it and restart."
        )
        return None

    user = UserDB(email=email, display_name="Initial admin", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    brand = ensure_default_brand(db)
    role = db.query(RoleDB).filter(RoleDB.key == ADMIN).first()
    db.add(RoleAssignmentDB(user_id=user.id, role_id=role.id, brand_id=brand.id))
    db.commit()
    logger.warning("auth: seeded initial admin %s", email)
    return user


def bootstrap(db: Session) -> None:
    ensure_default_brand(db)
    ensure_builtin_roles(db)
    ensure_initial_admin(db)


# --- sign-in ---------------------------------------------------------------

# --- the system-mail channel ------------------------------------------------
# Sign-in codes are the first user of a **third** category of outbound mail, and
# it is neither of the two the architecture knows about:
#
#   marketing customer     — campaigns, bulk, opt-in under UWG §7
#   transactional customer — receipts and confirmations, triggered by a customer
#   system internal        — this: mail to the company's own operators
#
# System mail is not customer-facing at all, so it carries no consent question,
# no unsubscribe semantics and almost no volume. What makes it a separate
# channel rather than a flavour of transactional is the **failure mode**: if
# transactional delivery degrades a customer misses a receipt, but if system
# delivery degrades nobody can sign in — including the person who would fix
# whatever caused it. That circularity is unique to this category.
#
# Login is only the first consumer. Approval notifications, AI-suggestion
# alerts and other operator-facing messages belong on the same channel, which
# is why these read SYSTEM_ rather than AUTH_. They live in this module for now
# because auth is the only caller; they should move to a shared helper as soon
# as a second one appears.

def system_mail_provider() -> str:
    """Which send provider carries system mail. **Mock by default.**

    Same posture as everywhere else in the architecture: the free, offline
    option is what you get unless a deployment opts in. Deliberately *not*
    inferred from whether a provider key happens to be present — a developer
    machine legitimately holds a real key for testing sends, and inferring
    from it once caused this code to email a live message to a throwaway test
    address. Enabling real system mail is an explicit act.
    """
    return (os.environ.get("SYSTEM_MAIL_PROVIDER") or "mock").strip().lower()


def system_mail_from() -> str | None:
    """Sender for system mail. None means "fall back to the marketing sender".

    Which is the thing to avoid: campaign complaint rates degrade the
    reputation of everything sent from that domain, and system mail landing in
    spam locks operators out of the platform. A separate verified domain or
    subdomain is the intent — see the module note above.

    Not enforced, because the correct value depends on DNS a deployment
    controls. Falling back is allowed and warned about, never silent.
    """
    return (os.environ.get("SYSTEM_MAIL_FROM") or "").strip() or None


def dev_code_visible() -> bool:
    """Whether the code must be shown on screen instead of emailed.

    True when the configured provider cannot actually deliver (the mock sends
    nothing, so a developer who cannot see the code cannot sign in at all), or
    when explicitly requested.
    """
    if (os.environ.get("AUTH_DEV_SHOW_CODE") or "").strip().lower() in {"1", "true", "yes"}:
        return True
    return system_mail_provider() == "mock"


def deliver_code(email: str, code: str) -> bool:
    """Send the code. Returns True if it went out over a real provider.

    Never raises: a delivery failure must leave the user with a clear message,
    not a stack trace — and the caller answers identically either way so the
    form stays enumeration-resistant.
    """
    if dev_code_visible():
        logger.warning("auth: DEV sign-in code for %s is %s", email, code)
        return False

    from app.delivery.providers.factory import get_provider

    sender = system_mail_from()
    if sender is None:
        logger.warning(
            "auth: SYSTEM_MAIL_FROM is not set — system mail is going out from the "
            "marketing sender, so campaign complaint rates can push sign-in codes "
            "into spam and lock operators out. Use a separate verified domain."
        )

    try:
        result = get_provider(system_mail_provider(), from_address=sender).send(
            email,
            "Your sign-in code",
            f"<p>Your sign-in code is <strong>{code}</strong>.</p>"
            f"<p>It expires in {CODE_TTL_MINUTES} minutes.</p>",
        )
        if not result.success:
            logger.warning("auth: sign-in code delivery failed: %s", result.message)
        return bool(result.success)
    except Exception as error:  # noqa: BLE001 — never let login raise
        logger.warning("auth: sign-in code delivery error: %s", error)
        return False


def request_login_code(db: Session, email: str) -> str | None:
    """Issue a code for an existing active user.

    Returns the code **only** when the dev path is active, so a caller can show
    it. Returns None otherwise — including for unknown or deactivated
    addresses, which is what keeps the response identical for every input
    (ADR-151 §2).
    """
    address = normalise_email(email)
    user = db.query(UserDB).filter(UserDB.email == address).first()
    if user is None or not user.is_active:
        logger.info("auth: sign-in requested for unknown or inactive address")
        return None

    # Supersede any outstanding code so a request cannot be used to keep an
    # older, possibly observed, code alive.
    db.query(LoginCodeDB).filter(
        LoginCodeDB.user_id == user.id, LoginCodeDB.consumed_at.is_(None)
    ).update({"consumed_at": now()})

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(LoginCodeDB(
        user_id=user.id,
        code_hash=hash_secret(code),
        expires_at=now() + timedelta(minutes=CODE_TTL_MINUTES),
    ))
    db.commit()

    delivered = deliver_code(address, code)
    return None if delivered else code


def verify_login_code(db: Session, email: str, code: str) -> str | None:
    """Check a code and open a session. Returns the session token, or None."""
    address = normalise_email(email)
    user = db.query(UserDB).filter(UserDB.email == address).first()
    if user is None or not user.is_active:
        return None

    row = (
        db.query(LoginCodeDB)
        .filter(LoginCodeDB.user_id == user.id, LoginCodeDB.consumed_at.is_(None))
        .order_by(LoginCodeDB.id.desc())
        .first()
    )
    if row is None or row.expires_at <= now():
        return None

    if row.attempts >= CODE_MAX_ATTEMPTS:
        # Burn it rather than leaving a guessable code alive.
        row.consumed_at = now()
        db.commit()
        return None

    row.attempts += 1
    if not secrets.compare_digest(row.code_hash, hash_secret((code or "").strip())):
        db.commit()
        return None

    row.consumed_at = now()
    user.last_login_at = now()
    db.commit()
    return create_session(db, user)


def create_session(db: Session, user: UserDB) -> str:
    token = secrets.token_urlsafe(32)
    db.add(SessionDB(
        user_id=user.id,
        token_hash=hash_secret(token),
        expires_at=now() + timedelta(hours=SESSION_ABSOLUTE_HOURS),
    ))
    db.commit()
    return token


def user_for_token(db: Session, token: str | None) -> UserDB | None:
    """Resolve a session cookie to a user, enforcing both expiries."""
    if not token:
        return None

    row = (
        db.query(SessionDB)
        .filter(SessionDB.token_hash == hash_secret(token), SessionDB.revoked_at.is_(None))
        .first()
    )
    if row is None:
        return None

    current = now()
    if row.expires_at <= current:
        return None
    if row.last_seen_at + timedelta(minutes=SESSION_IDLE_MINUTES) <= current:
        return None

    user = db.query(UserDB).filter(UserDB.id == row.user_id).first()
    if user is None or not user.is_active:
        return None

    row.last_seen_at = current
    db.commit()
    return user


def revoke_token(db: Session, token: str | None) -> None:
    if not token:
        return
    db.query(SessionDB).filter(
        SessionDB.token_hash == hash_secret(token), SessionDB.revoked_at.is_(None)
    ).update({"revoked_at": now()})
    db.commit()


def revoke_all_sessions(db: Session, user_id: int) -> int:
    count = db.query(SessionDB).filter(
        SessionDB.user_id == user_id, SessionDB.revoked_at.is_(None)
    ).update({"revoked_at": now()})
    db.commit()
    return count


# --- permissions -----------------------------------------------------------

def permissions_for(db: Session, user: UserDB, brand_id: int | None = None) -> set[str]:
    """Every permission this user holds, optionally narrowed to one brand."""
    if user is None or not user.is_active:
        return set()

    query = (
        db.query(RolePermissionDB.permission)
        .join(RoleDB, RoleDB.id == RolePermissionDB.role_id)
        .join(RoleAssignmentDB, RoleAssignmentDB.role_id == RoleDB.id)
        .filter(RoleAssignmentDB.user_id == user.id)
    )
    if brand_id is not None:
        query = query.filter(RoleAssignmentDB.brand_id == brand_id)
    return {row[0] for row in query.all()}


def has_permission(
    db: Session, user: UserDB, permission: str, brand_id: int | None = None
) -> bool:
    return permission in permissions_for(db, user, brand_id)


# --- user administration ---------------------------------------------------

def create_user(
    db: Session, email: str, display_name: str | None = None,
    is_external: bool = False, role_key: str = "viewer", brand_id: int | None = None,
) -> UserDB | None:
    address = normalise_email(email)
    if not address or db.query(UserDB).filter(UserDB.email == address).first():
        return None

    user = UserDB(
        email=address,
        display_name=(display_name or "").strip() or None,
        is_external=is_external,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    role = db.query(RoleDB).filter(RoleDB.key == role_key).first()
    if role is not None:
        brand = brand_id or ensure_default_brand(db).id
        db.add(RoleAssignmentDB(user_id=user.id, role_id=role.id, brand_id=brand))
        db.commit()
    return user


def set_active(db: Session, user_id: int, active: bool) -> UserDB | None:
    """Deactivating revokes live sessions immediately — that is the point.

    ADR-151 §5: nothing tells the system when an external operator leaves the
    agency, so deactivation is the whole offboarding control and it has to bite
    now rather than at next expiry.
    """
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if user is None:
        return None
    user.is_active = active
    db.commit()
    if not active:
        revoke_all_sessions(db, user_id)
    return user


def access_list(db: Session) -> list[dict]:
    """Every account with its grants and last login — the ADR-151 §5 review surface."""
    rows = []
    for user in db.query(UserDB).order_by(UserDB.email.asc()).all():
        grants = (
            db.query(RoleDB.name, BrandDB.name)
            .join(RoleAssignmentDB, RoleAssignmentDB.role_id == RoleDB.id)
            .join(BrandDB, BrandDB.id == RoleAssignmentDB.brand_id)
            .filter(RoleAssignmentDB.user_id == user.id)
            .all()
        )
        live = db.query(SessionDB).filter(
            SessionDB.user_id == user.id,
            SessionDB.revoked_at.is_(None),
            SessionDB.expires_at > now(),
        ).count()
        rows.append({
            "user": user,
            "grants": [{"role": r, "brand": b} for r, b in grants],
            "live_sessions": live,
        })
    return rows
