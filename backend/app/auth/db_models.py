"""Access model tables (ADR-150) and the passwordless login flow (ADR-151).

Two shapes here are decisions rather than convenience:

  **Roles and permissions are rows, not an enum.** ADR-150 ships three roles as
  a *preset* a company can extend, replace or ignore — adding a role must not
  require code. The permission *vocabulary* stays in code (a permission names a
  code path), but which role holds which permission is data.

  **Access is `(user × role × brand)`, one row per grant.** A person working on
  two brands has two rows, not one row with a list. That keeps a real foreign
  key per grant, lets each grant be audited and revoked on its own (ADR-153),
  and allows *different* roles per brand — Manager on one, Viewer on another —
  which a multi-value column on a single role row cannot express.
"""

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func,
)

from app.database import Base


class BrandDB(Base):
    """A brand is a *scope*, not a hierarchy (ADR-150 §2).

    One row always exists. A company using brands as nothing but a logo and a
    palette never creates a second one and never sees the machinery (ADR-150
    §4) — but the column exists from the start, because retrofitting the scope
    into every access grant later is the expensive path.
    """

    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserDB(Base):
    """A person who can sign in. No password column — by design (ADR-151)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Stored lowercase; the login form normalises before lookup so that
    # Anna@x.com and anna@x.com are one account rather than two.
    email = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=True)
    # ADR-150 §7: the agency operator is not a role — they are an Admin or
    # Manager who happens to be external. This flag exists for *visibility* in
    # the access list, not to grant or withhold anything.
    is_external = Column(Boolean, nullable=False, default=False)
    # Deactivation rather than deletion: an erased user would orphan the audit
    # trail that ADR-153 depends on.
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)


class RoleDB(Base):
    """A named bundle of permissions. Three are seeded; a company may add more."""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    # Seeded roles are protected from deletion so a company cannot lock itself
    # out by removing the only role that can manage users.
    is_builtin = Column(Boolean, nullable=False, default=False)
    # Set the first time somebody edits a built-in role's permissions, and it
    # stops being re-synced from the shipped preset at startup. Without this the
    # preset would silently revert a company's changes on the next restart — the
    # sync exists so new permission keys reach shipped roles without a
    # migration, not to overwrite decisions somebody made deliberately.
    is_customised = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RolePermissionDB(Base):
    """Which permission keys a role holds. The keys themselves live in code."""

    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission", name="uq_role_permission"),)

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    permission = Column(String(100), nullable=False)


class RoleAssignmentDB(Base):
    """One grant: this user holds this role on this brand (ADR-150 §6)."""

    __tablename__ = "role_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "brand_id", name="uq_user_role_brand"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LoginCodeDB(Base):
    """A one-time sign-in code (ADR-151 §1-2).

    Stored hashed, short-lived, single-use and attempt-limited. The hash is a
    plain digest rather than a slow KDF: a six-digit code has too little
    entropy for a KDF to save it if the table leaks, so the protections that
    actually matter are the short TTL, the single use, and the attempt counter.
    """

    __tablename__ = "login_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    code_hash = Column(String(64), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LoginCodeRequestDB(Base):
    """One recorded *request* for a sign-in code — the rate-limit counter.

    `LoginCodeDB` caps how many times a code may be **guessed**
    (`CODE_MAX_ATTEMPTS`). Nothing capped how often one could be **asked for**,
    so anyone could trigger unlimited mail to a guessed address. ADR-151 §2
    requires the limit per address *and* per IP; this table is how it is
    counted.

    **Rows, not memory.** An in-memory counter resets on restart and each
    worker keeps its own, so a stated limit of five is silently five times the
    worker count — a limit that lies about its own value is worse than none.

    **Both identifiers are stored hashed.** The decision recorded for the
    address was that a throttle counts attempts for addresses that may not be
    users at all, and ADR-154's rule is that accountability records carry ids
    rather than contact details. The same reasoning covers the client IP, which
    is equally personal data, and counting works identically on a digest either
    way. The cost is that these rows are useless for abuse forensics — they are
    a counter, not an audit trail, and ADR-153's log is the place for the
    latter.

    Rows outside the longest window are pruned as they are written, so the
    table stays proportional to live traffic rather than growing forever.
    """

    __tablename__ = "login_code_requests"

    id = Column(Integer, primary_key=True, index=True)
    address_hash = Column(String(64), nullable=False, index=True)
    client_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class SessionDB(Base):
    """A signed-in session (ADR-151 §3).

    Two expiries, not one: `expires_at` is the absolute lifetime and
    `last_seen_at` drives the idle timeout. `revoked_at` is what makes
    deactivating a user take effect immediately rather than at next expiry —
    the property the offboarding story in ADR-151 §5 rests on.
    """

    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    # The brand this session is working in (ADR-150 point 2's switcher).
    # Nullable: a session predating the switcher, or one belonging to a user
    # with no grant at all, simply has no working context — the resolver falls
    # back rather than the column lying. Server-side on purpose: the same
    # reason the session token is, and it dies with the session when ADR-151
    # point 3's immediate revocation fires.
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True, index=True)


# --- machine principals (ADR-166) -------------------------------------------
#
# These live here, in the access model, rather than in an `app/integrations/`
# package of their own. That is point 1 expressed in the directory tree: an
# integration is "a principal inside ADR-150's access model, not a parallel
# authorization system", and a separate package is precisely how a parallel
# system starts — one grant table over here, another over there, and two
# answers to "may this caller do this here" within a release or two.


class IntegrationDB(Base):
    """A system that calls the API — "n8n", "the website form".

    **The integration is the durable audit actor, not the credential.**
    ADR-166 point 3: credentials are issued, rotated and revoked beneath an
    integration, and history is attributed to the integration so it stays
    continuous across a rotation. A credential-as-actor model cannot answer
    "who triggered this send" a year later once the credential that acted has
    been revoked — the row would point at nothing.
    """

    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    # Display metadata, deliberately NOT stamped into audit rows (ADR-166
    # point 3, ADR-153 §5, ADR-154 §3). An integration named after a person or
    # a customer must not become the contact detail that breaks the rule that
    # accountability records carry internal identifiers.
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    # Deactivation is immediate and applies to every credential beneath it,
    # the same property ADR-151 §3 gives a revoked session.
    is_active = Column(Boolean, nullable=False, default=True)
    # ADR-166 point 5. **Safe by default**: a machine-triggered send lands in
    # ADR-142 §4's approval surface unless somebody deliberately said
    # otherwise. Opt-out, explicit, and logged — the same posture as the mock
    # provider default and the governed model list.
    may_send_unattended = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Who set it up, for the access list. NOT an ownership link: ADR-166
    # point 4 makes a credential independent of the person who issued it, so
    # deactivating this user does not revoke anything. The cost is booked in
    # that record's Negative section rather than mitigated here.
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class IntegrationCredentialDB(Base):
    """A key + secret pair beneath an integration.

    **Key and secret, not a bare token** (ADR-166 point 1). The key identifies
    which integration is calling before the secret is resolved, which is what
    makes rate limiting, aggregation and a useful log line possible on a
    request that ultimately fails to authenticate. A bare token that does not
    verify identifies nobody, so the failure cannot be attributed or counted.
    """

    __tablename__ = "integration_credentials"

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)
    # Public half. Safe in a log line — it names the caller, proves nothing.
    key_id = Column(String(64), nullable=False, unique=True, index=True)
    # **Hashed, never reversible ciphertext.** ADR-151 §2 stores login codes
    # hashed; ADR-152's Notes reject encryption at rest as moving the problem,
    # since the decryption key still has to live somewhere. The two combine to
    # one answer, and it is the same answer for a credential the platform
    # issues as for one it holds.
    secret_hash = Column(String(64), nullable=False)
    # A human label for the key itself ("n8n production"), so a list of three
    # keys under one integration is readable during a rotation.
    label = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Written on successful authentication only. A failed attempt proves
    # nothing about the holder of the key — anyone can name a key they do not
    # have — so counting it here would let an outsider write to this row.
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    # **Revocation is immediate, not effective at next expiry** (ADR-166
    # point 3, inheriting ADR-151 §3): an integration that has started
    # misbehaving is exactly the case where waiting is unacceptable.
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class IntegrationGrantDB(Base):
    """`(integration × permission × brand)` — ADR-166 point 7 and its addendum.

    **Permissions directly, not through a role.** A role is a human convenience
    for naming a job; an integration does not have a job, it has the list of
    calls it makes. Modelling "n8n-sender" as a role would fill a company's
    role list with single-purpose entries that are really integrations wearing
    a hat.

    `brand_id` is NOT NULL, exactly as `role_assignments.brand_id` is. A
    platform-level permission is checked without a brand filter for a machine
    the same way it is for a person (ADR-150's 2026-09-15 addendum), so this
    column carrying a value always means one rule fewer, not one more.
    """

    __tablename__ = "integration_grants"
    __table_args__ = (
        UniqueConstraint(
            "integration_id", "permission", "brand_id",
            name="uq_integration_permission_brand",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)
    permission = Column(String(100), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
