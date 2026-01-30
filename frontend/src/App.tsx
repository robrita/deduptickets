import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { ClustersPage } from './pages/ClustersPage';
import { MergesPage } from './pages/MergesPage';
import { SpikesPage } from './pages/SpikesPage';
import { TrendsPage } from './pages/TrendsPage';
import { AuditPage } from './pages/AuditPage';

const navItems = [
  { path: '/', label: 'Dashboard' },
  { path: '/clusters', label: 'Clusters' },
  { path: '/merges', label: 'Merges' },
  { path: '/spikes', label: 'Spikes' },
  { path: '/trends', label: 'Trends' },
  { path: '/audit', label: 'Audit' },
];

function App() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold text-gray-900">DedupTickets</h1>
            <nav className="flex gap-1">
              {navItems.map(item => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    location.pathname === item.path
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
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/clusters" element={<ClustersPage />} />
          <Route path="/merges" element={<MergesPage />} />
          <Route path="/spikes" element={<SpikesPage />} />
          <Route path="/trends" element={<TrendsPage />} />
          <Route path="/audit" element={<AuditPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
