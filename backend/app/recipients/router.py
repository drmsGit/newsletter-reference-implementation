from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import enforce_api_policy
from app.auth.permissions import RECIPIENTS_CONSENT
from app.auth.service import has_permission
from app.auth.dependencies import working_brand
from app.database import get_db
from app.recipients.models import (
    ConsentDriftItem,
    ConsentSyncLog,
    ConsentSyncRequest,
    Recipient,
    RecipientCreate,
    RecipientPreference,
    RecipientPreferenceCreate,
)
from app.recipients.service import (
    create_recipient,
    detect_consent_drift,
    get_recipient_by_external_id,
    list_consent_sync_logs,
    list_recipients,
    create_recipient_preference,
    list_preferences_for_recipient,
    sync_consent_from_crm,
)


router = APIRouter(prefix="/recipients", tags=["recipients"])


@router.post("/", response_model=Recipient)
def create_recipient_record(
    payload: RecipientCreate,
    db: Session = Depends(get_db),
    principal=Depends(enforce_api_policy),
):
    """Create or upsert a recipient.

    **This route needs two permissions, not one**, and it is the only route in
    the system that does. The policy table maps it to `recipients.manage`,
    which is right for creating a contact — but the payload also carries
    `consent_status`, and writing that is `recipients.consent`. ADR-150
    point 5 separates the two precisely so "an integration that only imports
    contact records cannot also assert consent for them", and a single mapping
    would have let the weaker grant assert consent through the body.

    The check is payload-dependent, so it cannot live in the route→permission
    table — that table matches on the route template and has nothing to read a
    body with. Hence an explicit guard here, in the one place the distinction
    is visible. `enforce_api_policy` is already the router-level dependency, so
    this re-declaration resolves from FastAPI's per-request cache rather than
    authenticating a second time.

    **That last sentence used to read differently and was made false by
    ADR-168.** It said a cookie-authenticated caller could not reach this route
    at all, because the machine plane took no cookies. It now takes them, so
    `principal` here may be a person as well as an integration — and the check
    is correct either way, since it asks `has_permission` rather than asking
    what kind of principal this is. A false comment about who can reach a
    consent-writing route is the expensive kind, which is why it is corrected
    rather than left to age.
    """
    declared = payload.consent_status.value
    if declared and principal is not None:
        if not has_permission(db, principal, RECIPIENTS_CONSENT):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Creating a recipient needs 'recipients.manage'; asserting "
                    "their consent needs 'recipients.consent' as well. Omit "
                    "consent_status, or grant the second permission."
                ),
            )
    try:
        return create_recipient(
            db=db,
            brand_id=payload.brand_id,
            external_id=payload.external_id,
            address=payload.address,
            channel=payload.channel,
            language=payload.language,
            attributes=payload.attributes,
            status=payload.status,
            consent_status=payload.consent_status.value,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/", response_model=list[Recipient])
def get_recipients(
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    # A brand as CONTEXT, not authorisation: `recipients.manage` stays
    # platform-level because recipients carry no brand, but their consent does,
    # so projecting it needs one named (ADR-150's 2026-09-20 addendum).
    return list_recipients(db, brand_id=brand_id)


# --- Consent (CRM-synced) -------------------------------------------------
# Registered before the "/{external_id}" catch-all so these fixed multi-segment
# paths resolve correctly. GET drift/sync-log are 2-segment, so they can't be
# swallowed by the single-segment "/{external_id}" route regardless of order.


@router.get("/consent/drift", response_model=list[ConsentDriftItem])
def get_consent_drift(db: Session = Depends(get_db)):
    """Recipients whose platform consent_status diverges from the CRM's most
    recent assertion — a sync that failed to stick, which must not be silent."""
    return detect_consent_drift(db)


@router.get("/consent/sync-log", response_model=list[ConsentSyncLog])
def get_consent_sync_log(
    recipient_id: int | None = None,
    db: Session = Depends(get_db),
):
    return list_consent_sync_logs(db, recipient_id=recipient_id)


@router.post("/{external_id}/consent", response_model=Recipient)
def sync_recipient_consent(
    external_id: str,
    payload: ConsentSyncRequest,
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Apply a CRM consent assertion to the local projection and log it.

    **Two brands arrive here and they answer different questions.** The
    declared brand — `X-Brand`, or a person's working brand — says which brand
    this caller may act in, and `recipients.consent` is checked against it like
    any other brand-scoped write since ADR-150's 2026-09-20 addendum. The
    body's `brand_id` says which brand the CRM is asserting about, which is
    ADR-120's point and why that field is required and undefaulted.

    **They must agree, and a disagreement is refused rather than resolved.**
    Picking either one silently is how a consent record lands on a brand nobody
    checked — reading the body would be the payload choosing the scope its own
    authorisation was evaluated against, which ADR-166 point 8 refuses by name;
    reading the header would quietly overwrite what the CRM actually asserted.
    Keeping both is redundancy on purpose: it is what makes the disagreement
    visible.
    """
    if payload.brand_id != brand_id:
        raise HTTPException(
            status_code=409,
            detail=(
                f"This request declares brand {brand_id} and asserts consent "
                f"for brand {payload.brand_id}. Refusing rather than choosing "
                "one: a consent record is a compliance record."
            ),
        )
    try:
        return sync_consent_from_crm(
            db=db,
            external_id=external_id,
            crm_consent_status=payload.consent_status.value,
            brand_id=payload.brand_id,
            source=payload.source,
            channel=payload.channel,
            purpose=payload.purpose,
            note=payload.note,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get("/{external_id}", response_model=Recipient)
def get_recipient(
    external_id: str,
    db: Session = Depends(get_db),
):
    recipient = get_recipient_by_external_id(
        db=db,
        external_id=external_id,
    )

    if recipient is None:
        raise HTTPException(
            status_code=404,
            detail="Recipient not found",
        )

    return recipient


@router.get(
    "/{recipient_id}/preferences",
    response_model=list[RecipientPreference],
)
def get_preferences(
    recipient_id: int,
    db: Session = Depends(get_db),
):
    return list_preferences_for_recipient(
        db=db,
        recipient_id=recipient_id,
    )


@router.post(
    "/preferences",
    response_model=RecipientPreference,
)
def create_preference(
    payload: RecipientPreferenceCreate,
    db: Session = Depends(get_db),
):
    return create_recipient_preference(
        db=db,
        recipient_id=payload.recipient_id,
        category_id=payload.category_id,
        score=payload.score,
        source=payload.source,
    )