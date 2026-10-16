"""Administering people, roles and brands — each write once (task-358).

Both the old Jinja forms (`app/auth/router.py`) and the JSON routes
(`app/auth/admin_router.py`) call these, so a rule and its audit entry exist
once: the service function that does the write, the lock-out guards inside it
(ADR-150 addendum 2026-10-16), and the entry that records it. A refusal is an
`AdminRefused` (or the service's `AccessLockout`), in words a person can act on.
"""
from fastapi import Request
from sqlalchemy.orm import Session

from app.audit import service as audit
from app.auth import service
from app.auth.db_models import RoleAssignmentDB, RoleDB, UserDB


class AdminRefused(ValueError):
    pass


class AdminNotFound(LookupError):
    pass


def create_user(request: Request, db: Session, *, email: str, display_name: str = "", is_external: bool = False,
                role_key: str = "viewer", brand_id: int | None = None) -> UserDB:
    user = service.create_user(db, email=email, display_name=display_name, is_external=is_external,
                               role_key=role_key, brand_id=brand_id)
    if user is None:
        raise AdminRefused("That address is empty, or it already has an account.")
    audit.record_from_request(request, db, audit.USER_CREATED, subject_type="user", subject_id=user.id,
                              detail={"external": user.is_external, "role": role_key})
    return user


def set_active(request: Request, db: Session, user_id: int, active: bool, *, actor_user_id: int | None) -> UserDB:
    user = service.set_active(db, user_id, active, actor_user_id=actor_user_id)
    if user is None:
        raise AdminNotFound("That person does not exist.")
    audit.record_from_request(request, db, audit.USER_REACTIVATED if active else audit.USER_DEACTIVATED,
                              subject_type="user", subject_id=user_id)
    return user


def grant_role(request: Request, db: Session, user_id: int, role_id: int, brand_id: int | None) -> None:
    if db.get(UserDB, user_id) is None or db.get(RoleDB, role_id) is None:
        raise AdminNotFound("That person or role does not exist.")
    if service.assign_role(db, user_id, role_id, brand_id=brand_id):
        audit.record_from_request(request, db, audit.ROLE_GRANTED, subject_type="user", subject_id=user_id,
                                  brand_id=brand_id, detail={"role_id": role_id})


def revoke_grant(request: Request, db: Session, assignment_id: int) -> None:
    # Read before revoking: afterwards the row is gone (ADR-153 point 5).
    grant = db.query(RoleAssignmentDB).filter(RoleAssignmentDB.id == assignment_id).first()
    if grant is None:
        raise AdminNotFound("That grant no longer exists.")
    user_id, role_id, brand_id = grant.user_id, grant.role_id, grant.brand_id
    service.revoke_assignment(db, assignment_id)
    audit.record_from_request(request, db, audit.ROLE_REVOKED, subject_type="user", subject_id=user_id,
                              brand_id=brand_id, detail={"role_id": role_id, "brand_id": brand_id})


def create_role(request: Request, db: Session, *, key: str, name: str = "", copy_from: int | None = None) -> RoleDB:
    role = service.create_role(db, key=key, name=name, copy_from_role_id=copy_from)
    if role is None:
        raise AdminRefused("That role key is empty, or already in use.")
    audit.record_from_request(request, db, audit.ROLE_CREATED, subject_type="role", subject_id=role.id,
                              detail={"key": role.key, "copied_from": copy_from})
    return role


def set_permissions(request: Request, db: Session, role_id: int, permissions: list[str]) -> RoleDB:
    role = service.set_role_permissions(db, role_id, permissions)
    if role is None:
        raise AdminNotFound("That role does not exist.")
    held = sorted(p for (p,) in db.query(service.RolePermissionDB.permission)
                  .filter(service.RolePermissionDB.role_id == role_id))
    audit.record_from_request(request, db, audit.ROLE_PERMISSIONS_SET, subject_type="role", subject_id=role_id,
                              detail={"permissions": held})
    return role


def delete_role(request: Request, db: Session, role_id: int) -> None:
    error = service.delete_role(db, role_id)
    if error:
        raise AdminRefused(error)
    audit.record_from_request(request, db, audit.ROLE_DELETED, subject_type="role", subject_id=role_id)


def create_brand(request: Request, db: Session, *, key: str, name: str):
    brand = service.create_brand(db, key=key, name=name)
    if brand is None:
        raise AdminRefused("That brand key is already taken, or the name is empty.")
    # The brand the action created, not the one the actor was working in.
    audit.record_from_request(request, db, audit.BRAND_CREATED, subject_type="brand", subject_id=brand.id,
                              brand_id=brand.id, detail={"key": brand.key, "name": brand.name})
    return brand


def rename_brand(request: Request, db: Session, brand_id: int, name: str):
    brand = service.rename_brand(db, brand_id=brand_id, name=name)
    if brand is None:
        raise AdminRefused("That brand does not exist, or the name is empty.")
    audit.record_from_request(request, db, audit.BRAND_RENAMED, subject_type="brand", subject_id=brand_id,
                              brand_id=brand_id, detail={"name": brand.name})
    return brand


def delete_brand(request: Request, db: Session, brand_id: int) -> None:
    error = service.delete_brand(db, brand_id=brand_id)
    if error:
        raise AdminRefused(error)
    audit.record_from_request(request, db, audit.BRAND_DELETED, subject_type="brand", subject_id=brand_id)
