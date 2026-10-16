# privacy

Empty on purpose. Erasure and retention will live here when built: removing a person on request and pruning data past its retention period. The decision is ADR-154 (Erasure and Retention); the data-lifecycle policy it needs is still open in the queue (task-136, with task-117). Until then nothing in the platform is erased.

**What erasure must reach, once built (added 2026-10-16, task-365).** Since ADR-199 a recipient carries `gender`, `first_name` and `last_name` as columns (`app/recipients/db_models.py`), and each delivery record keeps the personalised texts they received, such as "Dear Ms Müller,", under `delivery_executions.delivery_record["personal"]`. A reconstruction of what was sent reads those values, never the recipient as they are now, so erasing the recipient alone leaves them in every delivery record (ADR-154 point 5).
