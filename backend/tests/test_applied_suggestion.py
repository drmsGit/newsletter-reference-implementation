"""Taking an AI suggestion is a variant edit that says where the copy came
from (task-367; ADR-141 §3), as the Jinja page's "Use this" did.
"""
from app.ai.db_models import AIRunDB
from app.audit.db_models import AuditEventDB
from tests import test_render_skip as fixtures
from tests.test_api_guard import signed_in

db = fixtures.db
world = fixtures.world


def _save(db, variant, run_id):
    with signed_in(db) as (client, _token, csrf):
        composition = client.get(f"/campaigns/{variant.campaign_id}/composition").json()
        version = next(v["variant"]["updated_at"] for v in composition["variants"] if v["variant"]["id"] == variant.id)
        response = client.put(f"/campaigns/variants/{variant.id}", json={
            "name": variant.name, "envelope": {"subject": "Spring is here", "preheader": "A peek"},
            "applied_suggestion_run_id": run_id}, headers={"X-CSRF-Token": csrf, "If-Match": version})
    assert response.status_code == 200, response.text
    db.expire_all()
    return (db.query(AuditEventDB).filter_by(action="variant.updated", subject_type="variant", subject_id=variant.id)
            .order_by(AuditEventDB.id.desc()).first())


def _run(db, target_id):
    run = AIRunDB(task_key="subject_preheader", provider="mock", status="ok", target_type="variant",
                  target_id=target_id, output_text="[]")
    db.add(run)
    db.commit()
    return run


def test_the_entry_names_the_run_the_copy_came_from(db, world):
    variant = world["variant"]()
    run = _run(db, variant.id)
    try:
        entry = _save(db, variant, run.id)
        assert entry.detail["applied_suggestion"] is True and entry.detail["ai_run_id"] == run.id
        assert entry.detail["envelope"]["subject"] == "Spring is here"
    finally:
        db.delete(run)
        db.commit()


def test_a_run_of_another_variant_is_not_named(db, world):
    variant, other = world["variant"](), world["variant"]()
    run = _run(db, other.id)
    try:
        entry = _save(db, variant, run.id)
        assert "applied_suggestion" not in entry.detail
    finally:
        db.delete(run)
        db.commit()


def test_a_held_run_names_its_approval_and_an_inline_one_none(db, world):
    """The editor offers "Use this" only on a run nobody has to approve: a held
    run's options are taken in Approvals, as the Jinja page sends them."""
    from app.approvals import service as approvals
    from app.approvals.actions import ai_subject_apply
    from app.approvals.db_models import PendingActionDB
    from app.auth.service import ensure_default_brand

    variant = world["variant"]()
    inline, held = _run(db, variant.id), _run(db, variant.id)
    action = approvals.request_approval(
        db, ai_subject_apply.META.key, payload={"ai_run_id": held.id}, summary="t367",
        requested_by_type="system", brand_id=ensure_default_brand(db).id, subject_id=held.id)
    try:
        with signed_in(db) as (client, _token, _csrf):
            runs = {r["run_id"]: r for r in client.get(f"/campaigns/variants/{variant.id}/suggestions").json()}
        assert runs[held.id]["pending_action_id"] == action.id
        assert runs[inline.id]["pending_action_id"] is None
    finally:
        db.query(PendingActionDB).filter_by(id=action.id).delete()
        db.delete(inline)
        db.delete(held)
        db.commit()


def test_only_the_apply_action_marks_a_run_held(db, world):
    """Another action that happens to be about the same run is not its approval."""
    from app.approvals.db_models import PendingActionDB

    variant = world["variant"]()
    run = _run(db, variant.id)
    other = PendingActionDB(action_key="t367_other", payload={}, summary="t367", requested_by_type="system",
                            subject_type="ai_run", subject_id=run.id)
    db.add(other)
    db.commit()
    try:
        with signed_in(db) as (client, _token, _csrf):
            [listed] = client.get(f"/campaigns/variants/{variant.id}/suggestions").json()
        assert listed["pending_action_id"] is None
    finally:
        db.delete(other)
        db.delete(run)
        db.commit()


def test_another_tasks_run_on_the_variant_is_no_subject_suggestion(db, world):
    """task-370's topic runs are pointed at the variant too; the subject panel
    showed one as an unreadable suggestion."""
    variant = world["variant"]()
    subject, topic = _run(db, variant.id), AIRunDB(task_key="variant_from_topic", provider="mock", status="ok",
                                                  target_type="variant", target_id=variant.id, output_text="{}")
    db.add(topic)
    db.commit()
    try:
        with signed_in(db) as (client, _token, _csrf):
            runs = client.get(f"/campaigns/variants/{variant.id}/suggestions").json()
        assert [r["run_id"] for r in runs] == [subject.id]
    finally:
        db.delete(topic)
        db.delete(subject)
        db.commit()
