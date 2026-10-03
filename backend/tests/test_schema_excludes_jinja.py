"""The OpenAPI schema describes the JSON plane, not the frozen Jinja UI (task-244).

`frontend/src/api/schema.d.ts` is generated from `/openapi.json`, and on
2026-10-02 88 of its 198 paths were `/ui` form posts and pages the React client
never calls — noise in every regeneration, in `check:contract` diffs, and in
`/docs`. The Jinja routes still SERVE exactly as before (`test_jinja_freeze`
pins them); they are only left out of what is documented.
"""
from main import app
from app.frontend.router import router as frontend_router


def _schema_paths() -> set[str]:
    app.openapi_schema = None  # never a cached copy from an earlier test
    return set(app.openapi()["paths"])


def test_no_ui_path_is_documented_whichever_router_declares_it():
    documented = _schema_paths()
    leaked = sorted(p for p in documented if p.startswith("/ui"))
    assert not leaked, f"Jinja routes in the schema: {leaked[:5]}"
    # The auth router serves /ui/login, /ui/users and /ui/roles itself, so
    # hiding the frontend router alone would have left these behind.
    registered = {getattr(r, "path", "") for r in app.routes}
    assert {"/ui/login", "/ui/users", "/ui/roles"} <= registered


def test_no_jinja_page_is_documented_even_outside_ui():
    """The dashboard is the frontend router's `GET /`."""
    jinja_paths = {r.path for r in frontend_router.routes}
    assert "/" in jinja_paths
    assert not (jinja_paths & _schema_paths())


def test_the_json_plane_is_still_documented():
    documented = _schema_paths()
    assert {"/campaigns/", "/settings", "/delivery/send-instances", "/auth/session"} <= documented
