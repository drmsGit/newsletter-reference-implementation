"""Building a variant from a reviewed topic proposal (task-370; ADR-141
addendum 2026-10-17, point 5).

Everything is checked before anything is written — the run is this variant's
proposal, the variant is still empty, the ticked records are still ones a
machine may take and still fill their block, the ticked blocks were proposed
— so a refusal leaves the variant as it was. Then, in the scaffold's order:
the envelope (position 0 anyway, and the one write with refusals of its own,
ADR-199), the hero, the editorial, the image blocks alternating left and
right, and the slot's block continuing the alternation. Each write is the
ordinary one and its audit entry names the run.
"""
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.ai.tasks import variant_from_topic as task
from app.audit import service as audit


def _named(run_id: int) -> dict:
    return {"applied_suggestion": True, "ai_run_id": run_id}


def build(db: Session, request: Request, variant, payload, *, brand_id: int) -> int:
    """The number of blocks built. Raises HTTPException: 404 for a run that is
    not this variant's proposal, 409 for a variant or record that changed,
    422 for a choice the proposal does not hold."""
    from app.ai.db_models import AIRunDB
    from app.campaigns.service import (
        create_decision_slot_for_variant, create_module_for_variant, module_audit_detail, set_envelope_fields,
        slot_audit_detail,
    )

    run = db.get(AIRunDB, payload.run_id)
    if run is None or (run.task_key, run.target_type, run.target_id) != (task.TASK_KEY, "variant", variant.id):
        raise HTTPException(status_code=404, detail="That proposal is not this variant's.")
    if run.status != "ok":
        raise HTTPException(status_code=409, detail="That proposal has nothing to build.")
    try:
        task.check(db, variant)
    except task.ProposalRefused as error:
        raise HTTPException(status_code=409, detail=str(error))
    proposal = task.read_proposal(db, run.output_text or "", (run.input_snapshot or {}).get("offered", {}))

    proposed = [b["record_id"] for b in proposal["blocks"]]
    blocks = proposed if payload.blocks is None else payload.blocks
    foreign = [i for i in blocks if i not in proposed]
    if foreign or len(set(blocks)) != len(blocks):
        raise HTTPException(status_code=422, detail=[{"loc": ["body", "blocks"], "type": "value_error",
                                                      "msg": "Only the proposal's own blocks, each once."}])
    hero = proposal["hero"]["record_id"] if payload.hero and proposal["hero"] else None
    editorial = proposal["editorial"] if payload.editorial is None else payload.editorial.strip()
    slot = proposal["slot"] if payload.slot else None
    envelope = ({"subject": proposal["subject"], "preheader": proposal["preheader"]}
                if payload.envelope and proposal["subject"] else None)
    if not (hero or editorial or blocks or slot or envelope):
        raise HTTPException(status_code=422, detail="Nothing is ticked to build.")

    # Still what a machine may take, and still filling the block it goes in.
    wanted = [i for i in [hero, *blocks] if i is not None]
    now = task.offer(db, variant, brand_id, only=wanted)
    lost = [str(i) for i in wanted
            if str(i) not in now or ("hero" if i == hero else "image") not in now[str(i)]]
    if lost:
        raise HTTPException(status_code=409, detail=(
            f"Record {', '.join(lost)} is no longer one a machine may take for this block (published, ready "
            "for email, machine ready, in this language); nothing was built. Ask for a new proposal."))

    if envelope:
        set_envelope_fields(db, variant.id, envelope, brand_id=brand_id)
        audit.record_from_request(request, db, audit.VARIANT_UPDATED, subject_type="variant", subject_id=variant.id,
                                  detail={"envelope": envelope, **_named(run.id)})

    def module(module_type: str, **kwargs):
        created = create_module_for_variant(db, variant_id=variant.id, module_type=module_type, brand_id=brand_id,
                                            **kwargs)
        audit.record_from_request(request, db, audit.MODULE_CREATED, subject_type="module", subject_id=created.id,
                                  detail={**module_audit_detail(created), **_named(run.id)})

    built = 0
    if hero:
        module(task.HERO, content_record_id=hero)
        built += 1
    if editorial:
        module(task.EDITORIAL, module_data={"text": editorial})
        built += 1
    for index, record_id in enumerate(blocks):
        module(task.IMAGE_BLOCKS[index % 2], content_record_id=record_id)
        built += 1
    if slot:
        created = create_decision_slot_for_variant(
            db, variant_id=variant.id, name="From the topic", candidate_filter={"category_ids": slot["category_ids"]},
            max_results=task.SLOT_PICKS, brand_id=brand_id)
        audit.record_from_request(request, db, audit.DECISION_SLOT_CREATED, subject_type="decision_slot",
                                  subject_id=created.id, detail={**slot_audit_detail(created), **_named(run.id)})
        module(task.IMAGE_BLOCKS[len(blocks) % 2], decision_slot_id=created.id)
        built += 1
    return built
