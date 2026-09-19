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

from fastapi import APIRouter, Body, Depends, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import AUTH_ENFORCED_KEY, auth_enforced, require_permission
from app.auth.permissions import ALL_PERMISSIONS, BUILTIN_ROLES, USERS_MANAGE
from app.auth.db_models import RoleAssignmentDB, RoleDB
from app.auth.service import (
    SESSION_COOKIE, SESSION_ABSOLUTE_HOURS, access_list, assign_role,
    client_identifier, cookie_secure, create_brand, create_role, create_user,
    csrf_token_for,
    delete_brand, delete_role, dev_code_visible, list_brands,
    rename_brand,
    login_request_allowed, normalise_email, request_login_code,
    revoke_assignment, revoke_token, roles_with_permissions, safe_next, set_active,
    set_role_permissions, user_for_token, verify_login_code,
)
from app.audit import service as audit
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
    """Issue a code. The response is the same whether or not the address exists.

    One response, unconditionally — same status, same location, same body, for
    a known address, an unknown one, a deactivated user, and a failed send.
    That is ADR-151 §2, and it is enforced here rather than trusted: the
    branch this handler used to have rendered a 200 with the code for existing
    users and redirected 303 for everyone else, which told an unauthenticated
    visitor exactly which addresses were real.

    The dev code is not rendered either. It goes to the server log, which is
    the only place it can be shown without the response revealing that the
    account exists. Convenience on a demo machine is not worth an oracle in the
    configuration a prospect is shown — and `mock` is the default, so that was
    the shipped behaviour.
    """
    # Throttled BEFORE the user lookup, so the path cannot diverge at all — a
    # limit applied after it would take a different amount of work for a known
    # address than an unknown one, which is a timing oracle in place of the
    # response one. This is also the only call site of `request_login_code`
    # reachable over HTTP; a second one would need its own throttle, because
    # the limit lives here rather than in the service (the client address is a
    # request-scoped fact, and the service has no Request).
    if login_request_allowed(
        db, email,
        client_identifier(
            request.client.host if request.client else None,
            request.headers.get("x-forwarded-for"),
        ),
    ):
        # Return value deliberately unused. It carries the dev code, and
        # rendering it is exactly the defect this handler had.
        request_login_code(db, email)

    address = normalise_email(email)
    target = safe_next(next)

    return RedirectResponse(
        # `quote` on BOTH parameters. Starlette decodes `+` in a query value
        # as a space, so an unescaped `name+tag@example.com` arrives at
        # verify_form as `name tag@example.com`, pre-fills the mangled value,
        # and verify_login_code finds no user — reporting "that code is not
        # valid or has expired", which is the wrong diagnosis and is what made
        # this expensive to find. Sub-addressing is common in this product's
        # operator population.
        url=f"/ui/login/verify?email={quote(address, safe='')}"
            f"&next={quote(target, safe='')}",
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
            url=f"/ui/login/verify?email={quote(normalise_email(email), safe='')}"
                f"&next={quote(target, safe='')}"
                f"&error=That+code+is+not+valid+or+has+expired.",
            status_code=303,
        )

    # ADR-153 point 2: a sign-in has no domain record anywhere, so without
    # this line it is simply not recorded. Successes are logged individually;
    # FAILURES deliberately are not — point 6 makes them an aggregate, because
    # a row per failed attempt is a write-amplification target an
    # unauthenticated attacker controls. That aggregate is not in this slice.
    user = user_for_token(db, token)
    audit.record(
        db, audit.SIGNED_IN,
        actor_id=user.id if user else None,
        subject_type="user", subject_id=user.id if user else None,
    )

    # The dashboard by default, never /ui/users — a Viewer sent there lands on
    # a 403 with no navigation, which is indistinguishable from being locked
    # out of a system they just signed in to.
    response = RedirectResponse(url=target, status_code=303)
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=SESSION_ABSOLUTE_HOURS * 3600,
        # `secure` defaults on: without it a reachable HTTP path sends the
        # session token in clear. `httponly` stops script from reading it and
        # `samesite` blunts cross-site POST, but neither does anything about a
        # network observer, which is the gap this closes.
        httponly=True, samesite="lax", secure=cookie_secure(),
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
    error: str = "",
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    """The access list — who holds what, where, and when they last signed in."""
    brands = list_brands(db)
    return templates.TemplateResponse(
        request, "users.html",
        {
            "title": "Users & access",
            "error": error,
            "brands": brands,
            # Every brand-aware control on this page hides itself below two
            # brands (ADR-150 point 4). The brands panel itself always shows,
            # because it is the only place a second brand can come from — and
            # a switcher that can never appear was exactly the hole this fixes.
            "multi_brand": len(brands) > 1,
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
    brand_id: int | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    # Optional so a single-brand deployment never renders the field (ADR-150
    # point 4). `create_user` falls back to the default brand when it is None,
    # which in that case is the only brand there is — not a guess.
    create_user(
        db, email=email, display_name=display_name,
        is_external=bool(is_external), role_key=role_key, brand_id=brand_id,
    )
    return RedirectResponse(url="/ui/users", status_code=303)


@router.post("/ui/users/{user_id}/active")
def user_set_active(
    request: Request,
    user_id: int,
    active: str = Form(""),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    became_active = active == "1"
    set_active(db, user_id, became_active)
    audit.record_from_request(
        request, db,
        audit.USER_REACTIVATED if became_active else audit.USER_DEACTIVATED,
        subject_type="user", subject_id=user_id,
    )
    return RedirectResponse(url="/ui/users", status_code=303)


@router.post("/ui/users/{user_id}/roles")
def user_assign_role(
    request: Request,
    user_id: int,
    role_id: int = Form(...),
    brand_id: int | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    # A grant is (user × role × brand) — ADR-150 point 6. Dropping the brand
    # here is what made every grant land on the default brand however many
    # brands existed, so the switcher could never appear at all.
    assign_role(db, user_id, role_id, brand_id=brand_id)
    audit.record_from_request(
        request, db, audit.ROLE_GRANTED,
        subject_type="user", subject_id=user_id,
        brand_id=brand_id,
        detail={"role_id": role_id},
    )
    return RedirectResponse(url="/ui/users", status_code=303)


@router.post("/ui/brands")
def brand_create(
    request: Request,
    key: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    """Add a brand.

    Gated on `users.manage` rather than a key of its own: a brand is the scope
    in every access grant (ADR-150 point 6), so creating one acts on the access
    model — the same thing that permission already guards for roles and
    assignments. A seventeenth permission key would need an ADR amendment, and
    ADR-150 point 5's rule is that a key names a code path.
    """
    brand = create_brand(db, key=key, name=name)
    if brand is None:
        return RedirectResponse(
            url="/ui/users?error=" + quote("That brand key is already taken, or the name is empty."),
            status_code=303,
        )
    audit.record_from_request(
        request, db, audit.BRAND_CREATED,
        subject_type="brand", subject_id=brand.id,
        # The brand the action CREATED, not the one the actor was working in —
        # otherwise every brand creation reads as an event in brand 1.
        brand_id=brand.id,
        detail={"key": brand.key, "name": brand.name},
    )
    return RedirectResponse(url="/ui/users", status_code=303)


@router.post("/ui/brands/{brand_id}/rename")
def brand_rename(
    brand_id: int,
    name: str = Form(...),
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    rename_brand(db, brand_id, name)
    return RedirectResponse(url="/ui/users", status_code=303)


@router.post("/ui/brands/{brand_id}/delete")
def brand_delete(
    brand_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    error = delete_brand(db, brand_id)
    suffix = "?error=" + quote(error) if error else ""
    return RedirectResponse(url=f"/ui/users{suffix}", status_code=303)


@router.post("/ui/users/assignments/{assignment_id}/remove")
def user_revoke_assignment(
    request: Request,
    assignment_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_permission(USERS_MANAGE)),
):
    # Read the grant BEFORE revoking it — afterwards the row is gone and the
    # entry could only say "some assignment was removed", which is not an
    # accountability record. ADR-153 point 5 keeps this to internal ids.
    grant = (
        db.query(RoleAssignmentDB)
        .filter(RoleAssignmentDB.id == assignment_id)
        .first()
    )
    detail = (
        {"role_id": grant.role_id, "brand_id": grant.brand_id}
        if grant is not None else None
    )
    subject_id = grant.user_id if grant is not None else None

    revoke_assignment(db, assignment_id)
    audit.record_from_request(
        request, db, audit.ROLE_REVOKED,
        subject_type="user", subject_id=subject_id,
        brand_id=grant.brand_id if grant is not None else None,
        detail=detail,
    )
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


#: The JSON session surface lives on its own router, and the reason is a bug
#: avoided rather than a preference. `auth_router` is included with
#: `enforce_csrf`, which reads the request as a FORM — so a JSON sign-out,
#: which does carry a session cookie, would find no token in an empty
#: `FormData` and be refused every single time. These routes are wired with
#: `enforce_api_csrf` instead: skipped when there is no cookie (sign-in), and
#: requiring `X-CSRF-Token` when there is one (sign-out). Exactly the split
#: ADR-168 point 2 drew.
session_router = APIRouter(tags=["auth"])


# --- the JSON session surface (ADR-168) ------------------------------------
#
# **These exist because ADR-168 is otherwise unusable.** That record decided the
# manager client authenticates with the session cookie — and the only way to
# obtain one was an HTML form that answers with a 303 to a page. A client that
# renders its own screens cannot follow that, so the decision had no entry
# point. Found 2026-09-19 while auditing what the JSON API cannot do.
#
# **They are siblings of the form routes, not a second implementation.** Same
# service calls, same throttle, same audit write, same cookie attributes. The
# difference is the shape of the answer, and where the form version leans on a
# redirect to say nothing, these have to say nothing out loud.

@session_router.post("/auth/session/request", status_code=202)
def session_request(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Ask for a sign-in code. **One answer, always.**

    202 with an identical body for a known address, an unknown one, a
    deactivated user and a failed send — ADR-151 §2, and the property gate 4b
    was opened to fix. A JSON surface makes this harder than the form did: a
    redirect says nothing by construction, while a body has to be *written* to
    say nothing, and every branch is a chance to say something.

    Throttled **before** the lookup, for the same reason the form route is: a
    limit applied afterwards costs different work for a known address than an
    unknown one, which is a timing oracle replacing a response one. That
    substitution is already an open P1 against this pair — `request_login_code`
    still calls the provider synchronously — and this route inherits it rather
    than adding a second instance of it.
    """
    email = (payload or {}).get("email") or ""
    if login_request_allowed(
        db, email,
        client_identifier(
            request.client.host if request.client else None,
            request.headers.get("x-forwarded-for"),
        ),
    ):
        # Return value deliberately unused: it carries the dev code, and
        # returning it is the defect gate 4b closed.
        request_login_code(db, email)

    return {
        "status": "code_requested",
        "detail": (
            "If that address belongs to an active account, a sign-in code is "
            "on its way. Submit it to /auth/session/verify."
        ),
    }


@session_router.post("/auth/session/verify")
def session_verify(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    response: Response = None,
):
    """Exchange a code for a session cookie.

    **The failure side is uniform and the success side cannot be**: a wrong
    code, an expired one, an address with no outstanding code and an address
    with no account all answer the same 401 with the same body, while success
    necessarily differs because it sets a cookie. That asymmetry is inherent —
    the point of ADR-151 §2 is that *failures* must not distinguish accounts,
    not that success is invisible.

    The cookie is set with the attributes the form route uses, read from the
    same helpers: `httponly` so script cannot read it, `samesite="lax"` which
    ADR-168 point 3's same-origin requirement is what keeps viable, and
    `secure` on by default.
    """
    email = (payload or {}).get("email") or ""
    code = (payload or {}).get("code") or ""

    token = verify_login_code(db, email, code)
    if token is None:
        # One body for every kind of failure. Naming which part was wrong is
        # the oracle in a different costume.
        raise HTTPException(
            status_code=401,
            detail="That code is not valid or has expired.",
        )

    user = user_for_token(db, token)
    # ADR-153 point 2: a sign-in has no domain record anywhere, so this is the
    # only place it is recorded. Successes individually, failures never —
    # point 6 makes those an aggregate, because a row per failed attempt is a
    # write primitive an unauthenticated caller controls.
    audit.record(
        db, audit.SIGNED_IN,
        actor_id=user.id if user else None,
        subject_type="user", subject_id=user.id if user else None,
    )

    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=SESSION_ABSOLUTE_HOURS * 3600,
        httponly=True, samesite="lax", secure=cookie_secure(),
    )
    return {
        "status": "signed_in",
        "user": {
            "id": user.id if user else None,
            "email": user.email if user else None,
            "display_name": user.display_name if user else None,
        },
        # The SPA needs this for every subsequent write: `enforce_api_csrf`
        # compares it against the token derived from the session. Handed over
        # here rather than fetched separately, because the only moment it can
        # be learned is the moment the session is created.
        "csrf_token": csrf_token_for(token),
    }


@session_router.post("/auth/session", status_code=204)
def session_end(request: Request, response: Response, db: Session = Depends(get_db)):
    """Sign out. Unguarded, like its form sibling.

    Signing out must work from any page and for any account, whatever that
    account can or cannot reach — a Viewer once had no route to it at all
    because the only control lived on a page their role was refused.
    """
    revoke_token(db, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE)
