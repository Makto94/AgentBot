import type { Signal } from '../types';

interface SignalsTableProps {
  signals: Signal[];
  compact?: boolean;
  onTickerClick?: (ticker: string) => void;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('it-IT', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function SignalsTable({ signals, compact = false, onTickerClick }: SignalsTableProps) {
  if (signals.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">~</div>
        <div>Nessun segnale</div>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table>
        <thead>
          <tr>
            <th>Candela</th>
            <th>Ticker</th>
            <th>TF</th>
            <th>Tipo</th>
            <th className={compact ? 'hidden' : ''}>Close</th>
            <th>Breakout %</th>
            {!compact && <th className="mobile-hide-md">S/R Level</th>}
            {!compact && <th className="mobile-hide-sm">ATR</th>}
          </tr>
        </thead>
        <tbody>
          {signals.map((s) => (
            <tr key={s.id}>
              <td className="font-mono text-xs text-muted whitespace-nowrap">
                {s.candle_time ? formatTime(s.candle_time) : '---'}
              </td>
              <td>
                <button
                  onClick={() => onTickerClick?.(s.ticker)}
                  className="font-mono font-semibold text-sm"
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--neon-blue)',
                    padding: 0,
                  }}
                >
                  {s.ticker}
                </button>
              </td>
              <td>
                <span className="badge badge-idle">{s.timeframe}</span>
              </td>
              <td>
                <span className={`badge ${s.signal_type === 'RIALZISTA' ? 'badge-long' : 'badge-short'}`}>
                  {s.signal_type === 'RIALZISTA' ? 'BULL' : 'BEAR'}
                </span>
              </td>
              <td className={`font-mono text-sm ${compact ? 'hidden' : ''}`}>
                {s.close_price.toFixed(2)}
              </td>
              <td>
                <span
                  className="font-mono font-semibold text-sm"
                  style={{
                    color: s.signal_type === 'RIALZISTA' ? 'var(--neon-green)' : 'var(--neon-red)',
                  }}
                >
                  {s.signal_type === 'RIALZISTA' ? '+' : '-'}{(s.breakout_pct * 100).toFixed(2)}%
                </span>
              </td>
              {!compact && (
                <td className="font-mono text-xs mobile-hide-md">
                  {s.sr_level ? (
                    <span>
                      {s.sr_level.toFixed(2)}
                      {s.near_sr && (
                        <span style={{ color: 'var(--neon-green)', marginLeft: '0.25rem' }}>*</span>
                      )}
                    </span>
                  ) : '---'}
                </td>
              )}
              {!compact && (
                <td className="font-mono text-xs text-muted mobile-hide-sm">
                  {s.atr_value ? s.atr_value.toFixed(4) : '---'}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
