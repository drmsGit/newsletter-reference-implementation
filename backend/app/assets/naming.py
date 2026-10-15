"""Generated image names (ADR-197 point 9; task-112 decision 5).

"Maintaining it is the difficult part (especially if it comes to special
characters)", the user said, "so we need some process in the back so 'search
only' is actually possible." So the template is applied here, and the typed
name is reduced to plain lowercase words with hyphens: umlauts and accents
spelled out or dropped, nothing a file system or a URL would trip on.
"""
import json
import re
import unicodedata
from datetime import date
from functools import lru_cache
from pathlib import Path

SETUP_PATH = Path(__file__).resolve().parents[3] / "storage" / "assets.json"
DEFAULT_TEMPLATE = "{brand}-{date}-{n}-{width}x{height}-{name}"
_SPELLED = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue", "&": "and"}


@lru_cache(maxsize=1)
def name_template() -> str:
    try:
        return json.loads(SETUP_PATH.read_text()).get("name_template") or DEFAULT_TEMPLATE
    except FileNotFoundError:
        return DEFAULT_TEMPLATE


def clean(text: str) -> str:
    """Plain lowercase words joined by hyphens."""
    spelled = "".join(_SPELLED.get(ch, ch) for ch in text)
    ascii_only = unicodedata.normalize("NFKD", spelled).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-") or "image"


def generate(*, label: str, day: date, n: int, width: int, height: int, extension: str,
             product_id: str | None = None, brand: str = "") -> str:
    values = {"brand": clean(brand) if brand else "", "date": day.strftime("%Y%m%d"), "n": n, "width": width, "height": height,
              "name": clean(label), "product_id": clean(product_id) if product_id else ""}
    base = name_template().format(**values)
    return f"{re.sub(r'-{2,}', '-', base).strip('-')}.{extension}"
