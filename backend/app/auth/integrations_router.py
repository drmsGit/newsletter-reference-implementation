"""Managing integrations over JSON — the SPA's administration surface (task-50, C14).

This was `POST /ui/integrations...` in `frontend/router.py` only, and ADR-170
gives that file a deletion date. **People only**: every route carries
`require_person_with(INTEGRATIONS_MANAGE)`, so a bearer credential is refused
even when it holds the permission — a machine that could mint credentials could
mint itself any grant (ADR-166 addendum, 2026-10-02). Reads carry the guard
too, because the policy table answers `view` for every GET.

**The secret appears once**, in the body of the issue-key response, with
`Cache-Control: no-store`, and nowhere else: no list, no detail, no log line
(ADR-152 §4, ADR-166 point 3). The hash is never serialised.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import integrations as ints
from app.auth.db_models import (
    IntegrationCredentialDB, IntegrationDB, IntegrationGrantDB,
)
from app.auth.dependencies import (
    auth_is_enforced, request_principal, require_person_with,
)
from app.auth.permissions import INTEGRATIONS_MANAGE
from app.database import get_db

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(require_person_with(INTEGRATIONS_MANAGE))],
)


class CredentialOut(BaseModel):
    id: int
    key_id: str
    label: str | None = None
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class GrantOut(BaseModel):
    permission: str
    brand_id: int


class IntegrationOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: bool
    may_send_unattended: bool
    created_at: datetime
    created_by_user_id: int | None = None
    live_keys: int
    grants: list[GrantOut]
    credentials: list[CredentialOut]


class IntegrationCreate(BaseModel):
    name: str
    description: str | None = None


class KeyCreate(BaseModel):
    label: str | None = None


class KeyIssued(BaseModel):
    credential: CredentialOut
    # `key_id.secret`, the whole bearer token. Shown here and never again.
    secret_key: str


class GrantRequest(BaseModel):
    permission: str
    brand_id: int


class UnattendedRequest(BaseModel):
    allowed: bool


def _out(db: Session, integration: IntegrationDB) -> IntegrationOut:
    credentials = ints.credentials_for(db, integration.id)
    grants = (
        db.query(IntegrationGrantDB)
        .filter(IntegrationGrantDB.integration_id == integration.id)
        .order_by(IntegrationGrantDB.permission, IntegrationGrantDB.brand_id)
        .all()
    )
    return IntegrationOut(
        id=integration.id,
        name=integration.name,
        description=integration.description,
        is_active=integration.is_active,
        may_send_unattended=integration.may_send_unattended,
        created_at=integration.created_at,
        created_by_user_id=integration.created_by_user_id,
        live_keys=sum(1 for c in credentials if c.revoked_at is None),
        grants=[GrantOut(permission=g.permission, brand_id=g.brand_id) for g in grants],
        credentials=[
            CredentialOut(
                id=c.id, key_id=c.key_id, label=c.label, created_at=c.created_at,
                last_used_at=c.last_used_at, revoked_at=c.revoked_at,
            )
            for c in credentials
        ],
    )


def _get(db: Session, integration_id: int) -> IntegrationDB:
    integration = db.get(IntegrationDB, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail=f"Integration {integration_id} not found")
    return integration


@router.get(
    "",
    response_model=list[IntegrationOut],
    summary="Every integration, with its grants and keys",
    description=(
        "The review surface ADR-166's Notes named: what each integration may do, "
        "how many keys are live, when each was last used, and whether it may send "
        "without approval. **Never carries a secret or a hash.** A person with "
        "`integrations.manage` only; a bearer credential is refused."
    ),
)
def list_integrations(db: Session = Depends(get_db)):
    return [_out(db, i) for i in db.query(IntegrationDB).order_by(IntegrationDB.id).all()]


@router.post("", response_model=IntegrationOut, status_code=201, summary="Create an integration")
def create_integration(
    payload: IntegrationCreate, request: Request, db: Session = Depends(get_db),
):
    principal = request_principal(request)
    integration = ints.create_integration(
        db, name=payload.name, description=payload.description,
        created_by_user_id=getattr(principal, "id", None),
    )
    if integration is None:
        raise HTTPException(status_code=422, detail="An integration needs a name.")
    return _out(db, integration)


@router.post(
    "/{integration_id}/keys",
    response_model=KeyIssued,
    status_code=201,
    summary="Issue a key. The secret is in this response and nowhere else",
)
def issue_key(
    integration_id: int, payload: KeyCreate, response: Response,
    db: Session = Depends(get_db),
):
    _get(db, integration_id)
    issued = ints.issue_credential(db, integration_id, label=payload.label)
    if issued is None:
        raise HTTPException(status_code=409, detail="That integration is deactivated.")
    credential, secret = issued
    # A secret in a cacheable response is a secret in somebody's cache.
    response.headers["Cache-Control"] = "no-store"
    return KeyIssued(
        credential=CredentialOut(
            id=credential.id, key_id=credential.key_id, label=credential.label,
            created_at=credential.created_at, last_used_at=None, revoked_at=None,
        ),
        secret_key=f"{credential.key_id}.{secret}",
    )


@router.post(
    "/{integration_id}/keys/{credential_id}/revoke",
    response_model=IntegrationOut,
    summary="Revoke one key, immediately",
)
def revoke_key(integration_id: int, credential_id: int, db: Session = Depends(get_db)):
    integration = _get(db, integration_id)
    # Ownership is part of the query, so naming one integration cannot revoke
    # another's key. Already-revoked and not-found answer alike.
    if not ints.revoke_credential(db, credential_id, integration_id=integration_id):
        raise HTTPException(status_code=404, detail=f"Key {credential_id} not found")
    return _out(db, integration)


@router.post(
    "/{integration_id}/grants",
    response_model=IntegrationOut,
    status_code=201,
    summary="Grant one permission on one brand",
    description=(
        "**You may grant only what you hold on that brand** — platform-level "
        "permissions included, because a grant on a brand lets the machine "
        "declare it. A brand that does not exist and one you hold nothing on "
        "both answer 403. An unknown permission is 422."
    ),
)
def add_grant(
    integration_id: int, payload: GrantRequest, request: Request,
    db: Session = Depends(get_db),
):
    from app.auth.permissions import ALL_PERMISSIONS

    integration = _get(db, integration_id)
    if payload.permission not in ALL_PERMISSIONS:
        raise HTTPException(status_code=422, detail=f"{payload.permission!r} is not a permission.")
    try:
        ints.grant_by_person(
            db, request_principal(request), integration_id,
            payload.permission, payload.brand_id, enforced=auth_is_enforced(request),
        )
    except ints.GrantForbidden as error:
        raise HTTPException(status_code=403, detail=str(error))
    return _out(db, integration)


@router.delete(
    "/{integration_id}/grants/{permission}/{brand_id}",
    response_model=IntegrationOut,
    summary="Remove one grant",
)
def remove_grant(
    integration_id: int, permission: str, brand_id: int, db: Session = Depends(get_db),
):
    integration = _get(db, integration_id)
    if not ints.revoke_grant(db, integration_id, permission, brand_id):
        raise HTTPException(status_code=404, detail="That grant does not exist.")
    return _out(db, integration)


@router.put(
    "/{integration_id}/unattended",
    response_model=IntegrationOut,
    summary="Allow or stop this integration sending without approval",
    description=(
        "ADR-166 point 5. Switching it on removes the human from the loop for "
        "this integration's sends, which is why the change is logged."
    ),
)
def set_unattended(
    integration_id: int, payload: UnattendedRequest, db: Session = Depends(get_db),
):
    integration = _get(db, integration_id)
    ints.set_unattended_sending(db, integration_id, payload.allowed)
    db.refresh(integration)
    return _out(db, integration)


@router.post(
    "/{integration_id}/deactivate",
    response_model=IntegrationOut,
    summary="Deactivate an integration and every key beneath it",
)
def deactivate(integration_id: int, db: Session = Depends(get_db)):
    integration = _get(db, integration_id)
    ints.deactivate_integration(db, integration_id)
    db.refresh(integration)
    return _out(db, integration)
