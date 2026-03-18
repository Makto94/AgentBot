import type { SignalFilters } from '../types';

interface FilterBarProps {
  filters: SignalFilters;
  onChange: (filters: SignalFilters) => void;
}

export function FilterBar({ filters, onChange }: FilterBarProps) {
  const update = (partial: Partial<SignalFilters>) => {
    onChange({ ...filters, ...partial, page: 1 });
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Ticker Search */}
      <div className="filter-group">
        <label className="filter-label">Ticker</label>
        <input
          type="text"
          placeholder="AAPL, ENI.MI..."
          value={filters.ticker || ''}
          onChange={e => update({ ticker: e.target.value || undefined })}
          className="filter-input"
          style={{ minWidth: '120px' }}
        />
      </div>

      {/* Signal Type */}
      <div className="filter-group">
        <label className="filter-label">Tipo</label>
        <select
          value={filters.type || ''}
          onChange={e => update({ type: (e.target.value || undefined) as SignalFilters['type'] })}
          className="filter-select"
        >
          <option value="">Tutti</option>
          <option value="RIALZISTA">Rialzista</option>
          <option value="RIBASSISTA">Ribassista</option>
        </select>
      </div>

      {/* Timeframe */}
      <div className="filter-group">
        <label className="filter-label">Timeframe</label>
        <select
          value={filters.timeframe || ''}
          onChange={e => update({ timeframe: (e.target.value || undefined) as SignalFilters['timeframe'] })}
          className="filter-select"
        >
          <option value="">Tutti</option>
          <option value="1h">1h</option>
          <option value="4h">4h</option>
        </select>
      </div>

      {/* Near S/R */}
      <div className="filter-group">
        <label className="filter-label">Near S/R</label>
        <select
          value={filters.near_sr === undefined ? '' : String(filters.near_sr)}
          onChange={e => {
            const val = e.target.value;
            update({ near_sr: val === '' ? undefined : val === 'true' });
          }}
          className="filter-select"
        >
          <option value="">Tutti</option>
          <option value="true">Si</option>
          <option value="false">No</option>
        </select>
      </div>

      {/* Date Range */}
      <div className="filter-group">
        <label className="filter-label">Da</label>
        <input
          type="date"
          value={filters.date_from || ''}
          onChange={e => update({ date_from: e.target.value || undefined })}
          className="filter-input"
        />
      </div>
      <div className="filter-group">
        <label className="filter-label">A</label>
        <input
          type="date"
          value={filters.date_to || ''}
          onChange={e => update({ date_to: e.target.value || undefined })}
          className="filter-input"
        />
      </div>

      {/* Sort */}
      <div className="filter-group">
        <label className="filter-label">Ordina</label>
        <select
          value={filters.sort_by}
          onChange={e => update({ sort_by: e.target.value })}
          className="filter-select"
        >
          <option value="created_at">Data</option>
          <option value="breakout_pct">Breakout %</option>
          <option value="ticker">Ticker</option>
        </select>
      </div>
      <div className="filter-group">
        <label className="filter-label">Ordine</label>
        <select
          value={filters.sort_order}
          onChange={e => update({ sort_order: e.target.value as 'asc' | 'desc' })}
          className="filter-select"
        >
          <option value="desc">Recenti</option>
          <option value="asc">Vecchi</option>
        </select>
      </div>

      {/* Page Size */}
      <div className="filter-group">
        <label className="filter-label">Per Pagina</label>
        <select
          value={filters.page_size}
          onChange={e => update({ page_size: Number(e.target.value) })}
          className="filter-select"
        >
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </div>
    </div>
  );
}
