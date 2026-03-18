import type { ScannerStats, ScannerStatus } from '../types';

interface StatsPanelProps {
  stats: ScannerStats | null;
  status: ScannerStatus | null;
}

export function StatsPanel({ stats, status }: StatsPanelProps) {
  const lastScanTime = status?.running
    ? 'In corso...'
    : status?.last_scan?.ended_at
      ? new Date(status.last_scan.ended_at).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
      : '---';

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 stagger-children">
      <div className="stat-card accent-blue">
        <div className="text-xs text-muted mb-2" style={{ letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          Segnali Oggi
        </div>
        <div className="font-mono font-bold" style={{ fontSize: '1.5rem' }}>
          {stats?.today?.near_sr ?? 0}
        </div>
        <div className="text-xs text-muted mt-1">
          {stats?.today?.total ?? 0} totali
        </div>
      </div>

      <div className="stat-card accent-green">
        <div className="text-xs text-muted mb-2" style={{ letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          Rialzisti
        </div>
        <div className="font-mono font-bold" style={{ fontSize: '1.5rem', color: 'var(--neon-green)' }}>
          {stats?.today?.bullish ?? 0}
        </div>
      </div>

      <div className="stat-card accent-red">
        <div className="text-xs text-muted mb-2" style={{ letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          Ribassisti
        </div>
        <div className="font-mono font-bold" style={{ fontSize: '1.5rem', color: 'var(--neon-red)' }}>
          {stats?.today?.bearish ?? 0}
        </div>
      </div>

      <div className="stat-card accent-yellow">
        <div className="text-xs text-muted mb-2" style={{ letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          Ultimo Scan
        </div>
        <div className="font-mono font-bold" style={{ fontSize: '1.5rem' }}>
          {lastScanTime}
        </div>
        <div className="text-xs text-muted mt-1">
          {status?.last_scan ? `${status.last_scan.signals_filtered} filtrati` : ''}
        </div>
      </div>
    </div>
  );
}
