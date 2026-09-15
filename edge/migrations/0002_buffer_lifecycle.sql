-- Document 45 (SPEC-EDGE-003) closes out the delivery-state/retention/observability gaps that
-- 0001_initial.sql's reduced (pending|sent|acked) model left open:
--   BUF-FR-006 (REJECTED_REVIEW is a real, persisted state -- rejection_code records why),
--   BUF-FR-009 (exponential backoff needs the already-declared-but-unused next_attempt_at indexed),
--   BUF-FR-020 (rejected payload retained for admin reconciliation, never silently dropped),
--   BUF-FR-022 (bulk historical backfill separately tagged, same idempotency/validation path).
-- Purely additive (new nullable/defaulted columns + an index) -- no destructive change, no rewrite of
-- existing rows (MIG-FR-004 expand pattern).

ALTER TABLE edge_outbox ADD COLUMN rejection_code TEXT;
ALTER TABLE edge_outbox ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'live';

CREATE INDEX IF NOT EXISTS idx_edge_outbox_send
ON edge_outbox (state, next_attempt_at, gateway_sequence);
