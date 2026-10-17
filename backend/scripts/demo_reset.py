"""Reset the dev database to the Grathaus demo (task-71).

    ./venv/bin/python scripts/demo_reset.py --yes

Empties all demo data — content, campaigns, sends, recipients, results,
audiences, approvals, AI runs, the image library and its files, and every
brand but the two Grathaus ones — and builds the demo from scripts/demo/
(see app/demo/reset.py for what is kept: accounts, roles, Settings,
integrations, the audit log).

Destructive, so it asks for --yes, and it refuses the test database (the suite
builds its own baseline with seed_demo_data.py). The send cap is read, never
raised.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv: list[str]) -> int:
    if "--yes" not in argv:
        print(__doc__)
        print("Nothing was changed. Run again with --yes to reset.")
        return 2
    import main as _app  # noqa: F401 — registers every model, as the app does
    from app.database import SessionLocal, engine

    current = engine.url.database or ""
    # By the name the suite gives every test database (`<dev>_test...`), and
    # by the run itself: inside pytest or CI the URL in the environment may be
    # the test database's, so comparing it with "the dev URL" proves nothing.
    if "_test" in current or os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("CI"):
        print(f"Refused: {current!r} is a test database, or this runs under pytest or CI. "
              "The demo reset is for the dev database.")
        return 3

    from app.demo.reset import run

    db = SessionLocal()
    try:
        outcome = run(db)
    finally:
        db.close()
    print("Grathaus demo built:")
    for line in outcome.lines:
        print(line)
    if outcome.problems:
        print(f"\n{len(outcome.problems)} things to look at:")
        for problem in outcome.problems:
            print("  -", problem)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
