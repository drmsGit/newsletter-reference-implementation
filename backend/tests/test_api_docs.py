"""API documentation exposure (ADR-184; tasks 31 and 232).

`API_DOCS` is read when `main` is imported, so the non-default modes run in a
fresh interpreter pointed at the test database — the real app, middleware and
guards included, rather than a stand-in built for the test.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.auth import service as auth
from main import app

BACKEND = Path(__file__).resolve().parents[1]
client = TestClient(app, raise_server_exceptions=False)


def _in_mode(mode: str, script: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "API_DOCS": mode}  # DATABASE_URL already points at the test DB
    return subprocess.run(
        [sys.executable, "-c", script], cwd=BACKEND, env=env,
        capture_output=True, text=True, timeout=120,
    )


_PROBE = """
import json
from fastapi.testclient import TestClient
from app.auth import service as auth
from main import app
from tests.machine import machine
from app.auth.permissions import VIEW
c = TestClient(app, raise_server_exceptions=False)
out = {p: c.get(p).status_code for p in ("/openapi.json", "/docs", "/redoc")}
with machine([VIEW]) as headers:
    out.update({"with_view" + p: c.get(p, headers=headers).status_code
                for p in ("/openapi.json", "/docs", "/redoc")})
print("RESULT" + json.dumps(out))
"""


def _probe(mode: str) -> dict:
    run = _in_mode(mode, _PROBE)
    line = next((l for l in run.stdout.splitlines() if l.startswith("RESULT")), None)
    assert line, run.stdout[-2000:] + run.stderr[-2000:]
    return json.loads(line[len("RESULT"):])


class TestThePublicDefault:
    def test_the_schema_and_docs_are_open(self):
        for path in ("/openapi.json", "/docs", "/redoc"):
            assert client.get(path).status_code == 200, path

    def test_the_schema_declares_the_authentication_that_exists(self):
        schema = client.get("/openapi.json").json()
        assert set(schema["components"]["securitySchemes"]) == {
            "SessionCookie", "CsrfToken", "MachineKey", "Brand"}
        assert schema["components"]["securitySchemes"]["SessionCookie"]["name"] == auth.SESSION_COOKIE
        assert {"MachineKey": [], "Brand": []} in schema["security"]

    def test_sign_in_and_webhooks_need_no_credential(self):
        paths = client.get("/openapi.json").json()["paths"]
        assert paths["/auth/session/verify"]["post"]["security"] == []
        assert paths["/provider/webhooks/resend"]["post"]["security"] == []
        assert "security" not in paths["/content/"]["get"], "a guarded route inherits the global rule"

    def test_try_it_out_sends_the_session_cookie(self):
        assert '"withCredentials": true' in client.get("/docs").text


class TestTheOtherModes:
    def test_signed_in_needs_view_for_all_three(self):
        result = _probe("signed_in")
        for path in ("/openapi.json", "/docs", "/redoc"):
            assert result[path] == 401, (path, result)
            assert result["with_view" + path] == 200, (path, result)

    def test_off_serves_none_of_them(self):
        result = _probe("off")
        for path in ("/openapi.json", "/docs", "/redoc"):
            assert result[path] == 404 and result["with_view" + path] == 404, (path, result)

    def test_an_unknown_value_stops_startup(self):
        run = _in_mode("sometimes", "import main")
        assert run.returncode != 0
        assert "API_DOCS='sometimes'" in run.stderr
