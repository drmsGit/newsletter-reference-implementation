"""The settings API (task-49 C2, task-50 B5–B8; ADR-150/ADR-142 addenda 2026-10-02).

Three rules each get a test that fails without them: writes are PEOPLE ONLY,
prompts and models need `ai.run` as well as `settings.manage`, and the value
rules live in the service, so the Jinja page refuses the same things as JSON.
Every test restores `app_config`, which is shared by the whole suite.
"""
import uuid
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.ai.db_models import AIPromptDB
from app.ai.tasks.registry import list_tasks
from app.auth import service as auth
from app.auth.db_models import RoleDB, RolePermissionDB
from app.auth.permissions import SETTINGS_MANAGE, VIEW
from app.database import SessionLocal
from app.settings import service as settings
from app.settings.db_models import AppConfigDB
from main import app
from tests.machine import machine
from tests.test_api_guard import signed_in

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def restore_config(db):
    """Put every config row back, and remove prompt versions a test published."""
    saved = {row.key: row.value for row in db.query(AppConfigDB).all()}
    prompt_ids = {row.id for row in db.query(AIPromptDB.id).all()}
    published = {row.id for row in db.query(AIPromptDB).filter(AIPromptDB.is_published.is_(True))}
    yield
    db.rollback()
    db.query(AppConfigDB).filter(AppConfigDB.key.notin_(list(saved))).delete(
        synchronize_session=False)
    for key, value in saved.items():
        settings.set_config(db, key, value)
    db.query(AIPromptDB).filter(AIPromptDB.id.notin_(list(prompt_ids))).delete(
        synchronize_session=False)
    for row in db.query(AIPromptDB).all():
        row.is_published = row.id in published
    db.commit()


@pytest.fixture
def task_key():
    # One that can be held, so the approval round trip has a switch to turn
    # (a task may have no held form: ADR-140 addendum 2026-10-16).
    tasks = [t for t in list_tasks() if t.held_form]
    assert tasks, "no AI task with an approval step is registered"
    return tasks[0].key


@contextmanager
def person_with(db, permissions):
    """A person whose only role carries exactly `permissions`."""
    role = auth.create_role(db, key=f"set-{uuid.uuid4().hex[:6]}", name="settings test")
    auth.set_role_permissions(db, role.id, permissions)
    user = auth.create_user(db, email=f"set-{uuid.uuid4().hex[:8]}@example.invalid",
                            role_key=role.key)
    token = auth.create_session(db, user)
    cookied = TestClient(app, raise_server_exceptions=False)
    cookied.cookies.set(auth.SESSION_COOKIE, token)
    try:
        yield cookied, {"X-CSRF-Token": auth.csrf_token_for(token)}, token
    finally:
        db.rollback()
        for table in ("login_codes", "auth_sessions", "role_assignments"):
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :u"), {"u": user.id})
        db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
        db.query(RolePermissionDB).filter(RolePermissionDB.role_id == role.id).delete()
        db.query(RoleDB).filter(RoleDB.id == role.id).delete()
        db.commit()


@contextmanager
def admin(db):
    with signed_in(db) as (cookied, _token, csrf):
        yield cookied, {"X-CSRF-Token": csrf}


class TestReading:
    def test_anyone_with_view_reads_everything_the_screen_shows(self, task_key):
        with machine([VIEW]) as headers:
            response = client.get("/settings", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert {c["name"] for c in body["channels"]} >= {"email"}
        assert all(isinstance(c["available"], bool) for c in body["channels"])
        assert isinstance(body["ai_key_present"], bool)
        assert task_key in {t["key"] for t in body["ai_tasks"]}
        assert {"tokens_remaining", "over_warn"} <= set(body["ai_budget"])
        attribution = {p["name"]: p["click_content_attribution"] for p in body["delivery_providers"]}
        assert attribution == {"mock": False, "resend": True}, "which providers credit content (task-240)"

    def test_a_switched_off_channel_reads_as_unavailable(self, db):
        settings.set_channel_available(db, "push", False)
        with machine([VIEW]) as headers:
            channels = client.get("/settings", headers=headers).json()["channels"]
        assert {c["name"]: c["available"] for c in channels}["push"] is False


class TestPeopleOnly:
    def test_a_machine_holding_settings_manage_cannot_write(self, db):
        before = settings.get_max_send_recipients(db)
        with machine([VIEW, SETTINGS_MANAGE]) as headers:
            response = client.put("/settings/send-cap", json={"max_send_recipients": before + 1},
                                  headers=headers)
        assert response.status_code == 403, response.text
        db.expire_all()
        assert settings.get_max_send_recipients(db) == before

    def test_a_viewer_cannot_write(self, db):
        with person_with(db, [VIEW]) as (c, h, _t):
            response = c.put("/settings/send-cap", json={"max_send_recipients": 7}, headers=h)
        assert response.status_code == 403

    def test_a_person_with_settings_manage_can(self, db):
        with person_with(db, [SETTINGS_MANAGE]) as (c, h, _t):
            response = c.put("/settings/send-cap", json={"max_send_recipients": 7}, headers=h)
        assert response.status_code == 200, response.text
        db.expire_all()
        assert settings.get_max_send_recipients(db) == 7


class TestPromptsAndModelsNeedAIRun:
    def test_settings_manage_alone_cannot_publish_a_prompt(self, db, task_key):
        with person_with(db, [SETTINGS_MANAGE]) as (c, h, _t):
            response = c.post(f"/settings/ai/tasks/{task_key}/prompt",
                              json={"body": "a new prompt"}, headers=h)
        assert response.status_code == 403, response.text
        assert db.query(AIPromptDB).filter(AIPromptDB.body == "a new prompt").count() == 0

    def test_settings_manage_alone_cannot_choose_a_model(self, db, task_key):
        with person_with(db, [SETTINGS_MANAGE]) as (c, h, _t):
            response = c.put(f"/settings/ai/tasks/{task_key}/model",
                             json={"model": settings.governed_models()[0]}, headers=h)
        assert response.status_code == 403, response.text

    def test_with_both_a_prompt_is_published_as_a_new_version(self, db, task_key):
        from app.auth.permissions import AI_RUN

        with person_with(db, [SETTINGS_MANAGE, AI_RUN]) as (c, h, _t):
            first = c.post(f"/settings/ai/tasks/{task_key}/prompt", json={"body": "v-a"}, headers=h)
            second = c.post(f"/settings/ai/tasks/{task_key}/prompt", json={"body": "v-b"}, headers=h)
        assert first.status_code == second.status_code == 201, second.text
        assert second.json()["version"] == first.json()["version"] + 1
        assert second.json()["is_published"] is True

    def test_the_jinja_page_needs_ai_run_too(self, db, task_key):
        with person_with(db, [SETTINGS_MANAGE]) as (c, _h, token):
            c.follow_redirects = False
            response = c.post("/ui/settings/ai-prompt", data={
                "task_key": task_key, "body": "jinja prompt",
                "csrf_token": auth.csrf_token_for(token)})
        assert response.status_code == 303 and "error=" in response.headers["location"]
        assert db.query(AIPromptDB).filter(AIPromptDB.body == "jinja prompt").count() == 0


    def test_the_jinja_model_choice_needs_ai_run_too(self, db, task_key):
        before = settings.get_task_model(db, task_key)
        with person_with(db, [SETTINGS_MANAGE]) as (c, _h, token):
            c.follow_redirects = False
            response = c.post("/ui/settings/ai-task-model", data={
                "task_key": task_key, "model": settings.governed_models()[0],
                "csrf_token": auth.csrf_token_for(token)})
        assert response.status_code == 303 and "error=" in response.headers["location"]
        db.expire_all()
        assert settings.get_task_model(db, task_key) == before

class TestTheValueRules:
    def test_a_zero_half_life_is_refused_and_nothing_is_stored(self, db):
        before = settings.get_half_lives(db)
        with admin(db) as (c, h):
            response = c.put("/settings/signals", headers=h,
                             json={"weights": {}, "half_lives": {"click": 0}})
        assert response.status_code == 422, response.text
        db.expire_all()
        assert settings.get_half_lives(db) == before

    def test_an_unknown_contribution_type_is_refused(self, db):
        with admin(db) as (c, h):
            response = c.put("/settings/signals", headers=h,
                             json={"weights": {"telepathy": 3}, "half_lives": {}})
        assert response.status_code == 422

    def test_signals_replace_the_overrides(self, db):
        with admin(db) as (c, h):
            response = c.put("/settings/signals", headers=h,
                             json={"weights": {"click": 7.5}, "half_lives": {"click": 30}})
        assert response.status_code == 200, response.text
        assert response.json()["weights"]["click"] == 7.5
        assert response.json()["half_lives"]["click"] == 30

    def test_a_warning_above_the_hard_stop_is_refused(self, db):
        with admin(db) as (c, h):
            response = c.put("/settings/ai/spend-cap", headers=h,
                             json={"warn_tokens": 900, "hard_stop_tokens": 100})
        assert response.status_code == 422, response.text

    def test_an_unknown_provider_is_refused(self, db):
        before = settings.get_ai_provider_name(db)
        with admin(db) as (c, h):
            response = c.put("/settings/ai/provider", json={"provider": "oracle"}, headers=h)
        assert response.status_code == 422
        db.expire_all()
        assert settings.get_ai_provider_name(db) == before

    def test_an_ungoverned_model_is_refused_not_silently_cleared(self, db, task_key):
        with admin(db) as (c, h):
            response = c.put(f"/settings/ai/tasks/{task_key}/model",
                             json={"model": "gpt-imaginary"}, headers=h)
        assert response.status_code == 422, response.text

    def test_an_unknown_task_is_not_found(self, db):
        with admin(db) as (c, h):
            response = c.put("/settings/ai/tasks/no-such-task/approval",
                             json={"mode": "require_approval"}, headers=h)
        assert response.status_code == 404

    def test_the_approval_mode_round_trips(self, db, task_key):
        with admin(db) as (c, h):
            response = c.put(f"/settings/ai/tasks/{task_key}/approval",
                             json={"mode": "require_approval"}, headers=h)
        assert response.json()["mode"] == "require_approval"

    def test_the_jinja_page_refuses_a_zero_half_life_too(self, db):
        before = settings.get_half_lives(db)
        with signed_in(db) as (c, token, _csrf):
            c.follow_redirects = False
            response = c.post("/ui/settings", data={
                "halflife__click": "0", "csrf_token": auth.csrf_token_for(token)})
        assert response.status_code == 303 and "error=" in response.headers["location"]
        db.expire_all()
        assert settings.get_half_lives(db) == before


class TestEverySettingsWriteIsAudited:
    """task-245: ADR-153 point 4 makes writes the audit floor, and until
    2026-10-03 no settings write recorded anything — the send cap, the AI
    spend limit, auto-apply for AI output, and the access-control switch
    itself. ADR-142's addendum makes no settings change approvable, so this
    log is the only after-the-fact accountability they have.

    **The guard walks the routes the app actually registers.** A settings write
    added later that is not listed here fails `test_every_route_is_covered`, so
    the author has to give it a payload — and then it is held to the audit too.

    **Every write here is a no-op**: the current value, written back. The send
    cap is never raised and access control is never switched off.
    """

    @pytest.fixture(autouse=True)
    def _remove_own_audit_rows(self, db):
        """The admin users these tests sign in as are deleted afterwards; their
        audit rows would otherwise stay in the shared dev database's log."""
        from app.audit.db_models import AuditEventDB

        start = self._last_audit_id(db)
        yield
        db.rollback()
        db.query(AuditEventDB).filter(
            AuditEventDB.id > start, AuditEventDB.action == "settings.changed",
        ).delete(synchronize_session=False)
        db.commit()

    def _audit_rows(self, db, since_id):
        from app.audit.db_models import AuditEventDB

        db.expire_all()
        return (
            db.query(AuditEventDB)
            .filter(AuditEventDB.id > since_id, AuditEventDB.action == "settings.changed")
            .order_by(AuditEventDB.id.asc())
            .all()
        )

    def _last_audit_id(self, db):
        from app.audit.db_models import AuditEventDB
        from sqlalchemy import func

        return db.query(func.coalesce(func.max(AuditEventDB.id), 0)).scalar()

    def _noop_writes(self, db, task_key, csrf):
        from app.ai.service import get_published_prompt
        from app.ai.tasks.registry import get_task
        from app.auth.dependencies import AUTH_ENFORCED_KEY

        weights, half = settings.get_signal_weights(db), settings.get_half_lives(db)
        cap = settings.get_max_send_recipients(db)
        offer_everything = settings.get_unsubscribe_offer_everything(db)
        spend = settings.get_ai_spend_cap(db)
        provider = settings.get_ai_provider_name(db)
        mode = settings.get_task_approval_mode(db, task_key)
        model = settings.get_task_model(db, task_key)
        published = get_published_prompt(db, task_key)
        body = published.body if published else get_task(task_key).default_prompt
        enforced = bool(settings.get_config(db, AUTH_ENFORCED_KEY, True))
        spend_json = {k: spend[k] for k in ("warn_tokens", "hard_stop_tokens", "budget_usd")}
        form = {"csrf_token": csrf}
        tuning_form = {**form, "max_send_recipients": str(cap),
                       **{f"weight__{t}": str(w) for t, w in weights.items()},
                       **{f"halflife__{t}": str(d) for t, d in half.items()}}
        return {
            ("PUT", "/settings/signals"): ("signals", {"json": {"weights": weights, "half_lives": half}}),
            ("PUT", "/settings/send-cap"): ("send_cap", {"json": {"max_send_recipients": cap}}),
            ("PUT", "/settings/session-lengths"): ("session_lengths", {"json": dict(
                zip(("absolute_hours", "idle_minutes"), settings.get_session_lengths(db)))}),
            ("PUT", "/settings/unsubscribe"): ("unsubscribe", {"json": {"offer_everything": offer_everything}}),
            ("PUT", "/settings/ai/spend-cap"): ("ai_spend_cap", {"json": spend_json}),
            ("PUT", "/settings/ai/budget-period"): ("ai_budget_period", {"json": {
                "period": settings.get_ai_budget_period(db)}}),
            ("PUT", "/settings/ai/provider"): ("ai_provider", {"json": {"provider": provider}}),
            ("PUT", "/settings/ai/tasks/{task_key}/approval"):
                ("ai_task_approval", {"json": {"mode": mode}}),
            ("POST", "/settings/ai/tasks/{task_key}/prompt"):
                ("ai_task_prompt", {"json": {"body": body}}),
            ("PUT", "/settings/ai/tasks/{task_key}/model"):
                ("ai_task_model", {"json": {"model": model}}),
            ("POST", "/ui/settings"): ("signals_and_send_cap", {"data": tuning_form}),
            ("POST", "/ui/settings/ai"): ("ai_spend_cap", {"data": {
                **form, "ai_warn_tokens": str(spend["warn_tokens"]),
                "ai_hard_stop_tokens": str(spend["hard_stop_tokens"]),
                "ai_budget_usd": str(spend["budget_usd"])}}),
            ("POST", "/ui/settings/ai-provider"): ("ai_provider", {"data": {**form, "ai_provider": provider}}),
            ("POST", "/ui/settings/ai-prompt"):
                ("ai_task_prompt", {"data": {**form, "task_key": task_key, "body": body}}),
            ("POST", "/ui/settings/ai-task-approval"):
                ("ai_task_approval", {"data": {**form, "task_key": task_key, "mode": mode}}),
            ("POST", "/ui/settings/ai-task-model"):
                ("ai_task_model", {"data": {**form, "task_key": task_key, "model": model or ""}}),
            # Posted as it already is: this suite must never switch access control off.
            ("POST", "/ui/users/enforcement"):
                ("access_control", {"data": {**form, "enforced": "1" if enforced else ""}}),
        }

    def _registered_writes(self):
        found = set()
        for route in app.routes:
            path = getattr(route, "path", "")
            if not (path.startswith("/settings") or path.startswith("/ui/settings")
                    or path == "/ui/users/enforcement"):
                continue
            for method in getattr(route, "methods", set()) - {"GET", "HEAD", "OPTIONS"}:
                found.add((method, path))
        return found

    def test_every_route_is_covered(self, db, task_key):
        listed = set(self._noop_writes(db, task_key, "x"))
        unlisted = self._registered_writes() - listed
        assert not unlisted, f"settings writes with no audit test: {sorted(unlisted)}"

    def test_each_write_records_who_changed_which_setting(self, db, task_key):
        with admin(db) as (c, h):
            csrf = h["X-CSRF-Token"]
            for (method, path), (setting, kwargs) in self._noop_writes(db, task_key, csrf).items():
                since = self._last_audit_id(db)
                url = path.replace("{task_key}", task_key)
                extra = {"headers": h} if "json" in kwargs else {}
                response = c.request(method, url, follow_redirects=False, **kwargs, **extra)
                assert response.status_code in (200, 201, 303), (path, response.text[:200])
                if response.status_code == 303:
                    assert "error=" not in response.headers["location"], (path, response.headers["location"])
                rows = self._audit_rows(db, since)
                assert len(rows) == 1, f"{method} {path}: {len(rows)} audit rows"
                assert rows[0].detail["setting"] == setting, path
                assert rows[0].actor_id is not None, f"{path}: recorded as nobody"
                assert rows[0].brand_id is None, f"{path}: settings are not brand-owned"

    def test_the_entry_carries_before_and_after(self, db):
        current = settings.get_ai_spend_cap(db)["budget_usd"]
        since = self._last_audit_id(db)
        with admin(db) as (c, h):
            response = c.put("/settings/ai/spend-cap", json={"budget_usd": current + 1}, headers=h)
        assert response.status_code == 200, response.text
        (row,) = self._audit_rows(db, since)
        change = row.detail["changes"]["ai_spend_cap"]
        assert (change["before"] or {}).get("budget_usd") != current + 1
        assert change["after"]["budget_usd"] == current + 1

    def test_a_refused_change_records_nothing(self, db):
        since = self._last_audit_id(db)
        with admin(db) as (c, h):
            response = c.put("/settings/ai/provider", json={"provider": "no-such-provider"}, headers=h)
        assert response.status_code == 422, response.text
        assert self._audit_rows(db, since) == []

    def test_a_published_prompt_is_named_by_version_never_by_body(self, db, task_key):
        since = self._last_audit_id(db)
        with admin(db) as (c, h):
            response = c.post(f"/settings/ai/tasks/{task_key}/prompt",
                              json={"body": "a body that must not reach the log"}, headers=h)
        assert response.status_code == 201, response.text
        (row,) = self._audit_rows(db, since)
        assert row.detail["task"] == task_key
        assert row.detail["version"] == response.json()["version"]
        assert "a body that must not reach the log" not in str(row.detail)


class TestTheScreenIsToldWhatThisCallerMayChange:
    """`may_manage` / `may_configure_ai` on GET /settings (2026-10-03).

    The settings screen shows edit controls only to someone the write routes
    would accept. The flags are the server's answer — the approval inbox's
    `may_decide` pattern — so a client never re-derives who may change what.
    Each case pairs the flag with the write it predicts, so the two cannot drift.
    """

    def _flags(self, c, h):
        body = c.get("/settings", headers=h).json()
        return body["may_manage"], body["may_configure_ai"]

    def test_a_viewer_may_change_nothing(self, db):
        with person_with(db, [VIEW]) as (c, h, _t):
            assert self._flags(c, h) == (False, False)
            current = settings.get_max_send_recipients(db)
            assert c.put("/settings/send-cap", json={"max_send_recipients": current},
                         headers=h).status_code == 403

    def test_settings_manage_alone_may_not_configure_ai(self, db, task_key):
        with person_with(db, [VIEW, SETTINGS_MANAGE]) as (c, h, _t):
            assert self._flags(c, h) == (True, False)
            assert c.put(f"/settings/ai/tasks/{task_key}/model", json={"model": None},
                         headers=h).status_code == 403

    def test_with_ai_run_too_it_may(self, db, task_key):
        from app.auth.permissions import AI_RUN

        with person_with(db, [VIEW, SETTINGS_MANAGE, AI_RUN]) as (c, h, _t):
            assert self._flags(c, h) == (True, True)
            assert c.put(f"/settings/ai/tasks/{task_key}/model", json={"model": None},
                         headers=h).status_code == 200

    def test_a_machine_may_never_change_settings_whatever_it_holds(self):
        from app.auth.permissions import AI_RUN

        with machine([VIEW, SETTINGS_MANAGE, AI_RUN]) as headers:
            body = client.get("/settings", headers=headers).json()
        assert (body["may_manage"], body["may_configure_ai"]) == (False, False)


class TestSignalTuningKeepsDefaultsLive:
    """A value equal to its code default is not stored as an override
    (2026-10-03). Storing it would pin the default: a later change to the code
    default would never reach this deployment, and nothing on screen would say
    so. The screen shows the defaults, so a person can see what blank means."""

    def test_the_defaults_are_readable(self):
        from app.settings.service import CONTRIBUTION_WEIGHTS, HALF_LIFE_DAYS

        with machine([VIEW]) as headers:
            body = client.get("/settings", headers=headers).json()
        assert body["signal_defaults"]["weights"] == CONTRIBUTION_WEIGHTS
        assert body["signal_defaults"]["half_lives"] == HALF_LIFE_DAYS

    def test_saving_the_defaults_stores_no_override(self, db):
        from app.settings.service import CONTRIBUTION_WEIGHTS, HALF_LIFE_DAYS

        any_type = sorted(CONTRIBUTION_WEIGHTS)[0]
        weights = {**CONTRIBUTION_WEIGHTS, any_type: CONTRIBUTION_WEIGHTS[any_type] + 1}
        settings.save_signal_tuning(db, weights, dict(HALF_LIFE_DAYS))
        db.expire_all()
        assert settings.get_config(db, settings.SIGNAL_WEIGHTS) == {
            any_type: CONTRIBUTION_WEIGHTS[any_type] + 1}, "a default was pinned as an override"
        assert settings.get_config(db, settings.HALF_LIFE_DAYS_KEY) == {}
        assert settings.get_signal_weights(db)[any_type] == CONTRIBUTION_WEIGHTS[any_type] + 1
