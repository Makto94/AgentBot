import { useNavigate } from 'react-router-dom';
import { useScannerStatus, useScannerStats, useLatestSignals } from '../hooks/useApi';
import { StatsPanel } from '../components/StatsPanel';
import { SignalsTable } from '../components/SignalsTable';

export function DashboardPage() {
  const { status } = useScannerStatus();
  const { stats } = useScannerStats();
  const { signals } = useLatestSignals(20);
  const navigate = useNavigate();

  return (
    <>
      <StatsPanel stats={stats} status={status} />

      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold">Ultimi Segnali (Near S/R)</h3>
          <button
            onClick={() => navigate('/signals')}
            className="text-xs font-medium"
            style={{
              color: 'var(--neon-blue)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            Vedi tutti
          </button>
        </div>
        <SignalsTable
          signals={signals}
          compact
          onTickerClick={(t) => navigate(`/ticker/${t}`)}
        />
      </div>
    </>
  );
}
