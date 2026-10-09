from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import enforce_api_policy
from app.auth.permissions import RECIPIENTS_CONSENT
from app.auth.service import has_permission
from app.auth.dependencies import working_brand
from app.pagination import Page, PageParams, page_of_list, page_params
from app.database import get_db
from app.recipients.models import (
    RecipientAudienceGroup,
    RecipientActivity,
    ConsentDriftItem,
    ConsentSyncLog,
    ConsentSyncRequest,
    Recipient,
    RecipientCreate,
    RecipientSignal,
    RecipientPreferenceCreate,
)
from app.recipients.service import (
    create_recipient,
    detect_consent_drift,
    get_recipient_by_external_id,
    create_recipient_preference,
    list_preferences_for_recipient,
    sync_consent_from_crm,
)


router = APIRouter(prefix="/recipients", tags=["recipients"])


@router.post("/", response_model=Recipient)
def create_recipient_record(
    request: Request,
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
        # **On the declared brand, and the body must agree** (task-16) — the
        # rule `/recipients/{external_id}/consent` has kept since ADR-150's
        # 2026-09-20 addendum, which this route never got. It used to check
        # `recipients.consent` with no brand, which meant the union across
        # every brand the caller holds, and then wrote the consent for the
        # body's brand: a caller authorised on brand A could create a
        # recipient carrying brand B's consent. Only here, because creating a
        # plain contact is platform-level and must not start requiring a brand.
        working = working_brand(request)
        if not has_permission(db, principal, RECIPIENTS_CONSENT, brand_id=working):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Creating a recipient needs 'recipients.manage'; asserting "
                    "their consent needs 'recipients.consent' as well, on the "
                    "brand this request declares. Omit consent_status, or grant "
                    "the second permission there."
                ),
            )
        if payload.brand_id != working:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"This request declares brand {working} and asserts consent "
                    f"for brand {payload.brand_id}. Refusing rather than choosing "
                    "one: a consent record is a compliance record."
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


@router.get("/", response_model=Page[Recipient])
def get_recipients(
    q: str | None = Query(None, description="Find by identifier or address on any channel (part, any case)."),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    # A brand as CONTEXT, not authorisation: `recipients.manage` stays
    # platform-level because recipients carry no brand, but their consent does,
    # so projecting it needs one named (ADR-150's 2026-09-20 addendum).
    from app.recipients.service import page_recipients

    return page_recipients(db, params, brand_id=brand_id, q=q)


# --- Consent (CRM-synced) -------------------------------------------------
# Registered before the "/{external_id}" catch-all so these fixed multi-segment
# paths resolve correctly. GET drift/sync-log are 2-segment, so they can't be
# swallowed by the single-segment "/{external_id}" route regardless of order.


@router.get("/consent/drift", response_model=Page[ConsentDriftItem])
def get_consent_drift(
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    """Recipients whose platform consent_status diverges from the CRM's most
    recent assertion — a sync that failed to stick, which must not be silent.
    The working brand's drift only (task-307)."""
    # Computed across the log, so paged after (ADR-185, `page_of_list`).
    return page_of_list(detect_consent_drift(db, brand_id=brand_id), params)


@router.get("/consent/sync-log", response_model=Page[ConsentSyncLog])
def get_consent_sync_log(
    recipient_id: int | None = None,
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
):
    from app.recipients.service import page_consent_sync_logs

    return page_consent_sync_logs(db, params, recipient_id=recipient_id)


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
    brand_id: int = Depends(working_brand),
):
    recipient = get_recipient_by_external_id(
        db=db,
        external_id=external_id,
        brand_id=brand_id,
    )

    if recipient is None:
        raise HTTPException(
            status_code=404,
            detail="Recipient not found",
        )

    return recipient


@router.get(
    "/{recipient_id}/preferences",
    response_model=list[RecipientSignal],
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
    response_model=RecipientSignal,
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

@router.get(
    "/{recipient_id}/activity",
    response_model=RecipientActivity,
    summary="One recipient as the recipient page shows them, from the working brand",
    description=(
        "This brand's decisions and deliveries (with each delivery's engagement "
        "trace), the one affinity profile, this brand's consent grid, and the "
        "consent history across brands, labelled. 404 when the recipient does "
        "not exist."
    ),
)
def get_recipient_activity(
    recipient_id: int, db: Session = Depends(get_db), brand_id: int = Depends(working_brand),
):
    from app.recipients.service import recipient_activity

    activity = recipient_activity(db, recipient_id, brand_id=brand_id)
    if activity is None:
        raise HTTPException(status_code=404, detail=f"Recipient {recipient_id} not found")
    return activity


@router.get(
    "/{recipient_id}/audience-groups",
    response_model=Page[RecipientAudienceGroup],
    summary="Which of the working brand's audience groups one person is in, and why",
    description=(
        "Worked out on request for this person on `channel`, as of now; nothing is stored "
        "(task-214, ADR-093). Lists the groups a rule matches or a hand-add touches, each with "
        "`member` and its reasons, paged like the group list (ADR-185). `channel` is required: "
        "there is no channel-less answer (ADR-176 point 5). 404 when the recipient does not exist."
    ),
)
def get_recipient_audience_groups(
    recipient_id: int,
    channel: str = Query(...),
    params: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    brand_id: int = Depends(working_brand),
):
    from app.audience.service import audience_memberships
    from app.channels.registry import is_registered
    from app.recipients.db_models import RecipientDB

    if not is_registered(channel):
        raise HTTPException(status_code=422, detail=f"{channel!r} is not a registered channel.")
    if db.get(RecipientDB, recipient_id) is None:
        raise HTTPException(status_code=404, detail=f"Recipient {recipient_id} not found")
    return page_of_list(audience_memberships(db, recipient_id, brand_id=brand_id, channel=channel), params)
