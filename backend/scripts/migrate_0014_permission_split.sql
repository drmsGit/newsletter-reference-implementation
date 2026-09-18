-- migrate_0014_permission_split.sql
--
-- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 2,
-- applied to [[ADR-150 — Tenancy and Access Model]] point 5: the permission
-- vocabulary goes from nine keys to sixteen, and two of the new keys are
-- SPLITS out of existing ones rather than additions beside them.
--
-- **A split silently takes capability away.** Before today, `audiences.manage`
-- meant "edit the rules AND pin a member", `sends.execute` meant "prepare AND
-- fire", and correcting a system pick was reachable under `campaigns.manage`.
-- After today each of those acts needs its own key. Anybody holding only the
-- coarse key therefore loses an ability they had yesterday — not by anyone
-- deciding it, but as a side effect of naming things more precisely. That is
-- the most dangerous shape a refactor can take, because it looks additive.
--
-- **Who is actually at risk is narrower than it first appears.** The three
-- preset roles re-sync their permissions from `permissions.py` on every
-- startup (`ensure_builtin_roles`), so Admin and Manager pick the new keys up
-- with no migration at all. But that sync deliberately SKIPS two kinds of row:
-- a built-in role somebody has edited (`is_customised`), because a preset is a
-- starting point and not a standing instruction, and a company's own roles,
-- which it never touches. Those are exactly the roles this migration is for —
-- the ones the automatic path is designed not to reach.
--
-- **Grant, never revoke.** Each statement below adds the finer key to any role
-- already holding its parent, and nothing is removed. A role that could pin
-- yesterday can pin today. Splitting is an opportunity to grant less, and
-- taking it silently — inside a migration, without anyone choosing — would be
-- a security decision made by a refactor. If a company wants the junior
-- marketer who may pin but may not restructure, it removes the parent key
-- deliberately, in the UI, where the act is visible and attributable.
--
-- Idempotent: re-running adds nothing, and `uq_role_permission` would refuse
-- it anyway. Safe to run before or after the application restarts.

-- `audiences.pin` out of `audiences.manage` — pinning one member is not
-- restructuring the audience it is pinned into (ADR-166 point 2's own example:
-- a website form may do the first and must never do the second).
INSERT INTO role_permissions (role_id, permission)
SELECT rp.role_id, 'audiences.pin'
FROM role_permissions rp
WHERE rp.permission = 'audiences.manage'
  AND NOT EXISTS (
        SELECT 1 FROM role_permissions held
        WHERE held.role_id = rp.role_id AND held.permission = 'audiences.pin'
  );

-- `sends.plan` out of `sends.execute` — the line is whether a person receives
-- something because of the request. Snapshotting and creating a send instance
-- reach nobody; dispatching does.
INSERT INTO role_permissions (role_id, permission)
SELECT rp.role_id, 'sends.plan'
FROM role_permissions rp
WHERE rp.permission = 'sends.execute'
  AND NOT EXISTS (
        SELECT 1 FROM role_permissions held
        WHERE held.role_id = rp.role_id AND held.permission = 'sends.plan'
  );

-- `overrides.manage` out of `campaigns.manage`. This one is a split even
-- though it reads like a new key: the override routes live under /ui/campaigns
-- and were matched by that prefix, so anyone who could edit a campaign could
-- already override a pick and reset one.
INSERT INTO role_permissions (role_id, permission)
SELECT rp.role_id, 'overrides.manage'
FROM role_permissions rp
WHERE rp.permission = 'campaigns.manage'
  AND NOT EXISTS (
        SELECT 1 FROM role_permissions held
        WHERE held.role_id = rp.role_id AND held.permission = 'overrides.manage'
  );

-- What is deliberately NOT granted to anybody here: `recipients.manage`,
-- `recipients.consent`, `insight.write` and `integrations.manage`. None of
-- them splits an existing key — they guard routes that had no guard at all,
-- which is the defect ADR-166 exists to close. Handing them out on the way
-- past would grant access that nobody has today, in a migration, which is the
-- opposite of what this file is for.
