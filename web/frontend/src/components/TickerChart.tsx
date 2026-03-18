import { useEffect, useRef } from 'react';
import { createChart, ColorType, CrosshairMode, type IChartApi, type ISeriesApi, type Time } from 'lightweight-charts';
import type { TickerChartData } from '../hooks/useApi';

interface TickerChartProps {
  ticker: string;
  chartData: TickerChartData | null;
  loading: boolean;
}

function safeRemoveSeries(chart: IChartApi | null, series: ISeriesApi<'Line'>) {
  if (!chart) return;
  try { chart.removeSeries(series); } catch { /* chart already destroyed */ }
}

export function TickerChart({ ticker, chartData, loading }: TickerChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const levelLinesRef = useRef<ISeriesApi<'Line'>[]>([]);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9e9890',
        fontFamily: "'Inter', sans-serif",
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: '#f0ebe2' },
        horzLines: { color: '#f0ebe2' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(107, 101, 96, 0.15)', labelBackgroundColor: '#ffffff' },
        horzLine: { color: 'rgba(107, 101, 96, 0.15)', labelBackgroundColor: '#ffffff' },
      },
      rightPriceScale: {
        borderColor: '#e5e0d5',
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
      timeScale: {
        borderColor: '#e5e0d5',
        timeVisible: true,
        secondsVisible: false,
      },
      watermark: { visible: false },
    });

    chartRef.current = chart;
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#6b9e8a',
      downColor: '#c47a6c',
      borderUpColor: '#6b9e8a',
      borderDownColor: '#c47a6c',
      wickUpColor: '#6b9e8a',
      wickDownColor: '#c47a6c',
    });
    candlestickSeriesRef.current = candlestickSeries;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    const ro = new ResizeObserver(handleResize);
    ro.observe(chartContainerRef.current);

    return () => {
      ro.disconnect();
      chartRef.current = null;
      candlestickSeriesRef.current = null;
      levelLinesRef.current = [];
      chart.remove();
    };
  }, []);

  // Update candle data and S/R levels
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current || !chartData) return;

    const chart = chartRef.current;
    const series = candlestickSeriesRef.current;

    // Set candle data
    if (chartData.candles.length > 0) {
      const data = chartData.candles.map(k => ({
        time: k.time as Time,
        open: k.open,
        high: k.high,
        low: k.low,
        close: k.close,
      }));
      series.setData(data);
      chart.timeScale().fitContent();
    }

    // Clear old S/R lines
    levelLinesRef.current.forEach(line => safeRemoveSeries(chart, line));
    levelLinesRef.current = [];

    // Draw S/R levels
    if (chartData.sr_levels.length > 0 && chartData.candles.length > 0) {
      const fromTime = chartData.candles[0].time;
      const toTime = chartData.candles[chartData.candles.length - 1].time;

      chartData.sr_levels.forEach((level, i) => {
        const isSupport = level.type === 'swing_low';
        const line = chart.addLineSeries({
          color: isSupport ? 'rgba(107, 158, 138, 0.4)' : 'rgba(196, 122, 108, 0.4)',
          lineWidth: 1,
          lineStyle: 2,
          title: i === 0 ? (isSupport ? 'S' : 'R') : undefined,
          lastValueVisible: true,
          priceLineVisible: false,
        });
        line.setData([
          { time: fromTime as Time, value: level.price },
          { time: toTime as Time, value: level.price },
        ]);
        levelLinesRef.current.push(line);
      });
    }
  }, [chartData]);

  const supportLevels = chartData?.sr_levels.filter(l => l.type === 'swing_low') ?? [];
  const resistanceLevels = chartData?.sr_levels.filter(l => l.type === 'swing_high') ?? [];

  return (
    <div
      className="card"
      style={{
        height: '100%',
        minHeight: '400px',
        display: 'flex',
        flexDirection: 'column',
        padding: 0,
        overflow: 'hidden',
      }}
    >
      {/* Chart header */}
      <div
        className="flex justify-between items-center px-5 py-3"
        style={{ borderBottom: '1px solid var(--border-color)' }}
      >
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            {ticker || 'Seleziona ticker'}
          </h3>
          <span className="badge badge-idle">4h</span>
          {loading && <span className="text-xs text-muted animate-pulse">Caricamento...</span>}
        </div>
      </div>

      {/* Chart container */}
      <div ref={chartContainerRef} style={{ flex: 1, width: '100%' }} />

      {/* Level values footer */}
      {(supportLevels.length > 0 || resistanceLevels.length > 0) && (
        <div
          className="flex gap-5 px-5 py-2 flex-wrap"
          style={{ borderTop: '1px solid var(--border-color)', fontSize: '0.6875rem' }}
        >
          {supportLevels.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-muted">Support:</span>
              <span className="font-mono" style={{ color: 'var(--neon-green)' }}>
                {supportLevels.map(l => l.price.toFixed(2)).join(' / ')}
              </span>
            </div>
          )}
          {resistanceLevels.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-muted">Resistance:</span>
              <span className="font-mono" style={{ color: 'var(--neon-red)' }}>
                {resistanceLevels.map(l => l.price.toFixed(2)).join(' / ')}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
