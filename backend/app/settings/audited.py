"""Every settings change leaves an audit entry (task-245, ADR-153 point 4).

Writes are ADR-153's audit floor, and until 2026-10-03 no settings write met
it — the send cap, the AI spend limit, auto-apply for AI output and the
access-control switch included. ADR-142's addendum makes no settings change
approvable ("whoever holds settings.manage is the authority"), so this log is
the only after-the-fact accountability those changes have.

**The keys a change touches are named, never discovered.** Diffing the whole
`app_config` table would be less typing and would put into the log whatever is
stored there later — including a secret, which ADR-152 keeps out of every log.
"""
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.audit import service as audit
from app.settings.service import get_config


@contextmanager
def audited_settings(request, db: Session, setting: str, keys: list[str]):
    """Record `setting` as changed if — and only if — the block completes.

    A refusal raises out of the block, nothing was written, and nothing is
    recorded. The caller may add to the yielded `note` what is not a config
    key: a published prompt's task and version (never its body).

    `brand_id=None` explicitly: settings are deployment-wide (the policy
    table's `/settings` entry), so the working brand the request happens to
    carry would attribute the change to the wrong thing.
    """
    before = {key: get_config(db, key) for key in keys}
    note: dict = {}
    yield note
    changes = {
        key: {"before": before[key], "after": get_config(db, key)} for key in keys
    }
    audit.record_from_request(
        request, db, audit.SETTINGS_CHANGED, subject_type="setting", brand_id=None,
        detail={"setting": setting, "changes": changes, **note},
    )
