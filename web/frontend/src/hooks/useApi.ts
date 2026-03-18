import { useState, useEffect, useCallback } from 'react';
import type {
  Signal,
  ScannerStatus,
  ScannerStats,
  SignalFilters,
  PaginatedResponse,
  TickerInfo,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || '';

export function useScannerStatus() {
  const [status, setStatus] = useState<ScannerStatus | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/scanner/status`);
      if (res.ok) setStatus(await res.json());
    } catch (err) {
      console.error('Failed to fetch scanner status:', err);
    }
  }, []);

  useEffect(() => {
    void fetchStatus();
    const interval = setInterval(() => void fetchStatus(), 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return { status, refetch: fetchStatus };
}

export function useScannerStats() {
  const [stats, setStats] = useState<ScannerStats | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/scanner/stats`);
      if (res.ok) setStats(await res.json());
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, []);

  useEffect(() => {
    void fetchStats();
    const interval = setInterval(() => void fetchStats(), 30000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  return { stats, refetch: fetchStats };
}

export function useLatestSignals(limit = 20) {
  const [signals, setSignals] = useState<Signal[]>([]);

  const fetchSignals = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/signals/latest?limit=${limit}`);
      if (res.ok) {
        const data = await res.json();
        setSignals(data.signals || []);
      }
    } catch (err) {
      console.error('Failed to fetch latest signals:', err);
    }
  }, [limit]);

  useEffect(() => {
    void fetchSignals();
    const interval = setInterval(() => void fetchSignals(), 30000);
    return () => clearInterval(interval);
  }, [fetchSignals]);

  return { signals, refetch: fetchSignals };
}

export function useSignalsPaginated(filters: SignalFilters) {
  const [data, setData] = useState<PaginatedResponse<Signal>>({
    items: [],
    total: 0,
    page: 1,
    page_size: 25,
    total_pages: 0,
  });
  const [loading, setLoading] = useState(true);

  const fetchSignals = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('page', String(filters.page));
      params.set('page_size', String(filters.page_size));
      params.set('sort_by', filters.sort_by);
      params.set('sort_order', filters.sort_order);
      if (filters.ticker) params.set('ticker', filters.ticker);
      if (filters.type) params.set('type', filters.type);
      if (filters.timeframe) params.set('timeframe', filters.timeframe);
      if (filters.near_sr !== undefined) params.set('near_sr', String(filters.near_sr));
      if (filters.date_from) params.set('date_from', filters.date_from);
      if (filters.date_to) params.set('date_to', filters.date_to);

      const res = await fetch(`${API_URL}/api/signals?${params}`);
      if (res.ok) setData(await res.json());
    } catch (err) {
      console.error('Failed to fetch signals:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void fetchSignals();
  }, [fetchSignals]);

  return { data, loading, refetch: fetchSignals };
}

export function useTickers(search?: string) {
  const [tickers, setTickers] = useState<TickerInfo[]>([]);

  const fetchTickers = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/tickers`);
      if (res.ok) {
        const data = await res.json();
        let items: TickerInfo[] = data.tickers || [];
        if (search) {
          const q = search.toUpperCase();
          items = items.filter(t => t.ticker.toUpperCase().includes(q));
        }
        setTickers(items);
      }
    } catch (err) {
      console.error('Failed to fetch tickers:', err);
    }
  }, [search]);

  useEffect(() => {
    void fetchTickers();
  }, [fetchTickers]);

  return { tickers, refetch: fetchTickers };
}

export interface TickerChartData {
  candles: { time: number; open: number; high: number; low: number; close: number }[];
  sr_levels: { price: number; type: string }[];
}

export function useTickerChart(ticker: string) {
  const [data, setData] = useState<TickerChartData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchChart = useCallback(async () => {
    if (!ticker) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/ticker/${encodeURIComponent(ticker)}/chart`);
      if (res.ok) setData(await res.json());
    } catch (err) {
      console.error('Failed to fetch chart:', err);
    } finally {
      setLoading(false);
    }
  }, [ticker]);

  useEffect(() => {
    void fetchChart();
  }, [fetchChart]);

  return { data, loading, refetch: fetchChart };
}

export function useTickerSignals(ticker: string) {
  const [signals, setSignals] = useState<Signal[]>([]);

  const fetchSignals = useCallback(async () => {
    if (!ticker) return;
    try {
      const res = await fetch(`${API_URL}/api/ticker/${encodeURIComponent(ticker)}/signals`);
      if (res.ok) {
        const data = await res.json();
        setSignals(data.signals || []);
      }
    } catch (err) {
      console.error('Failed to fetch ticker signals:', err);
    }
  }, [ticker]);

  useEffect(() => {
    void fetchSignals();
  }, [fetchSignals]);

  return { signals, refetch: fetchSignals };
}
