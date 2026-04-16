-- Migration Step 1: drop unused indexes, slim sr_levels + candles, reclaim space.
-- All operations transactional. Idempotent guards via IF EXISTS.
--
-- Coordination: this migration changes sr_levels schema (level_type → is_high)
-- and candles schema (drops id). The bot db.py and web/backend/database.py
-- are updated in lockstep — apply all together.

BEGIN;

-- ── 1A. Drop indici mai usati (idx_scan = 0) ────────────────────────────
DROP INDEX IF EXISTS idx_candles_time;          -- 12 MB, mai scansionato

-- ── 1B. Slim sr_levels: rimuovi PK SERIAL + colonne ridondanti ──────────

-- Drop la colonna updated_at (immutabile, duplicato di created_at).
-- Backfill created_at sui vecchi record che hanno NULL.
UPDATE sr_levels SET created_at = updated_at WHERE created_at IS NULL;
ALTER TABLE sr_levels ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE sr_levels ALTER COLUMN created_at SET DEFAULT NOW();
ALTER TABLE sr_levels DROP COLUMN IF EXISTS updated_at;

-- Aggiungi colonna boolean is_high (sostituisce level_type VARCHAR(10))
ALTER TABLE sr_levels ADD COLUMN IF NOT EXISTS is_high BOOLEAN;
UPDATE sr_levels SET is_high = (level_type = 'swing_high') WHERE is_high IS NULL;
ALTER TABLE sr_levels ALTER COLUMN is_high SET NOT NULL;
ALTER TABLE sr_levels DROP COLUMN IF EXISTS level_type;

-- Backfill scan_id sui record antichi pre-migrazione (~60 senza scan_id)
UPDATE sr_levels
SET scan_id = (SELECT MIN(id) FROM scans)
WHERE scan_id IS NULL;
ALTER TABLE sr_levels ALTER COLUMN scan_id SET NOT NULL;

-- Drop il vecchio PK SERIAL (id) — l'indice è 77 MB mai usato.
ALTER TABLE sr_levels DROP CONSTRAINT IF EXISTS sr_levels_pkey;
ALTER TABLE sr_levels DROP COLUMN IF EXISTS id;

-- Rimuovi eventuali duplicati emergenti dal backfill scan_id NULL → MIN(id)
DELETE FROM sr_levels a
USING sr_levels b
WHERE a.ctid < b.ctid
  AND a.scan_id = b.scan_id
  AND a.ticker = b.ticker
  AND a.timeframe = b.timeframe
  AND a.level_price = b.level_price;

-- PK composito ottimizzato per il pattern di accesso del backend:
-- "ultimo scan per ticker/timeframe" → leading columns ticker, timeframe.
ALTER TABLE sr_levels
  ADD CONSTRAINT sr_levels_pkey PRIMARY KEY (ticker, timeframe, scan_id, level_price);

-- Indici secondari ora ridondanti col nuovo PK (idx_sr_levels_ticker = 25 MB,
-- idx_sr_levels_scan = 24 MB) — il PK copre entrambi i pattern di lookup.
DROP INDEX IF EXISTS idx_sr_levels_ticker;
DROP INDEX IF EXISTS idx_sr_levels_scan;

-- ── 1C. Slim candles: drop pkey SERIAL inutile ──────────────────────────
-- L'unique constraint (ticker, timeframe, candle_time) è il vero PK semantico.
-- candles.id non è usato né dal bot (db.py:280-285) né dal backend.
ALTER TABLE candles DROP CONSTRAINT IF EXISTS candles_pkey;
ALTER TABLE candles DROP COLUMN IF EXISTS id;
ALTER TABLE candles
  DROP CONSTRAINT IF EXISTS candles_ticker_timeframe_candle_time_key;
ALTER TABLE candles
  ADD CONSTRAINT candles_pkey PRIMARY KEY (ticker, timeframe, candle_time);

-- ── 1D. signals: NON tocchiamo id (usato dall'API web) ──────────────────
-- signals.id è esposto al frontend come React key (web/backend/database.py:178)
-- — manteniamo lo schema attuale.

COMMIT;

-- ── 1E. VACUUM FULL fuori transazione (richiede AccessExclusiveLock) ────
-- Eseguire separatamente:
--   psql -c "VACUUM FULL ANALYZE candles;"
--   psql -c "VACUUM FULL ANALYZE sr_levels;"
