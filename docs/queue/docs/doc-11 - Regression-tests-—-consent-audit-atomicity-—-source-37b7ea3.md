---
id: doc-11
title: Regression tests — consent audit atomicity — source 37b7ea3
type: other
created_date: '2026-10-10 20:58'
updated_date: '2026-10-10 22:04'
---
Source: 37b7ea36a21a92ec2f2c93083c4a2124c987a422; task-340.
Added file: backend/tests/test_consent_audit_atomicity.py (2 parametrized cases, upsert and CRM assertion). ADR-153/163: consent, its actor audit and sync success log share a transaction; audit failure cannot leave a consent change committed.
Validation snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-new-batches-integrated/newsletter-reference-implementation; disposable database app_test_newsletter_reference_implementation_f659ff, distinct from development, no TEST_DATABASE_URL override or .env file. Mock fixtures and vendor HTTP guard active.
Backend commands:
PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_send_consent_audit.py tests/test_consent_audit_atomicity.py — 11 passed, exit 0.
PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests — 1639 passed, 10 existing skips, exit 0.
Snapshot-root command: /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/ruff check --no-cache backend/tests/test_consent_audit_atomicity.py — passed, exit 0.
Batch commit: 0cbd54050f832682e021ea2b67458f0db34e82b7. Only backend/tests/test_consent_audit_atomicity.py changed, 54 lines. Origin push SUCCESS (exit 0) with explicit refspec refs/heads/codex/regression-tests:refs/heads/codex/regression-tests. git ls-remote verified this exact SHA; no main push, merge, or PR.
Tests-branch previous tip 6ae93bb9457167e2192f8d740d24d6d2f6b439c0; production base remains 28aa4e88f4846768a18fd81b66949f959cd3b38a. Source verification is not validation against that older branch base.
Known source defects/open-bug test failures tasks 315-323: none observed. Focused rollback gap covered; relevant source backend suite passes with 10 existing skips. Not an exhaustive coverage claim. Infrastructure failures: none in this batch. Pending integration after publication.


Mutation: PYTHONPATH=/tmp PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q -p task340_atomicity_mutation tests/test_consent_audit_atomicity.py — 2 failed, exit 1, because an early consent commit left one extra consent event despite HTTP 500. Runtime-only plugin forces commit=True; no production files modified. Expected mutation failures are not open source defects.
The older tests branch lacks the new task-340 audit action and actor propagation; no suite success claimed against that older production base.


Post-mutation clean-source recheck: PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_consent_audit_atomicity.py — 2 passed, exit 0. No known open-bug failures or infrastructure-blocked checks remain for this test batch. Awaiting integration.


Integration independently verified 2026-10-10: 1a89071d44ec9990775cca2ea837ce343c5273d4 integrates batch 0cbd540, changing the docstring only; strict test bodies preserved.
Scope clarification: these tests cover an audit call that RAISES (a programming error), not SQLAlchemyError swallowed inside audit.record. ADR-153's savepoint/fail-open policy permits the consent operation to succeed without an audit entry for that database error. Read all earlier "audit failure" wording in this note in that narrower sense.
Exact validation snapshot: /Users/diedeslembrouck/.codex/worktrees/regression-neutral-prompt/newsletter-reference-implementation, pinned to the integration SHA; database app_test_newsletter_reference_implementation_045474, distinct from development; no TEST_DATABASE_URL override or .env file, mocked fixtures and vendor guard.
Backend cwd commands:
PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests/test_consent_audit_atomicity.py — 2 passed, exit 0.
PYTHON_DOTENV_DISABLED=1 /Users/diedeslembrouck/Projects/newsletter-reference-implementation/backend/venv/bin/python -m pytest -q tests — 1652 passed, 10 existing skips, exit 0.
Integration complete and verified; no new batch or push needed. No infrastructure-blocked verification remains for this integration.
