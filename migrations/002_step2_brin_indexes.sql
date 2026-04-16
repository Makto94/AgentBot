-- Migration Step 2: BRIN indexes su colonne tempo + drop colonna morta sr_levels.timeframe.
-- BRIN è ideale per dati naturalmente ordinati cronologicamente: ~kB invece di MB.

BEGIN;

-- ── 2A. sr_levels.timeframe è 100% '4h' — colonna morta nel PK ─────────
-- Ridimensiona il PK per liberare ~14 MB sull'indice composito.
ALTER TABLE sr_levels DROP CONSTRAINT sr_levels_pkey;
ALTER TABLE sr_levels DROP COLUMN timeframe;
ALTER TABLE sr_levels ADD PRIMARY KEY (ticker, scan_id, level_price);

COMMIT;

-- ── 2B. BRIN indexes — fuori transazione per CONCURRENTLY ─────────────
-- (Eseguire le CREATE INDEX CONCURRENTLY separatamente, vedi sotto)
