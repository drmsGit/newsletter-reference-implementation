"""Sign-in, sign-out and the user access list (ADR-151).

Server-rendered to match the rest of the POC UI. Two behaviours are load-
bearing rather than cosmetic:

  - **Requesting a code answers identically for every address**, known or not,
    so the form cannot be used to discover who has an account (ADR-151 §2).
  - **The dev path shows the code on screen** when no real sender is
    configured, because login runs through the delivery layer and the dev
    default is the mock provider, which sends nothing.
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import AUTH_ENFORCED_KEY, auth_enforced, require_permission
from app.auth.permissions import BUILTIN_ROLES, USERS_MANAGE
from app.auth.db_models import RoleDB
from app.auth.service import (
    SESSION_COOKIE, SESSION_ABSOLUTE_HOURS, access_list, create_user,
    dev_code_visible, normalise_email, request_login_code, revoke_token,
    set_active, user_for_token, verify_login_code,
)
from app.database import get_db
from app.settings.service import set_config

router = APIRouter(tags=["frontend"])
templates = Jinja2Templates(directory="app/templates")

# Shown whatever happens, so the page cannot be read as "this address exists".
NEUTRAL_NOTICE = "If that address has an account, a sign-in code is on its way."


@router.get("/ui/login")
def login_form(request: Request, notice: str = "", error: str = "", email: str = ""):
    return templates.TemplateResponse(
        request, "login.html",
        {"title": "Sign in", "notice": notice, "error": error, "email": email,
         "dev_mode": dev_code_visible(), "code": ""},
    )


@router.post("/ui/login")
def login_request(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    """Issue a code. The response is the same whether or not the address exists."""
    code = request_login_code(db, email)
    address = normalise_email(email)

    if code:
        # Dev path only: request_login_code returns a code exclusively when it
        # could not be delivered over a real provider. Rendered directly rather
        # than redirected, breaking the post-redirect-get pattern used
        # everywhere else on purpose — the alternative is putting a sign-in
        # code in a query string, where it lands in history and referrer logs.
        # That is a bad habit to teach in a reference implementation, and the
        # inconsistency is confined to a branch production never reaches.
        return templates.TemplateResponse(
            request, "login_verify.html",
            {"title": "Enter your code", "email": address, "prefilled": code,
             "error": "", "notice": NEUTRAL_NOTICE, "dev_mode": True},
        )

    return RedirectResponse(url=f"/ui/login/verify?email={address}", status_code=303)


@router.get("/ui/login/verify")
def verify_form(request: Request, email: str = "", code: str = "", error: str = ""):
    return templates.TemplateResponse(
        request, "login_verify.html",
        {"title": "Enter your code", "email": email, "prefilled": code,
         "error": error, "notice": NEUTRAL_NOTICE, "dev_mode": dev_code_visible()},
    )


@router.post("/ui/login/verify")
def verify_submit(
    email: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(get_db),
):
    token = verify_login_code(db, email, code)
    if token is None:
        return RedirectResponse(
            url=f"/ui/login/verify?email={normalise_email(email)}"
                f"&error=That+code+is+not+valid+or+has+expired.",
            status_code=303,
        )

    response = RedirectResponse(url="/ui/users", status_code=303)
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=SESSION_ABSOLUTE_HOURS * 3600,
        httponly=True, samesite="lax",
    )
    return response


@router.post("/ui/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    revoke_token(db, request.cookies.get(SESSION_COOKIE))
    response = RedirectResponse(url="/ui/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@router.get("/ui/users")
def users_page(
    request: Request,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    """The access list — who holds what, and when they last signed in."""
    return templates.TemplateResponse(
        request, "users.html",
        {
            "title": "Users & access",
            "rows": access_list(db),
            "roles": db.query(RoleDB).order_by(RoleDB.id.asc()).all(),
            "builtin_keys": list(BUILTIN_ROLES),
            "enforced": auth_enforced(db),
            "signed_in_as": user_for_token(db, request.cookies.get(SESSION_COOKIE)),
            "dev_mode": dev_code_visible(),
        },
    )


@router.post("/ui/users")
def user_create(
    email: str = Form(...),
    display_name: str = Form(""),
    role_key: str = Form("viewer"),
    is_external: str = Form(""),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    create_user(
        db, email=email, display_name=display_name,
        is_external=bool(is_external), role_key=role_key,
    )
    return RedirectResponse(url="/ui/users", status_code=303)


@router.post("/ui/users/{user_id}/active")
def user_set_active(
    user_id: int,
    active: str = Form(""),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    set_active(db, user_id, active == "1")
    return RedirectResponse(url="/ui/users", status_code=303)


@router.post("/ui/users/enforcement")
def set_enforcement(
    enforced: str = Form(""),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    """Turn access control on or off.

    Deliberately reachable from the UI: the alternative is an environment
    variable, and an operator who has locked themselves out cannot edit one
    without shell access to the server.
    """
    set_config(db, AUTH_ENFORCED_KEY, enforced == "1")
    return RedirectResponse(url="/ui/users", status_code=303)
