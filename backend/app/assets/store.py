"""Where image files live (ADR-197 point 10, the ADR-101 seam).

One declaration — put, get — with a local-disk implementation today. Object
storage or an adopter's DAM goes behind the same two calls; nothing outside
this file knows where the bytes are. The location is set per installation:
`ASSETS_DIR`, or `storage/assets/` (gitignored), following ADR-152's "the
environment is the interface". **A folder per brand**, named by the brand's
permanent key (decided with the user 2026-10-15), so one brand's images can be
backed up, moved or handed over on their own.
"""
import os
import re
from pathlib import Path

DEFAULT_DIR = Path(__file__).resolve().parents[3] / "storage" / "assets"


class LocalAssetStore:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or os.environ.get("ASSETS_DIR") or DEFAULT_DIR)

    def _path(self, brand_key: str, token: str) -> Path:
        # Both parts are ours (a permanent brand key, a hex token), never a
        # caller's string, but a path is still only ever built from what they
        # may contain.
        if not token.isalnum() or not re.fullmatch(r"[A-Za-z0-9_-]+", brand_key or ""):
            raise ValueError("not an asset location")
        return self.root / brand_key / token

    def put(self, brand_key: str, token: str, data: bytes) -> None:
        path = self._path(brand_key, token)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".part")
        temporary.write_bytes(data)
        temporary.replace(path)  # a replacement is never seen half-written

    def get(self, brand_key: str, token: str) -> bytes | None:
        path = self._path(brand_key, token)
        return path.read_bytes() if path.is_file() else None


def get_store() -> LocalAssetStore:
    return LocalAssetStore()
