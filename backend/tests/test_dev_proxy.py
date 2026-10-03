"""The Vite dev proxy forwards every path the backend owns (2026-10-03).

`frontend/vite.config.ts` lists the backend's top-level prefixes by hand, so
the browser sees one origin in development (ADR-168 point 3). A router added
later without a line there works in every test — the client's tests stub
`fetch` and never pass through Vite — and returns 404 the first time a person
opens the screen. `/settings` and `/integrations` were missing exactly that way.
"""
import re
from pathlib import Path

from main import app

VITE_CONFIG = Path(__file__).resolve().parents[2] / "frontend" / "vite.config.ts"

#: Owned by the backend but deliberately not proxied: in development the
#: client itself is served by Vite at `/manager/`, and proxying it would send
#: the page to FastAPI's built copy instead of the live one.
NOT_PROXIED = {"/manager"}


def _backend_prefixes() -> set[str]:
    return {
        "/" + route.path.strip("/").split("/")[0]
        for route in app.routes
        if getattr(route, "path", "/").startswith("/") and route.path != "/"
    }


def _proxied() -> set[str]:
    return set(re.findall(r"^  '(/[^']*)',", VITE_CONFIG.read_text(), re.M))


def test_every_backend_prefix_is_proxied():
    missing = _backend_prefixes() - NOT_PROXIED - _proxied()
    assert not missing, f"add to API_PREFIXES in frontend/vite.config.ts: {sorted(missing)}"


def test_nothing_proxied_that_the_backend_does_not_own():
    stale = _proxied() - _backend_prefixes()
    assert not stale, f"proxied but no longer a backend route: {sorted(stale)}"
