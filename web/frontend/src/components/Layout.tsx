import { useState, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { ToastContainer } from './Toast';

export function Layout() {
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem('sidebar-collapsed') === 'true';
  });

  const toggleCollapsed = useCallback(() => {
    setCollapsed(prev => {
      const next = !prev;
      localStorage.setItem('sidebar-collapsed', String(next));
      return next;
    });
  }, []);

  const sidebarWidth = collapsed ? 64 : 240;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <Sidebar collapsed={collapsed} onToggleCollapse={toggleCollapsed} />
      <main
        className="layout-main"
        style={{ marginLeft: sidebarWidth, height: '100vh', overflowY: 'auto' }}
      >
        <div className="px-5" style={{ paddingTop: '1.75rem', paddingBottom: '1.25rem' }}>
          <div className="flex flex-col gap-5 page-enter" style={{ maxWidth: '1600px', margin: '0 auto' }}>
            <Outlet />
          </div>
        </div>
      </main>
      <ToastContainer />
    </div>
  );
}
