import { useState, useEffect, useRef, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || '';

interface TickerSelectorProps {
  value: string;
  onChange: (ticker: string) => void;
}

export function TickerSelector({ value, onChange }: TickerSelectorProps) {
  const [search, setSearch] = useState(value);
  const [open, setOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch suggestions when search changes
  const fetchSuggestions = useCallback(async (q: string) => {
    if (q.length < 1) {
      setSuggestions([]);
      return;
    }
    try {
      const res = await fetch(`${API_URL}/api/tickers/all?q=${encodeURIComponent(q)}`);
      if (res.ok) {
        const data = await res.json();
        setSuggestions(data.tickers || []);
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => fetchSuggestions(search), 150);
    return () => clearTimeout(timeout);
  }, [search, fetchSuggestions]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '240px' }}>
      <input
        type="text"
        placeholder="Cerca ticker... (Invio per confermare)"
        value={search}
        onChange={e => {
          setSearch(e.target.value.toUpperCase());
          setOpen(true);
        }}
        onFocus={() => {
          setOpen(true);
          if (search.length >= 1) fetchSuggestions(search);
        }}
        onKeyDown={e => {
          if (e.key === 'Enter' && search.trim()) {
            onChange(search.trim());
            setOpen(false);
          }
        }}
        className="filter-input"
        style={{ width: '100%' }}
      />

      {open && suggestions.length > 0 && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            maxHeight: '300px',
            overflowY: 'auto',
            background: 'var(--bg-card)',
            borderRadius: '8px',
            boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
            zIndex: 50,
            marginTop: '4px',
          }}
        >
          {suggestions.map(t => (
            <button
              key={t}
              onClick={() => {
                onChange(t);
                setSearch(t);
                setOpen(false);
              }}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                width: '100%',
                padding: '0.5rem 0.75rem',
                border: 'none',
                background: t === value ? 'var(--neon-blue-dim)' : 'transparent',
                cursor: 'pointer',
                fontSize: '0.8125rem',
                textAlign: 'left',
                color: 'var(--text-primary)',
              }}
            >
              <span className="font-mono font-semibold">{t}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
