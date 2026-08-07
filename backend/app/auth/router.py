"""Sign-in, sign-out and the user access list (ADR-151).

Server-rendered to match the rest of the POC UI. Two behaviours are load-
bearing rather than cosmetic:

  - **Requesting a code answers identically for every address**, known or not,
    so the form cannot be used to discover who has an account (ADR-151 §2).
  - **The dev path shows the code on screen** when no real sender is
    configured, because login runs through the delivery layer and the dev
    default is the mock provider, which sends nothing.
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import AUTH_ENFORCED_KEY, auth_enforced, require_permission
from app.auth.permissions import ALL_PERMISSIONS, BUILTIN_ROLES, USERS_MANAGE
from app.auth.db_models import RoleDB
from app.auth.service import (
    SESSION_COOKIE, SESSION_ABSOLUTE_HOURS, access_list, assign_role, create_role,
    create_user, delete_role, dev_code_visible, normalise_email, request_login_code,
    revoke_assignment, revoke_token, roles_with_permissions, safe_next, set_active,
    set_role_permissions, user_for_token, verify_login_code,
)
from app.database import get_db
from app.settings.service import set_config

router = APIRouter(tags=["frontend"])
templates = Jinja2Templates(directory="app/templates")

# Shown whatever happens, so the page cannot be read as "this address exists".
NEUTRAL_NOTICE = "If that address has an account, a sign-in code is on its way."


@router.get("/ui/login")
def login_form(
    request: Request, notice: str = "", error: str = "",
    email: str = "", next: str = "",
):
    return templates.TemplateResponse(
        request, "login.html",
        {"title": "Sign in", "notice": notice, "error": error, "email": email,
         "dev_mode": dev_code_visible(), "code": "", "next": safe_next(next)},
    )


@router.post("/ui/login")
def login_request(
    request: Request,
    email: str = Form(...),
    next: str = Form(""),
    db: Session = Depends(get_db),
):
    """Issue a code. The response is the same whether or not the address exists."""
    code = request_login_code(db, email)
    address = normalise_email(email)
    target = safe_next(next)

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
             "error": "", "notice": NEUTRAL_NOTICE, "dev_mode": True,
             "next": target},
        )

    return RedirectResponse(
        url=f"/ui/login/verify?email={address}&next={quote(target, safe='')}",
        status_code=303,
    )


@router.get("/ui/login/verify")
def verify_form(
    request: Request, email: str = "", code: str = "",
    error: str = "", next: str = "",
):
    return templates.TemplateResponse(
        request, "login_verify.html",
        {"title": "Enter your code", "email": email, "prefilled": code,
         "error": error, "notice": NEUTRAL_NOTICE,
         "dev_mode": dev_code_visible(), "next": safe_next(next)},
    )


@router.post("/ui/login/verify")
def verify_submit(
    email: str = Form(...),
    code: str = Form(...),
    next: str = Form(""),
    db: Session = Depends(get_db),
):
    target = safe_next(next)
    token = verify_login_code(db, email, code)
    if token is None:
        return RedirectResponse(
            url=f"/ui/login/verify?email={normalise_email(email)}"
                f"&next={quote(target, safe='')}"
                f"&error=That+code+is+not+valid+or+has+expired.",
            status_code=303,
        )

    # The dashboard by default, never /ui/users — a Viewer sent there lands on
    # a 403 with no navigation, which is indistinguishable from being locked
    # out of a system they just signed in to.
    response = RedirectResponse(url=target, status_code=303)
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=SESSION_ABSOLUTE_HOURS * 3600,
        httponly=True, samesite="lax",
    )
    return response


@router.post("/ui/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    """Deliberately unguarded: signing out must work from any page, whatever
    the account can or cannot reach. A Viewer previously had no route to it at
    all, because the only control lived on a page their role was refused."""
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


@router.post("/ui/users/{user_id}/roles")
def user_assign_role(
    user_id: int,
    role_id: int = Form(...),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    assign_role(db, user_id, role_id)
    return RedirectResponse(url="/ui/users", status_code=303)


@router.post("/ui/users/assignments/{assignment_id}/remove")
def user_revoke_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    revoke_assignment(db, assignment_id)
    return RedirectResponse(url="/ui/users", status_code=303)


@router.get("/ui/roles")
def roles_page(
    request: Request,
    error: str = "",
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    """Role × permission grid. The whole policy in one screen."""
    return templates.TemplateResponse(
        request, "roles.html",
        {
            "title": "Roles & permissions",
            "rows": roles_with_permissions(db),
            "all_permissions": ALL_PERMISSIONS,
            "error": error,
        },
    )


@router.post("/ui/roles")
def role_create(
    key: str = Form(...),
    name: str = Form(""),
    copy_from: str = Form(""),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    """Create a role, optionally copying an existing one as the starting set."""
    source = int(copy_from) if (copy_from or "").isdigit() else None
    if create_role(db, key=key, name=name, copy_from_role_id=source) is None:
        return RedirectResponse(
            url="/ui/roles?error=That+role+key+is+already+in+use+or+invalid.",
            status_code=303,
        )
    return RedirectResponse(url="/ui/roles", status_code=303)


@router.post("/ui/roles/{role_id}/permissions")
async def role_set_permissions(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    """Save one role's permissions. Marks it customised, so the shipped preset
    stops overwriting it at startup."""
    form = await request.form()
    set_role_permissions(db, role_id, form.getlist("permissions"))
    return RedirectResponse(url="/ui/roles", status_code=303)


@router.post("/ui/roles/{role_id}/delete")
def role_delete(
    role_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    error = delete_role(db, role_id)
    suffix = f"?error={quote(error)}" if error else ""
    return RedirectResponse(url=f"/ui/roles{suffix}", status_code=303)


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
