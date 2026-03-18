export interface Signal {
  id: number;
  scan_id?: number;
  ticker: string;
  timeframe: string;
  signal_type: 'RIALZISTA' | 'RIBASSISTA';
  close_price: number;
  prev_high: number;
  prev_low: number;
  breakout_pct: number;
  candle_time: string | null;
  near_sr: boolean;
  sr_level: number | null;
  sr_distance: number | null;
  atr_value: number | null;
  created_at: string;
}

export interface ScannerStatus {
  last_scan: {
    id: number;
    started_at: string | null;
    ended_at: string | null;
    total_stocks: number;
    signals_found: number;
    signals_filtered: number;
    errors: number;
  } | null;
  running: boolean;
  total_signals_today: number;
}

export interface ScannerStats {
  today: {
    total: number;
    bullish: number;
    bearish: number;
    near_sr: number;
  };
  week: number;
  month: number;
  by_type: { type: string; count: number }[];
  by_timeframe: { timeframe: string; count: number }[];
}

export interface TickerInfo {
  ticker: string;
  signal_count_7d: number;
}

export interface SRLevels {
  support: number[];
  resistance: number[];
}

export interface SignalFilters {
  page: number;
  page_size: number;
  ticker?: string;
  type?: 'RIALZISTA' | 'RIBASSISTA';
  timeframe?: '1h' | '4h';
  near_sr?: boolean;
  date_from?: string;
  date_to?: string;
  sort_by: string;
  sort_order: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
