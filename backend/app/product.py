"""What this product is called, read from `product.json` at the repository root.

**The name is provisional** (Tarrow, not yet legally cleared — see
`docs/business/decisions/naming-brand-tarrow.md`), so it lives in exactly one
place and everything that runs reads it from there (task-29): the API's title
and description, the Jinja nav, the session cookie. The React client reads the
same file through `frontend/vite.config.ts`. Prose, file names and YAML cannot
read a value; `scripts/rename_product.py` rewrites those.
"""
import json
from pathlib import Path

_PRODUCT = json.loads((Path(__file__).resolve().parents[2] / "product.json").read_text())

#: For people: page titles, the nav, the API docs. "Tarrow".
PRODUCT_NAME: str = _PRODUCT["name"]
#: For identifiers: lowercase, no spaces. "tarrow".
PRODUCT_SLUG: str = _PRODUCT["slug"]


def register(templates) -> None:
    """Make the name available to every Jinja page as `product_name`."""
    templates.env.globals["product_name"] = PRODUCT_NAME
