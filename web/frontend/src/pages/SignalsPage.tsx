import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSignalsPaginated } from '../hooks/useApi';
import { SignalsTable } from '../components/SignalsTable';
import { FilterBar } from '../components/FilterBar';
import { Pagination } from '../components/Pagination';
import type { SignalFilters } from '../types';

export function SignalsPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<SignalFilters>({
    page: 1,
    page_size: 25,
    sort_by: 'created_at',
    sort_order: 'desc',
  });

  const { data, loading } = useSignalsPaginated(filters);

  return (
    <>
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">Segnali</h2>
        <span className="text-xs text-muted">{data.total} totali</span>
      </div>

      <div className="card">
        <FilterBar filters={filters} onChange={setFilters} />
      </div>

      <div className="card" style={{ position: 'relative' }}>
        {loading && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(255,255,255,0.6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
              borderRadius: '16px',
            }}
          >
            <span className="text-sm text-muted animate-pulse">Caricamento...</span>
          </div>
        )}
        <SignalsTable
          signals={data.items}
          onTickerClick={(t) => navigate(`/ticker/${t}`)}
        />
        {data.total_pages > 1 && (
          <div className="mt-4">
            <Pagination
              page={data.page}
              totalPages={data.total_pages}
              total={data.total}
              pageSize={data.page_size}
              onPageChange={(p) => setFilters(f => ({ ...f, page: p }))}
            />
          </div>
        )}
      </div>
    </>
  );
}
