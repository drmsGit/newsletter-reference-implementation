"""Write the API's OpenAPI schema to a file, without starting a server.

For the contract check in CI (task-105, ADR-190; ADR-170 point 5): the
backend job writes the schema, the client job generates its types from that
file and fails if they differ from `frontend/src/api/schema.d.ts`. Locally,
`npm run check:contract` reads the same schema from the running API instead.

Imports the app, which checks the database schema on import, so it needs a
reachable database (CI's Postgres service, or the dev one locally).

    venv/bin/python scripts/export_openapi.py openapi.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    import main as app_module

    target.write_text(json.dumps(app_module.app.openapi(), indent=2) + "\n")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
