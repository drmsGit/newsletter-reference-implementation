"""The brand-profile API (task-350; ADR-194 and its 2026-10-11 addendum).

Reading is `view`, like every screen. **Every write is people only** (addendum
point 9, the settings rule): `brand_profiles.manage` comes from the policy
table's `/brand-profiles` entry, checked in the working brand, and
`require_person` refuses a machine whatever it holds. The rules for what a
profile may hold live in `service`; this file maps them to HTTP.
"""
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.auth.dependencies import require_person, working_brand
from app.auth.permissions import BRAND_PROFILES_MANAGE, BRAND_PROFILES_TRANSACTIONAL
from app.brand_profiles import service
from app.brand_profiles.models import (
    BrandProfile, BrandProfileCreate, BrandProfileDeleted, BrandProfileDuplicate,
    BrandProfileSummary, BrandProfileUpdate, ProfileFieldOut,
)
from app.brand_profiles.structure import KINDS, profile_structure, required_fields
from app.campaigns.router import IF_MATCH, _expected
from app.campaigns.service import StaleWrite
from app.database import get_db
from app.pagination import Page, PageParams, page_of_query, page_params

router = APIRouter(prefix="/brand-profiles", tags=["brand profiles"])

_PERSON = [Depends(require_person)]


def _summary(profile) -> dict:
    missing = service.missing(profile)
    return dict(id=profile.id, name=profile.name, language=profile.language, kind=profile.kind,
                is_default=profile.is_default, complete=not missing, missing=missing,
                updated_at=profile.updated_at)


def _full(profile, may_manage: bool = True, may_mark_transactional: bool = False) -> BrandProfile:
    """`may_manage` is True after a write: whoever just wrote may write."""
    return BrandProfile(**_summary(profile), field_values=dict(profile.field_values or {}),
                        may_manage=may_manage, may_mark_transactional=may_mark_transactional)


def _http(error: Exception) -> HTTPException:
    if isinstance(error, service.ProfileNotFound):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, service.ProfileForbidden):
        return HTTPException(status_code=403, detail=str(error))
    if isinstance(error, (service.ProfileConflict, StaleWrite)):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, service.ProfileInvalid):
        # FastAPI's own validation shape, one entry per refused part, as the
        # composer's (task-253): the client marks each field in its form.
        return HTTPException(status_code=422, detail=[
            {"loc": ["body", *loc], "msg": msg, "type": "value_error"} for loc, msg in error.errors])
    raise error


_REFUSALS = (service.ProfileNotFound, service.ProfileConflict, service.ProfileInvalid,
             service.ProfileForbidden, StaleWrite)


def _may(request: Request, db: Session, brand_id: int, permission: str) -> bool:
    """The write routes' own rule: a person, holding `permission` in this brand."""
    from app.auth.dependencies import _machine_credential, auth_is_enforced, request_principal
    from app.auth.service import has_permission

    if _machine_credential(request) is not None:
        return False
    if not auth_is_enforced(request):
        return True
    return has_permission(db, request_principal(request), permission, brand_id=brand_id)


def _may_manage(request: Request, db: Session, brand_id: int) -> bool:
    return _may(request, db, brand_id, BRAND_PROFILES_MANAGE)


def _may_mark_transactional(request: Request, db: Session, brand_id: int) -> bool:
    """ADR-195 point 5: creating or marking a transactional profile is its own right."""
    return _may(request, db, brand_id, BRAND_PROFILES_TRANSACTIONAL)


def _audit(request: Request, db: Session, action: str, profile_id: int, brand_id: int, detail: dict):
    audit.record_from_request(request, db, action, subject_type="brand_profile",
                              subject_id=profile_id, brand_id=brand_id, detail=detail)


@router.get("/structure", response_model=list[ProfileFieldOut],
            summary="The fields a profile may hold in this installation")
def read_structure():
    required = {kind: set(required_fields(kind)) for kind in KINDS}
    return [
        ProfileFieldOut(name=f.name, type=f.type, label=f.label, group=f.group,
                        multiline=f.multiline, core=f.core,
                        required_for=[kind for kind in KINDS if f.name in required[kind]])
        for f in profile_structure()
    ]


@router.get("/", response_model=Page[BrandProfileSummary],
            summary="The working brand's profiles, the default first, then by name")
def list_profiles(db: Session = Depends(get_db),
                  brand_id: int = Depends(working_brand),
                  params: PageParams = Depends(page_params)):
    return page_of_query(service.list_profiles(db, brand_id), params, *service.LIST_ORDER,
                         convert=lambda p: BrandProfileSummary(**_summary(p)))


@router.get("/{profile_id}", response_model=BrandProfile, summary="One profile with its values")
def read_profile(profile_id: int, request: Request, db: Session = Depends(get_db),
                 brand_id: int = Depends(working_brand)):
    try:
        return _full(service.get_profile(db, profile_id, brand_id),
                     may_manage=_may_manage(request, db, brand_id),
                     may_mark_transactional=_may_mark_transactional(request, db, brand_id))
    except _REFUSALS as error:
        raise _http(error)


@router.post("/", response_model=BrandProfile, status_code=201, dependencies=_PERSON,
             summary="Add a profile to the working brand")
def create_profile(body: BrandProfileCreate, request: Request, db: Session = Depends(get_db),
                   brand_id: int = Depends(working_brand)):
    try:
        profile = service.create_profile(
            db, brand_id, name=body.name, language=body.language, kind=body.kind,
            field_values=body.field_values,
            allow_transactional=_may_mark_transactional(request, db, brand_id))
    except _REFUSALS as error:
        raise _http(error)
    _audit(request, db, audit.BRAND_PROFILE_CREATED, profile.id, brand_id,
           {"fields": sorted(profile.field_values or {}), "kind": profile.kind})
    return _full(profile)


@router.put("/{profile_id}", response_model=BrandProfile, dependencies=_PERSON,
            summary="Replace a profile's name and values",
            description="States the profile's updated_at in If-Match; a stale one is refused with 409.")
def update_profile(profile_id: int, body: BrandProfileUpdate, request: Request,
                   db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
                   if_match: str | None = IF_MATCH):
    try:
        profile, changed = service.update_profile(
            db, profile_id, brand_id, name=body.name, language=body.language, kind=body.kind,
            field_values=body.field_values, expected_updated_at=_expected(if_match),
            allow_transactional=_may_mark_transactional(request, db, brand_id))
    except _REFUSALS as error:
        raise _http(error)
    if changed:
        _audit(request, db, audit.BRAND_PROFILE_UPDATED, profile.id, brand_id, {"changed": changed})
    return _full(profile)


@router.post("/{profile_id}/duplicate", response_model=BrandProfile, status_code=201,
             dependencies=_PERSON, summary="Copy a profile under a new name")
def duplicate_profile(profile_id: int, request: Request,
                      body: BrandProfileDuplicate | None = Body(None),
                      db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    try:
        copy = service.duplicate_profile(
            db, profile_id, brand_id, name=body.name if body else None,
            allow_transactional=_may_mark_transactional(request, db, brand_id))
    except _REFUSALS as error:
        raise _http(error)
    _audit(request, db, audit.BRAND_PROFILE_DUPLICATED, copy.id, brand_id,
           {"source_profile_id": profile_id, "kind": copy.kind})
    return _full(copy)


@router.post("/{profile_id}/make-default", response_model=BrandProfile, dependencies=_PERSON,
             summary="Make this the brand's default profile")
def make_default(profile_id: int, request: Request, db: Session = Depends(get_db),
                 brand_id: int = Depends(working_brand)):
    try:
        profile = service.make_default(db, profile_id, brand_id)
    except _REFUSALS as error:
        raise _http(error)
    _audit(request, db, audit.BRAND_PROFILE_MADE_DEFAULT, profile.id, brand_id, {})
    return _full(profile)


@router.delete("/{profile_id}", response_model=BrandProfileDeleted, dependencies=_PERSON,
               summary="Delete a profile; variants using it fall back to the default",
               description="The default cannot be deleted (409). Each variant that used the "
                           "profile gets a notice saying it now uses the default.")
def delete_profile(profile_id: int, request: Request, db: Session = Depends(get_db),
                   brand_id: int = Depends(working_brand), if_match: str | None = IF_MATCH):
    try:
        moved = service.delete_profile(db, profile_id, brand_id,
                                       expected_updated_at=_expected(if_match))
    except _REFUSALS as error:
        raise _http(error)
    _audit(request, db, audit.BRAND_PROFILE_DELETED, profile_id, brand_id, {"variants_moved": moved})
    return BrandProfileDeleted(variants_moved=moved)
