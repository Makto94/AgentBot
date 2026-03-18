import { useParams, useNavigate } from 'react-router-dom';
import { useTickerSignals, useTickerChart } from '../hooks/useApi';
import { TickerChart } from '../components/TickerChart';
import { TickerSelector } from '../components/TickerSelector';
import { SignalsTable } from '../components/SignalsTable';

export function TickerPage() {
  const { ticker = '' } = useParams<{ ticker: string }>();
  const navigate = useNavigate();

  const handleTickerChange = (t: string) => {
    navigate(`/ticker/${t}`);
  };

  const { signals } = useTickerSignals(ticker);
  const { data: chartData, loading: chartLoading } = useTickerChart(ticker);

  return (
    <>
      <div className="flex justify-between items-center flex-wrap gap-3">
        <h2 className="text-xl font-semibold">
          {ticker ? `${ticker} - Analisi` : 'Ticker Chart'}
        </h2>
        <TickerSelector value={ticker} onChange={handleTickerChange} />
      </div>

      {ticker ? (
        <>
          <div style={{ height: '500px' }}>
            <TickerChart ticker={ticker} chartData={chartData} loading={chartLoading} />
          </div>

          <div className="card">
            <h3 className="text-sm font-semibold mb-3">
              Storico Segnali - {ticker}
            </h3>
            <SignalsTable signals={signals} />
          </div>
        </>
      ) : (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">~</div>
            <div>Seleziona un ticker per visualizzare chart e segnali</div>
          </div>
        </div>
      )}
    </>
  );
}
