from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audience import service
from app.audience.models import AudienceGroup, AudienceGroupCreate, AudienceGroupMember
from app.database import get_db

router = APIRouter(prefix="/api/audience-groups", tags=["audience"])


@router.get("/", response_model=list[AudienceGroup])
def list_groups(db: Session = Depends(get_db)):
    return service.list_groups(db)


@router.post("/", response_model=AudienceGroup, status_code=201)
def create_group(payload: AudienceGroupCreate, db: Session = Depends(get_db)):
    try:
        return service.create_group(db, payload.name, payload.description)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.get("/{group_id}", response_model=AudienceGroup)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = service.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.patch("/{group_id}", response_model=AudienceGroup)
def update_group(group_id: int, payload: AudienceGroupCreate, db: Session = Depends(get_db)):
    try:
        group = service.update_group(db, group_id, payload.name, payload.description)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    if not service.delete_group(db, group_id):
        raise HTTPException(status_code=404, detail="Group not found")


@router.get("/{group_id}/members", response_model=list[AudienceGroupMember])
def list_members(group_id: int, db: Session = Depends(get_db)):
    return service.list_members(db, group_id)


@router.post("/{group_id}/members/{recipient_id}", response_model=AudienceGroupMember, status_code=201)
def add_member(group_id: int, recipient_id: int, db: Session = Depends(get_db)):
    member = service.add_member(db, group_id, recipient_id)
    if not member:
        raise HTTPException(status_code=404, detail="Group or recipient not found")
    return member


@router.delete("/{group_id}/members/{recipient_id}", status_code=204)
def remove_member(group_id: int, recipient_id: int, db: Session = Depends(get_db)):
    if not service.remove_member(db, group_id, recipient_id):
        raise HTTPException(status_code=404, detail="Member not found")
