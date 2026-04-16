-- Migration Step 4: convert candles to TimescaleDB hypertable + columnar compression.
-- sr_levels NON viene convertita: il pattern d'accesso "ultimo scan per ticker"
-- non beneficia del partitioning temporale.

-- ── 4A. Convert candles to hypertable, partitioned by candle_time ──────
-- chunk_time_interval = 1 mese: con ~125k righe/mese ogni chunk è ~5 MB.
SELECT create_hypertable(
  'candles',
  'candle_time',
  chunk_time_interval => INTERVAL '1 month',
  migrate_data => TRUE
);

-- ── 4B. Compression policy ────────────────────────────────────────────
-- Comprimi chunks più vecchi di 7 giorni. Compressione columnar nativa
-- TimescaleDB → riduzione tipica 10-20x per OHLCV.
ALTER TABLE candles SET (
  timescaledb.compress = TRUE,
  timescaledb.compress_segmentby = 'ticker, timeframe',
  timescaledb.compress_orderby = 'candle_time DESC'
);

SELECT add_compression_policy('candles', INTERVAL '7 days');

-- ── 4C. Comprimi subito i chunks storici (eccetto ultimi 7 giorni) ────
-- Forza compressione retroattiva sui dati esistenti.
SELECT compress_chunk(c, if_not_compressed => TRUE)
FROM show_chunks('candles', older_than => INTERVAL '7 days') c;

-- ── 4D. Verifica risultato ────────────────────────────────────────────
SELECT
  hypertable_name,
  pg_size_pretty(before_compression_total_bytes) AS before,
  pg_size_pretty(after_compression_total_bytes) AS after,
  ROUND(100.0 * (1 - after_compression_total_bytes::numeric / NULLIF(before_compression_total_bytes,0)), 1) AS pct_saved
FROM hypertable_compression_stats('candles');
