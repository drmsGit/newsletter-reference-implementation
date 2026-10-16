"""The expression dictionary API (task-365, ADR-199).

Reading is `view`, like every screen: the Personalise picker needs the entries
wherever a text is written. **Every write is people only** and needs
`brand_profiles.manage` in the working brand, from the policy table's
`/expressions` entry — the people who already set a brand's texts and tone.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.auth.dependencies import require_person, working_brand
from app.brand_profiles.router import _may_manage
from app.campaigns.router import IF_MATCH, _expected
from app.campaigns.service import StaleWrite
from app.database import get_db
from app.expressions import service
from app.expressions.models import (
    ExpressionDictionary, ExpressionEntry, ExpressionEntryCreate, ExpressionEntryUpdate, stored,
)

router = APIRouter(prefix="/expressions", tags=["personalisation"])

_PERSON = [Depends(require_person)]
_REFUSALS = (service.EntryNotFound, service.EntryConflict, service.EntryInvalid, StaleWrite)


def _http(error: Exception) -> HTTPException:
    if isinstance(error, service.EntryNotFound):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, (service.EntryConflict, StaleWrite)):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, service.EntryInvalid):
        return HTTPException(status_code=422, detail=[
            {"loc": ["body", *loc], "msg": msg, "type": "value_error"} for loc, msg in error.errors])
    raise error


def _out(entry) -> ExpressionEntry:
    return ExpressionEntry(id=entry.id, name=entry.name, label=entry.label,
                           languages=entry.languages, updated_at=entry.updated_at)


def _audit(request: Request, db: Session, action: str, entry_id: int, brand_id: int, detail: dict):
    audit.record_from_request(request, db, action, subject_type="expression_entry",
                              subject_id=entry_id, brand_id=brand_id, detail=detail)


@router.get("", response_model=ExpressionDictionary, summary="The brand's expression dictionary")
def read_dictionary(request: Request, db: Session = Depends(get_db), brand_id: int = Depends(working_brand)):
    entries = service.entries_of(db, brand_id)
    return ExpressionDictionary(items=[_out(e) for e in entries], may_manage=_may_manage(request, db, brand_id))


@router.post("", response_model=ExpressionEntry, status_code=201, dependencies=_PERSON,
             summary="Add an entry; its name is fixed from now on")
def create_entry(body: ExpressionEntryCreate, request: Request, db: Session = Depends(get_db),
                 brand_id: int = Depends(working_brand)):
    try:
        entry = service.create_entry(db, brand_id, name=body.name, label=body.label,
                                     languages=stored(body.languages))
    except _REFUSALS as error:
        raise _http(error)
    _audit(request, db, audit.EXPRESSION_CREATED, entry.id, brand_id, {"name": entry.name})
    return _out(entry)


@router.put("/{entry_id}", response_model=ExpressionEntry, dependencies=_PERSON,
            summary="Change an entry's label and cases",
            description="States the entry's updated_at in If-Match; a stale one is refused with 409.")
def update_entry(entry_id: int, body: ExpressionEntryUpdate, request: Request, db: Session = Depends(get_db),
                 brand_id: int = Depends(working_brand), if_match: str | None = IF_MATCH):
    try:
        entry, changed = service.update_entry(db, entry_id, brand_id, label=body.label,
                                              languages=stored(body.languages),
                                              expected_updated_at=_expected(if_match))
    except _REFUSALS as error:
        raise _http(error)
    if changed:
        _audit(request, db, audit.EXPRESSION_UPDATED, entry.id, brand_id, {"name": entry.name, "changed": changed})
    return _out(entry)


@router.delete("/{entry_id}", status_code=204, dependencies=_PERSON,
               summary="Delete an entry no text uses",
               description="Refused with 409, naming where, while a text still uses it.")
def delete_entry(entry_id: int, request: Request, db: Session = Depends(get_db),
                 brand_id: int = Depends(working_brand), if_match: str | None = IF_MATCH):
    try:
        name = service.delete_entry(db, entry_id, brand_id, expected_updated_at=_expected(if_match))
    except _REFUSALS as error:
        raise _http(error)
    _audit(request, db, audit.EXPRESSION_DELETED, entry_id, brand_id, {"name": name})
