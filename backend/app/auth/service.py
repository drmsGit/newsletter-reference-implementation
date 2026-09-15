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
from enum import Enum

from sqlalchemy.orm import Session

from app.auth.db_models import (
    BrandDB, LoginCodeDB, LoginCodeRequestDB, RoleAssignmentDB, RoleDB,
    RolePermissionDB, SessionDB, UserDB,
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
SESSION_ABSOLUTE_HOURS = 12
SESSION_IDLE_MINUTES = 60
SESSION_COOKIE = "nra_session"

DEFAULT_BRAND_KEY = "default"


def now() -> datetime:
    return datetime.now(timezone.utc)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def brand_usage(db: Session) -> dict[int, int]:
    """How many rows hang off each brand — content, campaigns, audiences, sends
    and grants combined.

    Shown beside Delete so the refusal is predictable rather than a surprise
    after clicking. A zero here is the only case `delete_brand` accepts.
    """
    from app.audience.db_models import AudienceGroupDB
    from app.campaigns.db_models import CampaignDB
    from app.content.db_models import ContentRecordDB
    from app.delivery.db_models import SendInstanceDB

    counts: dict[int, int] = {}
    for brand in db.query(BrandDB).all():
        counts[brand.id] = sum((
            db.query(ContentRecordDB).filter(ContentRecordDB.brand_id == brand.id).count(),
            db.query(CampaignDB).filter(CampaignDB.brand_id == brand.id).count(),
            db.query(AudienceGroupDB).filter(AudienceGroupDB.brand_id == brand.id).count(),
            db.query(SendInstanceDB).filter(SendInstanceDB.brand_id == brand.id).count(),
            db.query(RoleAssignmentDB).filter(RoleAssignmentDB.brand_id == brand.id).count(),
        ))
    return counts


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


def delete_brand(db: Session, brand_id: int) -> str | None:
    """Remove a brand. Returns an error message, or None on success.

    Refused while anything still belongs to it, and refused outright for the
    default brand. Both refusals exist for the same reason: every row in four
    tables carries a NOT NULL brand, so deleting one out from under its content
    would either fail at the foreign key or, worse, need a rule for where the
    orphans go — and inventing that rule silently is how content ends up in a
    brand nobody chose.
    """
    brand = db.query(BrandDB).filter(BrandDB.id == brand_id).first()
    if brand is None:
        return "That brand no longer exists."
    if brand.key == DEFAULT_BRAND_KEY:
        return "The default brand cannot be deleted — one brand always exists (ADR-150 point 4)."

    from app.audience.db_models import AudienceGroupDB
    from app.campaigns.db_models import CampaignDB
    from app.content.db_models import ContentRecordDB
    from app.delivery.db_models import SendInstanceDB

    holders = {
        "content record": db.query(ContentRecordDB).filter(ContentRecordDB.brand_id == brand_id).count(),
        "campaign": db.query(CampaignDB).filter(CampaignDB.brand_id == brand_id).count(),
        "audience group": db.query(AudienceGroupDB).filter(AudienceGroupDB.brand_id == brand_id).count(),
        "send": db.query(SendInstanceDB).filter(SendInstanceDB.brand_id == brand_id).count(),
        "role assignment": db.query(RoleAssignmentDB).filter(RoleAssignmentDB.brand_id == brand_id).count(),
    }
    blocking = [f"{n} {label}{'s' if n != 1 else ''}" for label, n in holders.items() if n]
    if blocking:
        return f"{brand.name} still has {', '.join(blocking)}. Move or remove those first."

    db.query(SessionDB).filter(SessionDB.brand_id == brand_id).update({"brand_id": None})
    db.query(BrandDB).filter(BrandDB.id == brand_id).delete()
    db.commit()
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
    return {
        "id": brand.id,
        "key": brand.key,
        "name": brand.name,
        "switchable": len(brands_for_user(db, user_for_token(db, token))) > 1,
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
        result = get_provider(system_mail_provider(), from_address=sender).send(
            email,
            "Your sign-in code",
            f"<p>Your sign-in code is <strong>{code}</strong>.</p>"
            f"<p>It expires in {CODE_TTL_MINUTES} minutes.</p>",
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


def request_login_code(db: Session, email: str) -> str | None:
    """Issue a code for an existing active user.

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
    account-enumeration oracle; this return exists for local development and
    for tests, which run on the mock provider. If you find yourself passing it
    into a template, you are reintroducing the defect.
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

    outcome = deliver_code(address, code)
    # The code escapes this function only when nothing was sent and it is
    # already in the log. `failed` deliberately returns None: the user is told
    # nothing, because telling them delivery failed would reveal that delivery
    # was ATTEMPTED, which only happens for addresses that exist.
    return code if outcome is CodeDelivery.dev_not_attempted else None


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
    granted = brands_for_user(db, user)
    db.add(SessionDB(
        user_id=user.id,
        token_hash=hash_secret(token),
        expires_at=now() + timedelta(hours=SESSION_ABSOLUTE_HOURS),
        # The working brand starts at the first brand they hold, and stays None
        # for a user with no grant — `resolve_session_brand` falls back rather
        # than this column asserting access nobody gave.
        brand_id=granted[0].id if granted else None,
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
            db.query(RoleAssignmentDB.id, RoleDB.name, BrandDB.name)
            .join(RoleDB, RoleDB.id == RoleAssignmentDB.role_id)
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
            "grants": [{"id": i, "role": r, "brand": b} for i, r, b in grants],
            "live_sessions": live,
        })
    return rows
