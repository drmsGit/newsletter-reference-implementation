---
id: doc-5
title: Regression tests — task-320 and task-321 — source ffb68c8
type: other
created_date: '2026-10-09 08:58'
updated_date: '2026-10-09 09:02'
---
Source commit: ffb68c8fc7fa129e0a208ca1b7b6fa12a90ac14f (task-321), including task-320's earlier source 7074102d52589b1bc43907b9fb9329e5ecc6120c.
Tests-branch batch: e3e952bace9f0ffeada801f81461a9fed4870094; pushed successfully to origin/codex/regression-tests and remote SHA verified.

Added: backend/tests/test_decision_send_pipeline.py.
The parametrized email/push regression uses the real decision engine and mock provider. It requires an eligible first send, removes channel readiness, then requires exclusion with nothing-to-show and no second delivery. ADR-163, ADR-174/179 and ADR-086 apply.

Verification:
- Exact task-320 snapshot /Users/diedeslembrouck/.codex/worktrees/regression-integrated/newsletter-reference-implementation: targeted test_stale_pick.py and test_render_skip.py: 13 passed. Full backend: 1540 passed, 10 existing skips, exit 0.
- Exact combined source /Users/diedeslembrouck/.codex/worktrees/regression-push-consent/newsletter-reference-implementation: existing test_slot_consent_channel.py: 3 passed. New test_decision_send_pipeline.py plus test_stale_pick.py and test_slot_consent_channel.py: 7 passed. Full backend including the new file: 1545 passed, 10 existing skips, exit 0.
- Passing full-suite invocations run from each snapshot's backend directory: /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests. Targeted commands from that directory: /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_stale_pick.py tests/test_render_skip.py (task-320, 13 passed); /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_slot_consent_channel.py (combined source, 3 passed); /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_decision_send_pipeline.py tests/test_stale_pick.py tests/test_slot_consent_channel.py (combined source, 7 passed, also confirmed again after publication). Ruff check --no-cache backend/tests/test_decision_send_pipeline.py passed from the snapshot root. The working directory matters: Jinja templates and migration scripts resolve relative to backend.
- On the persistent tests branch (production base 28aa4e88f4846768a18fd81b66949f959cd3b38a), python -m pytest -q backend/tests/test_decision_send_pipeline.py exits 1: email exposes task-320 (historical pick reused after readiness removal); push exposes task-321 (email consent checked despite push-only consent). Both failures remain strict. These are older-base failures, not failures on the tested fixed source.

Separate checkout-derived disposable PostgreSQL databases: task-320 app_test_newsletter_reference_implementation_0f33c8; combined source app_test_newsletter_reference_implementation_edfa42; tests branch app_test_newsletter_reference_implementation_17aa4d. Mock delivery only. No infrastructure-blocked checks; frontend suite not run for this backend-only batch. Existing Starlette deprecation warning remains.

The persistent tests branch retains its older production history and earlier batches; production changes were not merged. Claude should review/apply this test-only batch with the corresponding fixes before running its suite. Never integrate the strict older-base failures alone into main. Coverage improved for these reviewed behaviors; this is not an exhaustive proof of all send/decision behavior.

