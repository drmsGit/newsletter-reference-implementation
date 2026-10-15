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
from typing import NamedTuple
from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy.orm import Session

from app.product import PRODUCT_SLUG
from app.auth.db_models import (
    BrandDB, IntegrationDB, IntegrationGrantDB, LoginCodeDB,
    LoginCodeRequestDB, RoleAssignmentDB, RoleDB, RolePermissionDB, SessionDB,
    UserDB,
)
from app.auth.permissions import ALL_PERMISSIONS, BUILTIN_ROLES, IMPLIED, ADMIN

logger = logging.getLogger(__name__)

CODE_TTL_MINUTES = 10
CODE_MAX_ATTEMPTS = 5

# How often a code may be *requested*, as opposed to guessed (ADR-151 §2).
# Deliberately generous: the threat is bulk mail to a guessed address, not a
# user who clicks "send it again" because the first one has not arrived. The
# per-address window is longer than CODE_TTL_MINUTES so that a real person can
# always outlast one dead code, and the per-client allowance is larger because
# an office behind one NAT address is several people, not one.
CODE_REQUESTS_PER_ADDRESS = 5
CODE_REQUEST_ADDRESS_WINDOW_MINUTES = 15
CODE_REQUESTS_PER_CLIENT = 20
CODE_REQUEST_CLIENT_WINDOW_MINUTES = 60
#: The defaults only (task-342): the company sets both within safe ranges
#: (`settings.service.get_session_lengths`; ADR-151 addenda 2026-10-09 and
#: 2026-10-11). The sign-in code numbers above stay code: attack resistance.
SESSION_ABSOLUTE_HOURS = 12
SESSION_IDLE_MINUTES = 60
# Named after the product slug (task-29), so it follows product.json. Not a
# bare "session": browsers share cookies per host, not per port, and on
# localhost a bare name would meet every other dev app's cookie.
SESSION_COOKIE = f"{PRODUCT_SLUG}_session"

DEFAULT_BRAND_KEY = "default"


def now() -> datetime:
    return datetime.now(timezone.utc)


def hash_secret(value: str) -> str:
    """SHA-256 for high-entropy secrets: session tokens, machine-credential
    secrets and rate-limit identifiers. Right for those — there is no
    dictionary of 32 random bytes, and a KDF would sit on the hot path of
    every request. **Not for the six-digit login code**, which has 10^6
    possible values and uses `hash_login_code` instead (task-35)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# --- the login code: the one low-entropy secret (task-35) --------------------
#
# A six-digit code is 10^6 values. Under bare SHA-256 a reader of
# `login_codes` could precompute every code once, and identical codes collided
# across users. A per-row salt alone would not have fixed it: a salted row
# still falls to 10^6 SHA-256 guesses in milliseconds. scrypt makes each guess
# cost ~25 ms on the development machine (measured 2026-10-01) — about seven
# CPU-hours per code, against a ten-minute lifetime. Standard library, no new
# dependency, no new secret to manage.
_CODE_KDF = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}
_CODE_PREFIX = "scrypt$"
#: Salt for the KDF run a verify does when there is nothing real to check.
_NO_SALT = bytes(16)


def hash_login_code(code: str) -> str:
    """`scrypt$<salt hex>$<hash hex>`. Salted per row, so equal codes differ."""
    salt = os.urandom(16)
    digest = hashlib.scrypt((code or "").strip().encode("utf-8"), salt=salt, **_CODE_KDF)
    return f"{_CODE_PREFIX}{salt.hex()}${digest.hex()}"


def login_code_matches(stored: str | None, code: str) -> bool:
    """Whether `code` is the one `stored` was made from.

    **Runs the KDF exactly once whatever `stored` is** — a real hash, a legacy
    SHA-256 one, or None because there is no code to check. A slow hash on only
    some verify paths would be a timing oracle: ~25 ms when the address exists
    and holds a code, nothing otherwise, which is the account oracle ADR-151 §2
    closes, reopened through the verify route. A row written before this
    change (bare SHA-256, no prefix) never matches: it expires within the code
    TTL, so failing it closed costs one re-request at most.
    """
    candidate = (code or "").strip().encode("utf-8")
    if stored and stored.startswith(_CODE_PREFIX):
        salt_hex, _, want = stored[len(_CODE_PREFIX):].partition("$")
        got = hashlib.scrypt(candidate, salt=bytes.fromhex(salt_hex), **_CODE_KDF).hex()
        return secrets.compare_digest(got, want)
    hashlib.scrypt(candidate, salt=_NO_SALT, **_CODE_KDF)   # the same work, discarded
    return False


def csrf_token_for(session_token: str | None) -> str:
    """A CSRF token bound to one session, derived rather than stored.

    A synchroniser token normally means a random value kept server-side per
    session. Deriving it from the session token instead is equivalent here and
    costs no storage, no column and no new secret to rotate: CSRF defends
    against a cross-site attacker who can make the browser *send* the session
    cookie but cannot *read* it. Such an attacker therefore cannot compute this
    value. One who can read the cookie already has the session and has no need
    of CSRF.

    Domain-separated from `hash_secret` so this can never collide with the
    session hash stored in `auth_sessions.token_hash` — the two must not be the
    same string even though both derive from the same input.
    """
    if not session_token:
        return ""
    return hashlib.sha256(f"csrf:{session_token}".encode("utf-8")).hexdigest()


def normalise_email(email: str) -> str:
    return (email or "").strip().lower()


DEFAULT_LANDING = "/"


def safe_next(target: str | None) -> str:
    """Sanitise a post-login redirect target.

    A `next` parameter that is echoed back into a redirect is an open-redirect
    hole: an attacker sends a link to your own login page carrying
    `next=https://evil.example`, the victim signs in for real, and lands
    somewhere hostile still trusting the site they started on.

    Only same-site absolute paths are allowed through. Anything else — a full
    URL, a protocol-relative `//host`, a backslash that some clients normalise
    to a slash — falls back to the dashboard.
    """
    value = (target or "").strip()
    if not value.startswith("/"):
        return DEFAULT_LANDING
    if value.startswith("//") or "\\" in value:
        return DEFAULT_LANDING
    if any(ch in value for ch in ("\r", "\n")):
        return DEFAULT_LANDING
    return value


def current_user_summary(db: Session, token: str | None) -> dict | None:
    """Plain data about the signed-in user, safe to hand a template.

    Returns a dict rather than the ORM object on purpose: the caller closes its
    session immediately, and a committed instance would expire and raise on
    first attribute access in the template.
    """
    user = user_for_token(db, token)
    if user is None:
        return None
    return {"id": user.id, "email": user.email, "display_name": user.display_name}


# --- the working brand (ADR-150 point 2) -----------------------------------

def list_brands(db: Session) -> list[BrandDB]:
    """Every brand that exists, oldest first — the administration view.

    Distinct from `brands_for_user`, which answers "what may this person work
    in". Only a `users.manage` holder sees this one, because it is the list you
    grant *from*.
    """
    return db.query(BrandDB).order_by(BrandDB.id.asc()).all()


def create_brand(db: Session, key: str, name: str) -> BrandDB | None:
    """Add a brand. Returns None if the key is taken or empty.

    Gated on `users.manage` at the route, not on a key of its own. A brand is
    the scope in every access grant (ADR-150 point 6), so creating one is an
    act on the access model — the same thing `users.manage` already guards for
    roles and assignments. Inventing a seventeenth permission key would need an
    ADR amendment, and ADR-150 point 5's rule is that a key names a code path:
    there is no separate code path here worth naming.
    """
    key = (key or "").strip().lower().replace(" ", "-")
    name = (name or "").strip()
    if not key or not name:
        return None
    if db.query(BrandDB).filter(BrandDB.key == key).first():
        return None

    brand = BrandDB(key=key, name=name)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    # Every brand always has a default profile (ADR-194 point 1).
    from app.brand_profiles.service import ensure_default_profile
    ensure_default_profile(db, brand.id)
    logger.warning("auth: brand created — %s (%s)", name, key)
    return brand


def rename_brand(db: Session, brand_id: int, name: str) -> BrandDB | None:
    """Change a brand's display name. The key is permanent.

    The key is what a deployment's own configuration and any future per-brand
    asset path would reference, so renaming the label must not move it — the
    same reason ADR numbers are permanent while their titles are editable.
    """
    brand = db.query(BrandDB).filter(BrandDB.id == brand_id).first()
    if brand is None or not (name or "").strip():
        return None
    brand.name = name.strip()
    db.commit()
    db.refresh(brand)
    return brand


#: Brand references `delete_brand` clears rather than refuses on. A session's
#: brand is only where its owner happens to be standing; setting it to NULL is
#: what `resolve_session_brand` already treats as "fall back to a brand they
#: hold". Everything else that references a brand blocks the delete.
RELEASED_ON_BRAND_DELETE = {("auth_sessions", "brand_id")}

#: Brand references deleted together with the brand. A brand's profiles are its
#: own look (ADR-194), not anything a person or a send left behind, so they go
#: with it. What still uses a profile — a variant — belongs to a campaign,
#: which already blocks the delete.
DELETED_WITH_BRAND = {("brand_profiles", "brand_id")}


def brand_holders() -> list[tuple]:
    """Every (table, column) whose rows block deleting a brand.

    **Read from the models, not kept by hand** (task-19). The list this
    replaces named five tables, and two NOT NULL brand foreign keys were added
    after it — `consent_events` (migrate_0008) and `integration_grants`
    (ADR-166) — so a brand holding only a consent record, or only a machine
    grant, got past the guard and failed at the foreign key with a 500 instead
    of the sentence naming what blocks it. A maintenance rule written in a doc
    is not a control; every foreign key to `brands.id` counts here unless it is
    explicitly released above, so a new brand-carrying table refuses by
    default instead of crashing.
    """
    from app.database import Base
    from app.schema_migrations import import_all_models

    import_all_models()
    holders = []
    for table in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
        for column in table.columns:
            if (table.name, column.name) in RELEASED_ON_BRAND_DELETE | DELETED_WITH_BRAND:
                continue
            if any(fk.column.table.name == "brands" for fk in column.foreign_keys):
                holders.append((table, column))
    return holders


def delete_brand(db: Session, brand_id: int) -> str | None:
    """Remove a brand. Returns an error message, or None on success.

    Refused while anything still belongs to it, and refused outright for the
    default brand. Both refusals exist for the same reason: a row that carries
    a brand cannot have it deleted out from under it — that either fails at
    the foreign key or needs a rule for where the orphans go, and inventing
    that rule silently is how content ends up in a brand nobody chose.

    **Consent records block it too, and that one matters beyond the crash.**
    Refusing while consent events exist is what stops a brand being deleted
    and recreated as a way of dropping an opt-out record.
    """
    from sqlalchemy import func as sql_func, select
    from sqlalchemy.exc import IntegrityError

    brand = db.query(BrandDB).filter(BrandDB.id == brand_id).first()
    if brand is None:
        return "That brand no longer exists."
    if brand.key == DEFAULT_BRAND_KEY:
        return "The default brand cannot be deleted — one brand always exists (ADR-150 point 4)."

    blocking = []
    for table, column in brand_holders():
        n = db.execute(
            select(sql_func.count()).select_from(table).where(column == brand_id)
        ).scalar()
        if n:
            label = table.name.replace("_", " ").removesuffix("s")
            blocking.append(f"{n} {label}{'s' if n != 1 else ''}")
    if blocking:
        return f"{brand.name} still has {', '.join(blocking)}. Move or remove those first."

    db.query(SessionDB).filter(SessionDB.brand_id == brand_id).update({"brand_id": None})
    try:
        # Inside the try, not just the commit: a bulk `.delete()` executes at
        # once, so the foreign-key refusal is raised here, before any commit.
        from app.brand_profiles.db_models import BrandProfileDB
        db.query(BrandProfileDB).filter(BrandProfileDB.brand_id == brand_id).delete()
        db.query(BrandDB).filter(BrandDB.id == brand_id).delete()
        db.commit()
    except IntegrityError:
        # Something references this brand that the models do not declare — a
        # table only a migration created, say. The schema check (ADR-181's
        # addendum) is what should catch that; this keeps it a refusal rather
        # than a 500 if it has not.
        db.rollback()
        return (
            f"{brand.name} is still referenced by something the guard could not "
            "count, so it was not deleted. Run scripts/check_schema.py — the "
            "database may hold a table the models do not declare."
        )
    return None


def brands_for_user(db: Session, user: UserDB | None) -> list[BrandDB]:
    """Every brand this user holds a grant on, ordered by id.

    Empty for an unknown or deactivated user. Note this is *grants*, not every
    brand that exists: an Admin on brand 1 only does not get brand 2 handed to
    them because it happens to be in the table.
    """
    if user is None or not user.is_active:
        return []
    return (
        db.query(BrandDB)
        .join(RoleAssignmentDB, RoleAssignmentDB.brand_id == BrandDB.id)
        .filter(RoleAssignmentDB.user_id == user.id)
        .order_by(BrandDB.id.asc())
        .distinct()
        .all()
    )


def resolve_session_brand(db: Session, token: str | None) -> BrandDB | None:
    """Which brand this session is working in. Validated, never trusted.

    `auth_sessions.brand_id` is a *cache* of a choice the user made, not an
    authority. The grant table is the authority, so the stored value is checked
    against it on every resolution — a grant revoked after the choice was made
    must stop taking effect immediately, which is the same property ADR-151
    point 3 gives sessions themselves.

    Falls back to the user's first granted brand when the stored one is absent
    or no longer granted. Returns None only when the user holds no grant at
    all, which is a real state (a user created with no role) and must not be
    papered over with the default brand — that would invent access.
    """
    user = user_for_token(db, token)
    granted = brands_for_user(db, user)
    if not granted:
        return None

    row = (
        db.query(SessionDB)
        .filter(SessionDB.token_hash == hash_secret(token or ""), SessionDB.revoked_at.is_(None))
        .first()
    )
    if row is not None and row.brand_id is not None:
        for brand in granted:
            if brand.id == row.brand_id:
                return brand

    return granted[0]


def current_brand_summary(db: Session, token: str | None) -> dict | None:
    """Plain data about the working brand, safe to hand a template.

    A dict rather than the ORM object, for the same reason
    `current_user_summary` is one: the middleware closes its session
    immediately and a committed instance would expire on first attribute
    access in the template.

    `switchable` is what keeps ADR-150 point 4's promise that a single-brand
    company "never has to think about the switcher" — the navbar renders
    nothing at all unless this is True.
    """
    brand = resolve_session_brand(db, token)
    if brand is None:
        return None
    # The brand's logo, from its DEFAULT profile (ADR-194 point 12, narrowed
    # by the user to the logo only: the app keeps one palette and its fonts).
    # The names are the setup file's Header fields (task-351); an installation
    # that declares no logo shows none.
    # Looked up, never created: reading the session must not write.
    from app.brand_profiles.service import find_default_profile

    from app.assets.resolve import resolve_profile_values

    profile = find_default_profile(db, brand.id)
    values = resolve_profile_values(db, dict((profile.field_values if profile else None) or {}), brand.id)
    return {
        "id": brand.id,
        "key": brand.key,
        "name": brand.name,
        "switchable": len(brands_for_user(db, user_for_token(db, token))) > 1,
        "logo": values.get("logo") or None,
        "logo_alt": values.get("logo_alt") or None,
    }


def set_session_brand(db: Session, token: str | None, brand_id: int) -> BrandDB | None:
    """Switch the working brand. Refuses a brand the user holds no grant on.

    Returns the new brand, or None if the switch was refused — the caller
    answers the same either way, because a response that differed would tell a
    signed-in user which brands exist beyond their own grants.
    """
    user = user_for_token(db, token)
    target = next((b for b in brands_for_user(db, user) if b.id == brand_id), None)
    if target is None:
        logger.warning("auth: refused a brand switch to a brand the user holds no grant on")
        return None

    db.query(SessionDB).filter(
        SessionDB.token_hash == hash_secret(token or ""), SessionDB.revoked_at.is_(None)
    ).update({"brand_id": target.id})
    db.commit()
    return target


# --- seeding ---------------------------------------------------------------

def ensure_default_brand(db: Session) -> BrandDB:
    """One brand always exists (ADR-150 §4) — invisible until a second appears."""
    brand = db.query(BrandDB).filter(BrandDB.key == DEFAULT_BRAND_KEY).first()
    if brand is None:
        brand = BrandDB(key=DEFAULT_BRAND_KEY, name="Default")
        db.add(brand)
        db.commit()
        db.refresh(brand)
    from app.brand_profiles.service import ensure_default_profile
    ensure_default_profile(db, brand.id)
    return brand


def ensure_builtin_roles(db: Session) -> None:
    """Seed the three preset roles, and keep their permissions in step.

    Built-in permissions are re-synced on every startup so that adding a
    permission key in code reaches the shipped roles without a migration. A
    company's *own* roles are never touched — and neither is a built-in role
    somebody has **edited**: the preset is a starting point, not a standing
    instruction, so the moment a company changes one it becomes theirs and the
    sync leaves it alone. Without that, the next restart would silently revert
    a deliberate decision.
    """
    for key, spec in BUILTIN_ROLES.items():
        role = db.query(RoleDB).filter(RoleDB.key == key).first()
        if role is not None and role.is_customised:
            continue
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


def cookie_secure() -> bool:
    """Whether the session cookie carries `Secure`. **Defaults to True.**

    Without it a reachable HTTP path transmits the session token in clear, and
    a reference implementation people are meant to copy should not ship that.
    So the safe value is the default and the exception is explicit, the same
    posture as `system_mail_provider` and `trust_proxy_headers`.

    **The exception is real, not theoretical.** A `Secure` cookie is not sent
    over plain HTTP. Chrome and Firefox treat `http://localhost` as a
    trustworthy origin and send it anyway, so local development is normally
    fine — but Safari has not historically made that exemption, and a developer
    there would find sign-in silently looping back to the login form with no
    error to read. `AUTH_COOKIE_INSECURE=true` is for exactly that case, and
    startup says loudly which mode is in force so it is never a silent setting.
    """
    return (os.environ.get("AUTH_COOKIE_INSECURE") or "").strip().lower() not in {"1", "true", "yes"}


class CodeDelivery(str, Enum):
    """What actually happened to a sign-in code.

    A tri-state, because the two ways delivery can *not* happen are not the
    same thing and collapsing them is what created the P0: `deliver_code`
    returned False both when the dev path deliberately skipped sending and when
    a real send was attempted and failed, and the caller could not tell them
    apart. So a deployment whose provider was misconfigured handed the live
    code to whoever typed the address.
    """

    #: Dev path — nothing was attempted. The code is in the server log.
    dev_not_attempted = "dev_not_attempted"
    #: A real provider accepted it.
    sent = "sent"
    #: A real send was attempted and failed. The code must NOT be shown.
    failed = "failed"


def deliver_code(email: str, code: str) -> CodeDelivery:
    """Send the code, and say which of the three things happened.

    Never raises: a delivery failure must leave the user with a clear message,
    not a stack trace — and the caller answers identically either way so the
    form stays enumeration-resistant.
    """
    if dev_code_visible():
        logger.warning("auth: DEV sign-in code for %s is %s", email, code)
        return CodeDelivery.dev_not_attempted

    from app.delivery.providers.factory import get_provider

    sender = system_mail_from()
    if sender is None:
        logger.warning(
            "auth: SYSTEM_MAIL_FROM is not set — system mail is going out from the "
            "marketing sender, so campaign complaint rates can push sign-in codes "
            "into spam and lock operators out. Use a separate verified domain."
        )

    try:
        # System mail, not delivery: no campaign, no snapshot, no consent gate
        # and no channel behind it — but the same adapter, so it builds a plain
        # artifact rather than the addressed interface growing a second method
        # for a case that is not a send (ADR-161 point 1).
        from app.rendering.renderers.base import RenderedArtifact

        result = get_provider(system_mail_provider(), from_address=sender).send(
            email,
            RenderedArtifact.email(
                subject="Your sign-in code",
                html=(
                    f"<p>Your sign-in code is <strong>{code}</strong>.</p>"
                    f"<p>It expires in {CODE_TTL_MINUTES} minutes.</p>"
                ),
            ),
        )
        if not result.success:
            # error, not warning: nobody can sign in, and the person affected
            # is told nothing (deliberately — see request_login_code), so this
            # log line is the only signal anyone gets.
            logger.error("auth: sign-in code delivery FAILED: %s", result.message)
            return CodeDelivery.failed
        return CodeDelivery.sent
    except Exception as error:  # noqa: BLE001 — never let login raise
        logger.error("auth: sign-in code delivery ERROR: %s", error)
        return CodeDelivery.failed


def trust_proxy_headers() -> bool:
    """Whether `X-Forwarded-For` may be believed. **Off by default.**

    The per-IP limit is only as good as the address it counts. Behind a reverse
    proxy the peer address is the proxy, so every visitor shares one bucket and
    the limit becomes global — restrictive, but never wrong in the direction
    that matters. Believing the header instead makes the limit per-visitor
    again, but an attacker who can set a header can then mint a fresh identity
    per request and the limit stops existing at all.

    So the safe failure is the default and the useful one is opt-in, the same
    posture as AUTH_DEV_SHOW_CODE: turn it on only where a proxy you control
    overwrites the header rather than appending to it.
    """
    return (os.environ.get("TRUST_PROXY_HEADERS") or "").strip().lower() in {"1", "true", "yes"}


def client_identifier(peer: str | None, forwarded_for: str | None) -> str:
    """Which address the per-IP limit counts against.

    Takes strings rather than a Request so the choice above is testable without
    standing up a server, and so `service` stays clear of FastAPI.
    """
    if trust_proxy_headers() and forwarded_for:
        # Left-most entry is the original client; the rest are proxies.
        return forwarded_for.split(",")[0].strip()
    return (peer or "").strip()


def login_request_allowed(db: Session, email: str, client_ip: str) -> bool:
    """May this caller ask for a sign-in code right now? Records it if so.

    ADR-151 §2 requires the request path to be rate limited **per address and
    per IP**. Verification was already capped (`CODE_MAX_ATTEMPTS`); requesting
    was not, so anyone could trigger unlimited mail to a guessed address.

    **Refused requests are not recorded.** Counting them would let an attacker
    hold a victim's address over the limit indefinitely by simply continuing to
    hammer it — turning a mail-volume control into a way to lock a real person
    out of sign-in for as long as the attacker cares to keep going. Counting
    only what was allowed bounds that to a single window, and protects the mail
    volume just as well, which is the thing the limit is actually for.

    The caller must answer identically whether this returns True or False. A
    distinct response for a throttled request would tell an attacker their
    probe was counted, and would differ per address — reopening the
    enumeration oracle that ADR-151 §2 closes in the same sentence.
    """
    address_hash = hash_secret(normalise_email(email))
    client_hash = hash_secret(client_ip or "")
    current = now()

    windows = (
        (LoginCodeRequestDB.address_hash == address_hash,
         CODE_REQUEST_ADDRESS_WINDOW_MINUTES, CODE_REQUESTS_PER_ADDRESS, "address"),
        (LoginCodeRequestDB.client_hash == client_hash,
         CODE_REQUEST_CLIENT_WINDOW_MINUTES, CODE_REQUESTS_PER_CLIENT, "client"),
    )
    for match, minutes, limit, label in windows:
        used = db.query(LoginCodeRequestDB).filter(
            match, LoginCodeRequestDB.created_at > current - timedelta(minutes=minutes)
        ).count()
        if used >= limit:
            # No address and no IP in this line — the row does not keep them
            # and neither should the log. `label` says which limit bit, which
            # is what an operator reading a burst of these needs to know.
            logger.warning(
                "auth: sign-in code request throttled on the %s limit "
                "(%s in the last %s minutes)", label, used, minutes,
            )
            return False

    db.add(LoginCodeRequestDB(address_hash=address_hash, client_hash=client_hash))
    _prune_login_requests(db, current)
    db.commit()
    return True


def _prune_login_requests(db: Session, current: datetime) -> None:
    """Drop counter rows older than the longest window.

    These rows are a counter, not a record — once they are outside every window
    they can never affect a decision again, so keeping them would only
    accumulate hashes of who tried to sign in. Pruned on write rather than on a
    schedule because there is no scheduler, and the write rate here is a
    handful of rows a day.
    """
    longest = max(CODE_REQUEST_ADDRESS_WINDOW_MINUTES, CODE_REQUEST_CLIENT_WINDOW_MINUTES)
    db.query(LoginCodeRequestDB).filter(
        LoginCodeRequestDB.created_at <= current - timedelta(minutes=longest)
    ).delete(synchronize_session=False)


class IssuedCode(NamedTuple):
    """A code that exists and has not been sent yet — what `issue_login_code`
    hands the caller so that SENDING can happen somewhere else."""

    address: str
    code: str


def issue_login_code(db: Session, email: str) -> IssuedCode | None:
    """Create a code for an existing active user, and send nothing.

    **Split from delivery on 2026-09-29 (task-5, ADR-151 §2).** The two routes
    that answer a sign-in request used to call the provider inline, so a known
    address cost a round trip over HTTPS and an unknown one cost a single
    SELECT — the identical 303 arrived several hundred milliseconds later when
    the account existed. The response had been made identical; its *timing*
    had not. The routes now take this result and schedule `deliver_code` to
    run after the response has gone.

    What remains is this function's own work: for a known address one UPDATE,
    one INSERT and a commit, against one SELECT for an unknown one. Measured at
    a 0.6 ms median difference on the development machine, and sampled at most
    five times per address per fifteen minutes by the throttle in front of it.
    That is recorded as a bound, not as constant time.

    Returns None for an unknown or inactive address, and nothing is scheduled.
    """
    address = normalise_email(email)
    user = db.query(UserDB).filter(UserDB.email == address).first()
    if user is None or not user.is_active:
        logger.info("auth: sign-in requested for unknown or inactive address")
        # The same KDF work a real code costs, discarded (task-317). Without it
        # a known address answered ~25 ms slower than an unknown one: the
        # account oracle ADR-151 section 2 closes, reopened by task-35's scrypt.
        hash_login_code(f"{secrets.randbelow(1_000_000):06d}")
        return None

    # Supersede any outstanding code so a request cannot be used to keep an
    # older, possibly observed, code alive.
    db.query(LoginCodeDB).filter(
        LoginCodeDB.user_id == user.id, LoginCodeDB.consumed_at.is_(None)
    ).update({"consumed_at": now()})

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(LoginCodeDB(
        user_id=user.id,
        code_hash=hash_login_code(code),
        expires_at=now() + timedelta(minutes=CODE_TTL_MINUTES),
    ))
    db.commit()
    return IssuedCode(address, code)


def request_login_code(db: Session, email: str) -> str | None:
    """Issue a code and send it, synchronously — **not for HTTP routes.**

    The routes call `issue_login_code` and deliver in the background, because
    sending inline is a timing oracle (task-5). This synchronous form stays for
    local development, scripts and tests, which run on the mock provider where
    there is no round trip to leak.

    Returns the code **only** on the dev path, where nothing was sent and the
    code is already in the server log. Returns None for every other outcome —
    unknown address, deactivated user, successful send, and **a real send that
    failed**.

    That last case is the P0 this function used to have. It returned the code
    whenever delivery did not succeed, without distinguishing "deliberately not
    attempted" from "attempted and failed", so a deployment with a broken mail
    provider handed a working sign-in code to anyone who typed an admin's
    address.

    **No HTTP path may render this value.** The router redirects identically in
    every case (ADR-151 §2), which is what keeps the form from being an
    account-enumeration oracle. If you find yourself passing it into a
    template, you are reintroducing the defect.
    """
    issued = issue_login_code(db, email)
    if issued is None:
        return None
    outcome = deliver_code(issued.address, issued.code)
    # The code escapes this function only when nothing was sent and it is
    # already in the log. `failed` deliberately returns None: the user is told
    # nothing, because telling them delivery failed would reveal that delivery
    # was ATTEMPTED, which only happens for addresses that exist.
    return issued.code if outcome is CodeDelivery.dev_not_attempted else None


def verify_login_code(db: Session, email: str, code: str) -> str | None:
    """Check a code and open a session. Returns the session token, or None.

    **The code is checked exactly once on every path** — unknown address,
    inactive user, no code, expired, exhausted, wrong, right — because the
    check is a deliberately slow KDF, and running it on only some paths would
    tell a caller timing this route which addresses hold a code (task-35).
    """
    address = normalise_email(email)
    user = db.query(UserDB).filter(UserDB.email == address).first()
    row = None
    if user is not None and user.is_active:
        # Locked until this verification commits (task-316). Without the lock
        # two simultaneous submissions both read the code unconsumed — one code
        # opened two sessions — and parallel guesses overwrote each other's
        # `attempts`. A waiting verification is re-checked against the
        # committed row: a consumed code no longer matches, and the count it
        # sees is current (ADR-151 section 2: single use, bounded guesses).
        row = (
            db.query(LoginCodeDB)
            .filter(LoginCodeDB.user_id == user.id, LoginCodeDB.consumed_at.is_(None))
            .order_by(LoginCodeDB.id.desc())
            .with_for_update()
            .first()
        )
    current = now()
    checkable = (
        row is not None and row.expires_at > current and row.attempts < CODE_MAX_ATTEMPTS
    )
    matches = login_code_matches(row.code_hash if checkable else None, code)

    if row is None or row.expires_at <= current:
        return None

    if row.attempts >= CODE_MAX_ATTEMPTS:
        # Burn it rather than leaving a guessable code alive.
        row.consumed_at = current
        db.commit()
        return None

    row.attempts += 1
    if not matches:
        db.commit()
        return None

    row.consumed_at = current
    user.last_login_at = current
    db.commit()
    return create_session(db, user)


def create_session(db: Session, user: UserDB) -> str:
    from app.settings.service import get_session_lengths

    token = secrets.token_urlsafe(32)
    granted = brands_for_user(db, user)
    absolute_hours, _ = get_session_lengths(db)
    db.add(SessionDB(
        user_id=user.id,
        token_hash=hash_secret(token),
        # The company's lifetime when the session starts (task-342): a longer
        # one set later reaches only sessions started after it.
        expires_at=now() + timedelta(hours=absolute_hours),
        # The working brand starts at the first brand they hold, and stays None
        # for a user with no grant — `resolve_session_brand` falls back rather
        # than this column asserting access nobody gave.
        brand_id=granted[0].id if granted else None,
    ))
    db.commit()
    return token


#: How often a live session's `last_seen_at` is written. Short against the idle
#: timeout, so the slide still works; long against a request, so a page view
#: writes it at most once rather than on every one of its several lookups.
TOUCH_INTERVAL = timedelta(seconds=60)


def _session_user(db: Session, token: str | None, *, touch: bool) -> UserDB | None:
    """Resolve a session cookie to a user, enforcing both expiries.

    `touch` is the only difference between the two public callers, and it is
    kept as one function so the expiry rules cannot drift into two versions.
    With `touch=False` this performs no write and no commit, which is what lets
    a guard ask "is this a session?" without extending it.
    """
    if not token:
        return None

    row = (
        db.query(SessionDB)
        .filter(SessionDB.token_hash == hash_secret(token), SessionDB.revoked_at.is_(None))
        .first()
    )
    if row is None:
        return None

    # The company's lengths as they are now (task-342; ADR-151 addendum
    # 2026-10-11): a shorter lifetime ends an existing session at once (its
    # start plus the current lifetime), a longer one never extends it (its
    # stamped expiry still holds); the idle timeout is always the current one.
    from app.settings.service import get_session_lengths

    absolute_hours, idle_minutes = get_session_lengths(db)
    current = now()
    if row.expires_at <= current or row.created_at + timedelta(hours=absolute_hours) <= current:
        return None
    if row.last_seen_at + timedelta(minutes=idle_minutes) <= current:
        return None

    user = db.query(UserDB).filter(UserDB.id == row.user_id).first()
    if user is None or not user.is_active:
        return None

    # **Written at most once a minute** (task-32). This used to write and
    # commit on every call, and one request calls it four or five times —
    # middleware, brand summary, switcher count, brand options, the policy
    # guard — so every page view ran four UPDATE+COMMIT cycles on the same
    # row, and two tabs serialised on its lock. A React screen is five to
    # fifteen requests where a Jinja page was one. The idle timeout only needs
    # minute precision: a session can now lapse up to TOUCH_INTERVAL earlier
    # than it would have, and never later.
    if touch and current - row.last_seen_at >= TOUCH_INTERVAL:
        row.last_seen_at = current
        db.commit()
    return user


def actor_label(principal) -> str:
    """How a principal is named where a record stores its actor as text —
    `content_overrides.overridden_by` (task-243, task-113).

    **Always derived from the authenticated principal, never from a request
    body**, so it cannot be asserted: a user's email, `integration:<name>` for
    a machine caller, and a fixed label when access control is off and nobody
    is signed in to name. Text rather than an actor reference, decided
    2026-10-02: `audit_events` keeps the id-based record of the same act
    (ADR-153), so this is the readable copy, not the authority.
    """
    if isinstance(principal, UserDB):
        return principal.email
    if isinstance(principal, IntegrationDB):
        return f"integration:{principal.name}"[:255]
    return "unauthenticated (access control off)"

def user_for_token(db: Session, token: str | None) -> UserDB | None:
    """Resolve a session cookie to a user, enforcing both expiries.

    Extends the idle timeout as a side effect, which is what makes the timeout
    sliding rather than absolute.
    """
    return _session_user(db, token, touch=True)


def session_is_live(db: Session, token: str | None) -> bool:
    """Whether this cookie is a usable session, **without extending it**.

    For a guard that must distinguish "no session" from "a session", where
    asking the question must not itself be an answer. Read-only on purpose:
    `user_for_token` writes `last_seen_at` and commits on every call, and that
    write amplification is already a logged defect -- a guard that ran it a
    sixth time per request would make it worse to ask a question it does not
    need the answer to.

    Returns False for exactly the cases `user_for_token` returns None,
    including a deactivated user, because a guard that treated those
    differently would answer differently for a deactivated account than for an
    unknown one -- which is the account oracle ADR-151 §2 exists to close.
    """
    return _session_user(db, token, touch=False) is not None


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

# A principal is whoever a request is acting as. ADR-166 point 1: a machine
# caller is one of these, in the same access model, not beside it.
Principal = UserDB | IntegrationDB


class _AllBrands:
    """The type of `ALL_BRANDS`. One instance; compare with `is`."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "ALL_BRANDS"


#: The union across every brand a principal holds a grant on (task-16).
#:
#: **Named, so that nobody gets it by forgetting.** `permissions_for` used to
#: take `brand_id: int | None = None` and answer the union when it was left
#: out, so "may this caller do this on brand B?" and "may this caller do this
#: anywhere?" were the same call with one argument missing — and the second is
#: the fail-open answer. The create-recipient route asked it about a
#: brand-scoped permission and got exactly that: a caller holding
#: `recipients.consent` on brand A could assert consent for brand B.
#:
#: The union itself is right for a platform-level permission, which is held
#: everywhere or nowhere — and grants-only with no DENY means two roles can
#: never contradict each other, so it needs no other change. What changes is
#: that a caller has to say so.
ALL_BRANDS = _AllBrands()


def permissions_for(
    db: Session, principal: Principal | None, brand_id: "int | _AllBrands",
) -> set[str]:
    """Every permission this principal holds on one brand, or on `ALL_BRANDS`.

    **`brand_id` is required, and `None` is refused** (task-16): the union is
    something a caller names, never something it gets by leaving an argument
    out. Pass a brand's id, or `ALL_BRANDS` — and only for a platform-level
    permission or for showing a person their whole access.

    **Two storage shapes, one answer.** A person's permissions arrive through a
    role (`role_permissions → roles → role_assignments`, ADR-150 §6); an
    integration holds them directly (`integration_grants`, ADR-166 point 7 and
    its 2026-09-18 addendum). The dispatch lives here, in the one function both
    kinds of guard already call, so that "may this caller do this here" cannot
    be answered two different ways — which is what ADR-166 point 1 is actually
    protecting against. `has_permission`, `_permitted` and `enforce_policy`
    need no knowledge that machines exist.

    An inactive principal holds nothing, in either shape.
    """
    if brand_id is None:
        raise TypeError(
            "permissions_for needs a scope: a brand id, or ALL_BRANDS. None used "
            "to mean the union across every brand, which made the dangerous "
            "answer the one a caller got by forgetting (task-16)."
        )
    narrowed = brand_id is not ALL_BRANDS

    if principal is None:
        return set()

    if isinstance(principal, IntegrationDB):
        if not principal.is_active:
            return set()
        query = db.query(IntegrationGrantDB.permission).filter(
            IntegrationGrantDB.integration_id == principal.id
        )
        if narrowed:
            query = query.filter(IntegrationGrantDB.brand_id == brand_id)
        # **`view` is NOT implied for an integration**, and that asymmetry is
        # deliberate. Every *role* implies it, because a person who may edit
        # and not read is not a case worth modelling. For a machine it is the
        # ordinary case: n8n triggers a send and reads nothing, a website form
        # pins a recipient and reads nothing. Implying `view` would hand every
        # integration the recipient list — which is one of the four routes
        # ADR-166's Context names as the reason this feature exists.
        return {row[0] for row in query.all()}

    if not principal.is_active:
        return set()

    query = (
        db.query(RolePermissionDB.permission)
        .join(RoleDB, RoleDB.id == RolePermissionDB.role_id)
        .join(RoleAssignmentDB, RoleAssignmentDB.role_id == RoleDB.id)
        .filter(RoleAssignmentDB.user_id == principal.id)
    )
    if narrowed:
        query = query.filter(RoleAssignmentDB.brand_id == brand_id)
    return {row[0] for row in query.all()}


def has_permission(
    db: Session, principal: Principal | None, permission: str,
    brand_id: "int | _AllBrands",
) -> bool:
    """Required scope, for `permissions_for`'s reason: the union is named."""
    return permission in permissions_for(db, principal, brand_id)


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


# --- role administration ---------------------------------------------------

def assign_role(db: Session, user_id: int, role_id: int, brand_id: int | None = None) -> bool:
    """Grant a role on a brand. Idempotent.

    The gap this fills: until now a role was fixed at creation, so a promotion
    or a change of scope meant editing the database — a routine operation with
    no route to it.
    """
    brand = brand_id or ensure_default_brand(db).id
    exists = db.query(RoleAssignmentDB).filter(
        RoleAssignmentDB.user_id == user_id,
        RoleAssignmentDB.role_id == role_id,
        RoleAssignmentDB.brand_id == brand,
    ).first()
    if exists:
        return False
    db.add(RoleAssignmentDB(user_id=user_id, role_id=role_id, brand_id=brand))
    db.commit()
    return True


def revoke_assignment(db: Session, assignment_id: int) -> bool:
    """Remove one grant.

    Sessions are deliberately *not* revoked: losing a role is a change of
    scope, not a reason to be thrown out mid-edit, and the next request is
    checked against the new permissions anyway. Deactivation is the control
    that ends a session (ADR-151 §5).
    """
    removed = db.query(RoleAssignmentDB).filter(
        RoleAssignmentDB.id == assignment_id
    ).delete()
    db.commit()
    return bool(removed)


def create_role(db: Session, key: str, name: str, copy_from_role_id: int | None = None) -> RoleDB | None:
    """Add a role, optionally starting from an existing one's permissions.

    Copying is how "preset, then adjust individually" works: you begin from
    something sensible rather than an empty grid, then change what you need.
    """
    key = (key or "").strip().lower().replace(" ", "-")
    if not key or db.query(RoleDB).filter(RoleDB.key == key).first():
        return None

    role = RoleDB(key=key, name=(name or "").strip() or key, is_builtin=False)
    db.add(role)
    db.commit()
    db.refresh(role)

    if copy_from_role_id:
        source = {
            row.permission
            for row in db.query(RolePermissionDB).filter(
                RolePermissionDB.role_id == copy_from_role_id
            ).all()
        }
        for permission in source | IMPLIED:
            db.add(RolePermissionDB(role_id=role.id, permission=permission))
        db.commit()
    return role


def set_role_permissions(db: Session, role_id: int, permissions: list[str]) -> RoleDB | None:
    """Replace a role's permissions wholesale, and mark it customised.

    Unknown keys are dropped rather than stored: a permission that names no
    code path grants nothing, and keeping it would suggest otherwise. VIEW is
    always included — a role that can edit but not read is not a case worth
    modelling, and omitting it is a confusing way to lock someone out.
    """
    role = db.query(RoleDB).filter(RoleDB.id == role_id).first()
    if role is None:
        return None

    wanted = {p for p in (permissions or []) if p in ALL_PERMISSIONS} | IMPLIED
    db.query(RolePermissionDB).filter(RolePermissionDB.role_id == role_id).delete()
    for permission in sorted(wanted):
        db.add(RolePermissionDB(role_id=role_id, permission=permission))

    role.is_customised = True
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: int) -> str | None:
    """Remove a role. Returns an error message, or None on success.

    Built-in roles and roles somebody still holds are refused — the first so a
    company cannot delete the only role that can manage users, the second so a
    grant never dangles.
    """
    role = db.query(RoleDB).filter(RoleDB.id == role_id).first()
    if role is None:
        return "That role no longer exists."
    if role.is_builtin:
        return f"{role.name} ships with the platform and cannot be deleted."

    holders = db.query(RoleAssignmentDB).filter(RoleAssignmentDB.role_id == role_id).count()
    if holders:
        return f"{holders} user(s) still hold {role.name}. Remove those first."

    db.query(RolePermissionDB).filter(RolePermissionDB.role_id == role_id).delete()
    db.query(RoleDB).filter(RoleDB.id == role_id).delete()
    db.commit()
    return None


def roles_with_permissions(db: Session) -> list[dict]:
    """Every role and the permissions it holds — the editing grid's data."""
    rows = []
    for role in db.query(RoleDB).order_by(RoleDB.id.asc()).all():
        held = {
            r.permission
            for r in db.query(RolePermissionDB).filter(
                RolePermissionDB.role_id == role.id
            ).all()
        }
        rows.append({
            "role": role,
            "permissions": held,
            "holders": db.query(RoleAssignmentDB).filter(
                RoleAssignmentDB.role_id == role.id
            ).count(),
        })
    return rows


def access_list(db: Session) -> list[dict]:
    """Every account with its grants and last login — the ADR-151 §5 review surface."""
    rows = []
    for user in db.query(UserDB).order_by(UserDB.email.asc()).all():
        grants = (
            db.query(RoleAssignmentDB.id, RoleDB.name, BrandDB.name, BrandDB.id)
            .join(RoleDB, RoleDB.id == RoleAssignmentDB.role_id)
            .join(BrandDB, BrandDB.id == RoleAssignmentDB.brand_id)
            .filter(RoleAssignmentDB.user_id == user.id)
            .all()
        )

        # Where a brand carries more than one role, resolve the union and show
        # it. Several roles on one brand stay legal on purpose — it is how
        # customised roles combine — but two lines reading "Manager on Default"
        # and "Admin on Default" leave a reader to work out the actual access in
        # their head, and nobody chose that set explicitly. Computed only for
        # the ambiguous brands, so the ordinary one-role case costs no query
        # and adds no noise to the page.
        per_brand: dict[tuple[int, str], int] = {}
        for _, _, brand_name, brand_id in grants:
            per_brand[(brand_id, brand_name)] = per_brand.get((brand_id, brand_name), 0) + 1
        combined = [
            {"brand": brand_name,
             "permissions": sorted(permissions_for(db, user, brand_id=brand_id))}
            for (brand_id, brand_name), count in per_brand.items() if count > 1
        ]
        live = db.query(SessionDB).filter(
            SessionDB.user_id == user.id,
            SessionDB.revoked_at.is_(None),
            SessionDB.expires_at > now(),
        ).count()
        rows.append({
            "user": user,
            "grants": [{"id": i, "role": r, "brand": b} for i, r, b, _ in grants],
            "combined": combined,
            "live_sessions": live,
        })
    return rows
