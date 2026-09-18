-- migrate_0013_signal_contribution_channel.sql
--
-- [[ADR-164 — Channel Feedback and Signals]] point 9: "`SignalContributionDB`
-- gains an explicit `channel` column, and it does not change the topic score."
--
-- **One log, read along two axes.** Topic affinity sums over categories and
-- ignores channel — interest in hiking is interest in hiking wherever it was
-- clicked, so nothing about the existing score changes. Channel affinity sums
-- over channels and ignores category, and is new: the decision layer cannot
-- choose a channel per recipient without knowing which channels that person
-- engages with.
--
-- **Nullable, and the null means NOT APPLICABLE.** A manually declared
-- preference happened on no channel at all. Backfilling it to 'email' would
-- record an engagement nobody had, and it would then be counted in a channel
-- affinity score as evidence of something that never happened.
--
-- **Denormalised rather than derived**, which ADR-164 argues at length: the
-- derivation path is five joins on every read in a layer built around
-- compute-on-read; `event_id` is nullable so a declared preference would
-- answer *unknowable*; and ADR-132 prunes, so a contribution would lose its
-- channel retroactively over exactly the window worth analysing. The backfill
-- below is the one moment deriving is correct — the joins still resolve today,
-- and after this the value is kept rather than recomputed.
--
-- Every backfilled row will read 'email'. That is not an assumption: until
-- ADR-160 point 4 was built (migration 0010), `delivery_executions.channel`
-- defaulted to 'email' for every send ever made, so email is what those
-- engagements actually were.
--
-- Idempotent: safe to run twice.
--
-- Run with:
--   psql "$DATABASE_URL" -f scripts/migrate_0013_signal_contribution_channel.sql

BEGIN;

ALTER TABLE signal_contributions ADD COLUMN IF NOT EXISTS channel VARCHAR(50);

-- Backfill only what is derivable. A contribution with no event has no
-- channel, and that absence is the answer rather than a gap.
UPDATE signal_contributions sc
   SET channel = de.channel
  FROM engagement_events ee
  JOIN delivery_executions de ON de.id = ee.delivery_execution_id
 WHERE sc.event_id = ee.id
   AND sc.channel IS NULL;

CREATE INDEX IF NOT EXISTS ix_signal_contributions_channel
    ON signal_contributions (channel);

COMMIT;

-- ---------------------------------------------------------------------------
-- Verification
-- ---------------------------------------------------------------------------
-- Expect: engagement-sourced rows carry a channel, declared ones do not.
--
--   SELECT source, channel, count(*) FROM signal_contributions
--    GROUP BY source, channel ORDER BY source, channel;
--
-- Expect zero rows — an engagement contribution whose channel is derivable
-- but still null:
--
--   SELECT count(*) FROM signal_contributions sc
--     JOIN engagement_events ee ON ee.id = sc.event_id
--     JOIN delivery_executions de ON de.id = ee.delivery_execution_id
--    WHERE sc.channel IS NULL;
