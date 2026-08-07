"""One dependency guards every route (ADR-150).

The reason access control did not need to touch business logic: authentication
is a request-scoped concern, so it lives in a FastAPI dependency and the
services underneath never learn that users exist. Adding a guard to a route is
one parameter.

**The decision is forced login** (2026-08-02): every UI page requires a signed-in
user, applied as a router-level dependency in `main.py` rather than 57 route
decorators. The lockout worry that argued against it is gone, because system
mail defaults to the mock provider and the sign-in code appears on screen
instead of depending on a mail path that might not work.

Enforcement remains a **setting rather than a constant**, and ships *off* so a
deployment turns it on once it has signed in successfully — recovering from a
misconfiguration needs a way back that is not "edit an environment variable on
the server". Startup says loudly which state it is in.
"""

import logging

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.db_models import UserDB
from app.auth.service import SESSION_COOKIE, has_permission, user_for_token
from app.database import get_db
from app.settings.service import get_config

logger = logging.getLogger(__name__)

AUTH_ENFORCED_KEY = "auth_enforced"


class NotAuthenticated(Exception):
    """Raised when a guarded route is reached without a valid session."""


class NotAuthorised(Exception):
    """Raised when a valid session lacks the permission a route requires."""

    def __init__(self, permission: str):
        super().__init__(permission)
        self.permission = permission


def auth_enforced(db: Session) -> bool:
    return bool(get_config(db, AUTH_ENFORCED_KEY, False))


def current_user(request: Request, db: Session = Depends(get_db)) -> UserDB | None:
    """Resolve the session cookie, or None. Never raises — for optional use."""
    return user_for_token(db, request.cookies.get(SESSION_COOKIE))


def require_permission(permission: str):
    """Dependency factory: this route needs this permission.

    While enforcement is off the check is skipped, but a signed-in user is
    still resolved — so the UI can show who you are, and the audit trail
    (ADR-153) has an actor to attribute to, before the switch is flipped.
    """

    def guard(request: Request, db: Session = Depends(get_db)) -> UserDB | None:
        user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
        if not auth_enforced(db):
            return user
        if user is None:
            raise NotAuthenticated()
        if not has_permission(db, user, permission):
            raise NotAuthorised(permission)
        return user

    return guard
