import { useState } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { ClustersPage } from './pages/ClustersPage';
import { MergesPage } from './pages/MergesPage';
import { MergeDetailPage } from './pages/MergeDetailPage';
import { TicketsPage } from './pages/TicketsPage';
import { MonthSelector } from './components/shared/MonthSelector';

const navItems = [
  { path: '/', label: 'Dashboard' },
  { path: '/tickets', label: 'Tickets' },
  { path: '/clusters', label: 'Clusters' },
  { path: '/merges', label: 'Merges' },
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
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold text-gray-900">DedupTickets</h1>
            <div className="flex items-center gap-4">
              <MonthSelector value={month} onChange={setMonth} />
              <nav className="flex gap-1">
                {navItems.map(item => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                      isNavItemActive(item.path)
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`}
                  >
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </div>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard month={month} />} />
          <Route path="/tickets" element={<TicketsPage month={month} />} />
          <Route path="/clusters" element={<ClustersPage month={month} />} />
          <Route path="/merges" element={<MergesPage month={month} />} />
          <Route path="/merges/:mergeId" element={<MergeDetailPage month={month} />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
