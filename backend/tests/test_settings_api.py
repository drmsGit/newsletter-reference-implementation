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
    tasks = list_tasks()
    assert tasks, "no AI task is registered"
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
