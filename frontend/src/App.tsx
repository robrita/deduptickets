import { useState } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { ClustersPage } from './pages/ClustersPage';
import { MergesPage } from './pages/MergesPage';
import { MergeDetailPage } from './pages/MergeDetailPage';
import { TicketsPage } from './pages/TicketsPage';
import { MonthSelector } from './components/shared/MonthSelector';

const navItems = [
  {
    path: '/',
    label: 'Dashboard',
    icon: (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 13h8V3H3zM13 21h8v-6h-8zM13 11h8V3h-8zM3 21h8v-6H3z" />
      </svg>
    ),
  },
  {
    path: '/tickets',
    label: 'Tickets',
    icon: (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M4 6h16M4 12h16M4 18h10" />
      </svg>
    ),
  },
  {
    path: '/clusters',
    label: 'Clusters',
    icon: (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="7" cy="7" r="3" />
        <circle cx="17" cy="7" r="3" />
        <circle cx="12" cy="16" r="3" />
      </svg>
    ),
  },
  {
    path: '/merges',
    label: 'Merges',
    icon: (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M8 7h8M8 17h8" />
        <path d="m6 9 2-2 2 2M18 15l-2 2-2-2" />
      </svg>
    ),
  },
];

function App() {
  const location = useLocation();
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));

  const isNavItemActive = (path: string): boolean => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  return (
    <div className="min-h-screen">
      <header className="bg-gradient-to-r from-primary-600 to-primary-700 shadow-lg">
        <div className="mx-auto max-w-7xl px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <img
                src="https://vcmthecelebritysource.com/wp-content/uploads/2024/10/Gcash-logo.jpg"
                alt="GCash logo"
                className="h-9 w-9 rounded-lg bg-white p-0.5 shadow-sm"
              />
              <h1 className="text-xl font-bold tracking-tight text-white">DedupTickets</h1>
            </div>
            <div className="flex items-center gap-3 md:gap-6">
              <MonthSelector value={month} onChange={setMonth} />
              <nav className="hidden gap-1 md:flex" aria-label="Primary navigation">
                {navItems.map(item => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={
                      isNavItemActive(item.path) ? 'nav-link-active' : 'nav-link'
                    }
                  >
                    {item.icon}
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        </div>
      </header>
      <main className="pb-20 md:pb-0">
        <Routes>
          <Route path="/" element={<Dashboard month={month} />} />
          <Route path="/tickets" element={<TicketsPage month={month} />} />
          <Route path="/clusters" element={<ClustersPage month={month} />} />
          <Route path="/merges" element={<MergesPage month={month} />} />
          <Route path="/merges/:mergeId" element={<MergeDetailPage month={month} />} />
        </Routes>
      </main>

      <nav className="bottom-nav" aria-label="Mobile primary navigation">
        <div className="bottom-nav-list">
          {navItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={`bottom-nav-item ${isNavItemActive(item.path) ? 'bottom-nav-item-active' : ''}`}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
}

export default App;
