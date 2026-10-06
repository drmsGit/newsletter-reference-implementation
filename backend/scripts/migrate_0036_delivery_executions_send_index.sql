-- migrate_0036_delivery_executions_send_index.sql
--
-- task-296: audience rules can read engagement history (ADR-188 point 4).
-- A rule about one send ("received the spring send", "clicked it") filters
-- delivery_executions by send_instance_id, which had no index. Measured
-- 2026-10-06 on 100,000 deliveries (200 sends) and 50,000 events, in a
-- rolled-back transaction on the test database:
--   received one send: 4.76 ms / 2,310 buffers -> 1.62 ms / 384
--   clicked one send:  4.73 ms / 2,310 buffers -> 1.96 ms / 384
-- "Received any send in the last 30 days" reads about a third of all rows and
-- scans either way (~18 ms); no index is added for it.
--
-- Safe to re-run.

CREATE INDEX IF NOT EXISTS ix_delivery_executions_send_instance_id
    ON delivery_executions (send_instance_id);
