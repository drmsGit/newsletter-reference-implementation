"""Administering people, roles and brands over JSON (task-358; ADR-150
addendum 2026-10-16).

The React Settings subpages Users, Roles and Brands. **People only, and
users.manage for reads as well as writes**: `require_person_with` on the
router, because the policy table answers `view` for every GET and a list of
who has which access is itself administration. Every write goes through
`app/auth/admin.py`, as the Jinja forms do, so each rule, guard and audit entry
exists once.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import admin, service
from app.auth.db_models import BrandDB, RoleAssignmentDB, RoleDB, SessionDB, UserDB
from app.auth.dependencies import request_principal, require_person_with
from app.auth.permissions import ALL_PERMISSIONS, USERS_MANAGE, is_brand_scoped
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["administration"],
                   dependencies=[Depends(require_person_with(USERS_MANAGE))])


class Grant(BaseModel):
    id: int
    role_id: int
    role_name: str
    brand_id: int
    brand_name: str


class Person(BaseModel):
    id: int
    email: str
    display_name: str | None = None
    is_external: bool
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None
    live_sessions: int
    grants: list[Grant]
    is_you: bool = Field(description="The person asking: they cannot deactivate themselves")


class PersonCreate(BaseModel):
    email: str
    display_name: str = ""
    is_external: bool = False
    role_key: str = "viewer"
    brand_id: int | None = None


class Active(BaseModel):
    active: bool


class GrantCreate(BaseModel):
    role_id: int
    brand_id: int | None = None


class Role(BaseModel):
    id: int
    key: str
    name: str
    description: str | None = None
    is_builtin: bool
    is_customised: bool
    permissions: list[str]
    holders: int


class RoleCreate(BaseModel):
    key: str
    name: str = ""
    copy_from: int | None = None


class RolePermissions(BaseModel):
    permissions: list[str]


class Permission(BaseModel):
    key: str
    description: str
    brand_scoped: bool = Field(description="Held per brand; otherwise it applies to every brand")


class Brand(BaseModel):
    id: int
    key: str
    name: str
    created_at: datetime


class BrandCreate(BaseModel):
    key: str
    name: str


class BrandRename(BaseModel):
    name: str


def _http(error: Exception) -> HTTPException:
    if isinstance(error, admin.AdminNotFound):
        return HTTPException(status_code=404, detail=str(error))
    return HTTPException(status_code=409, detail=str(error))


_REFUSALS = (admin.AdminNotFound, admin.AdminRefused, service.AccessLockout)


def _you(request: Request) -> int | None:
    principal = request_principal(request)
    return principal.id if isinstance(principal, UserDB) else None


def _people(db: Session, you: int | None, only: int | None = None) -> list[Person]:
    users = db.query(UserDB).order_by(UserDB.email)
    if only is not None:
        users = users.filter(UserDB.id == only)
    users = users.all()
    ids = [u.id for u in users]
    grants: dict[int, list[Grant]] = {i: [] for i in ids}
    for gid, uid, rid, rname, bid, bname in (
            db.query(RoleAssignmentDB.id, RoleAssignmentDB.user_id, RoleDB.id, RoleDB.name, BrandDB.id, BrandDB.name)
            .join(RoleDB, RoleDB.id == RoleAssignmentDB.role_id)
            .join(BrandDB, BrandDB.id == RoleAssignmentDB.brand_id)
            .filter(RoleAssignmentDB.user_id.in_(ids)).order_by(BrandDB.name, RoleDB.name)):
        grants[uid].append(Grant(id=gid, role_id=rid, role_name=rname, brand_id=bid, brand_name=bname))
    # Live as the Jinja access list counts them: not revoked, not expired.
    live: dict[int, int] = {}
    for (uid,) in db.query(SessionDB.user_id).filter(SessionDB.user_id.in_(ids), SessionDB.revoked_at.is_(None),
                                                     SessionDB.expires_at > service.now()):
        live[uid] = live.get(uid, 0) + 1
    return [Person(id=u.id, email=u.email, display_name=u.display_name, is_external=u.is_external,
                   is_active=u.is_active, created_at=u.created_at, last_login_at=u.last_login_at,
                   live_sessions=live.get(u.id, 0), grants=grants[u.id], is_you=u.id == you) for u in users]


# --- people -------------------------------------------------------------------

@router.get("/users", response_model=list[Person], summary="Everyone with an account and their access")
def list_people(request: Request, db: Session = Depends(get_db)):
    return _people(db, _you(request))


@router.post("/users", response_model=Person, status_code=201, summary="Give a person an account")
def create_person(body: PersonCreate, request: Request, db: Session = Depends(get_db)):
    try:
        user = admin.create_user(request, db, email=body.email, display_name=body.display_name,
                                 is_external=body.is_external, role_key=body.role_key, brand_id=body.brand_id)
    except _REFUSALS as error:
        raise _http(error)
    return _people(db, _you(request), only=user.id)[0]


@router.post("/users/{user_id}/active", response_model=Person,
             summary="Deactivate (ends their sessions) or reactivate a person",
             description="Refused for yourself, and when nobody else could manage users afterwards.")
def set_person_active(user_id: int, body: Active, request: Request, db: Session = Depends(get_db)):
    try:
        admin.set_active(request, db, user_id, body.active, actor_user_id=_you(request))
    except _REFUSALS as error:
        raise _http(error)
    return _people(db, _you(request), only=user_id)[0]


@router.post("/users/{user_id}/grants", response_model=Person, summary="Give a person a role on a brand")
def add_grant(user_id: int, body: GrantCreate, request: Request, db: Session = Depends(get_db)):
    try:
        admin.grant_role(request, db, user_id, body.role_id, body.brand_id)
    except _REFUSALS as error:
        raise _http(error)
    return _people(db, _you(request), only=user_id)[0]


@router.delete("/users/{user_id}/grants/{grant_id}", response_model=Person,
               summary="Take a role on a brand away from a person",
               description="Refused when nobody could manage users afterwards.")
def remove_grant(user_id: int, grant_id: int, request: Request, db: Session = Depends(get_db)):
    grant = db.get(RoleAssignmentDB, grant_id)
    if grant is None or grant.user_id != user_id:
        raise HTTPException(status_code=404, detail="That grant is not this person's.")
    try:
        admin.revoke_grant(request, db, grant_id)
    except _REFUSALS as error:
        raise _http(error)
    return _people(db, _you(request), only=user_id)[0]


# --- roles --------------------------------------------------------------------

def _roles(db: Session) -> list[Role]:
    return [Role(id=row["role"].id, key=row["role"].key, name=row["role"].name, description=row["role"].description,
                 is_builtin=row["role"].is_builtin, is_customised=row["role"].is_customised,
                 permissions=sorted(row["permissions"]), holders=row["holders"])
            for row in service.roles_with_permissions(db)]


@router.get("/permissions", response_model=list[Permission], summary="What a role can hold")
def list_permissions():
    return [Permission(key=key, description=text, brand_scoped=is_brand_scoped(key))
            for key, text in ALL_PERMISSIONS.items()]


@router.get("/roles", response_model=list[Role], summary="Every role, its permissions and how many hold it")
def list_roles(db: Session = Depends(get_db)):
    return _roles(db)


@router.post("/roles", response_model=Role, status_code=201,
             summary="Add a role, optionally starting from another's permissions")
def create_role(body: RoleCreate, request: Request, db: Session = Depends(get_db)):
    try:
        role = admin.create_role(request, db, key=body.key, name=body.name, copy_from=body.copy_from)
    except _REFUSALS as error:
        raise _http(error)
    return next(r for r in _roles(db) if r.id == role.id)


@router.put("/roles/{role_id}/permissions", response_model=Role,
            summary="Replace a role's permissions",
            description="view is always kept. Refused when nobody could manage users afterwards.")
def set_role_permissions(role_id: int, body: RolePermissions, request: Request, db: Session = Depends(get_db)):
    try:
        admin.set_permissions(request, db, role_id, body.permissions)
    except _REFUSALS as error:
        raise _http(error)
    return next(r for r in _roles(db) if r.id == role_id)


@router.delete("/roles/{role_id}", status_code=204,
               summary="Delete a role nobody holds", description="A shipped role is never deleted.")
def delete_role(role_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        admin.delete_role(request, db, role_id)
    except _REFUSALS as error:
        raise _http(error)


# --- brands -------------------------------------------------------------------

@router.get("/brands", response_model=list[Brand], summary="Every brand of the installation")
def list_brands(db: Session = Depends(get_db)):
    return service.list_brands(db)


@router.post("/brands", response_model=Brand, status_code=201, summary="Add a brand; its key is permanent")
def create_brand(body: BrandCreate, request: Request, db: Session = Depends(get_db)):
    try:
        return admin.create_brand(request, db, key=body.key, name=body.name)
    except _REFUSALS as error:
        raise _http(error)


@router.patch("/brands/{brand_id}", response_model=Brand, summary="Rename a brand")
def rename_brand(brand_id: int, body: BrandRename, request: Request, db: Session = Depends(get_db)):
    try:
        return admin.rename_brand(request, db, brand_id, body.name)
    except _REFUSALS as error:
        raise _http(error)


@router.delete("/brands/{brand_id}", status_code=204,
               summary="Delete a brand nothing belongs to")
def delete_brand(brand_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        admin.delete_brand(request, db, brand_id)
    except _REFUSALS as error:
        raise _http(error)
