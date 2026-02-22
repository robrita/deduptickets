import { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { ClustersPage } from './pages/ClustersPage';
import { MergesPage } from './pages/MergesPage';
import { MergeDetailPage } from './pages/MergeDetailPage';
import { TicketsPage } from './pages/TicketsPage';
import { MonthSelector } from './components/shared/MonthSelector';
import { ThemeToggle } from './components/shared/ThemeToggle';
import { Sidebar } from './components/shared/Sidebar';

const navItems = [
  {
    path: '/',
    label: 'Dashboard',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path d="M3 13h8V3H3zM13 21h8v-6h-8zM13 11h8V3h-8zM3 21h8v-6H3z" />
      </svg>
    ),
  },
  {
    path: '/tickets',
    label: 'Tickets',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path d="M4 6h16M4 12h16M4 18h10" />
      </svg>
    ),
  },
  {
    path: '/clusters',
    label: 'Clusters',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
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
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
      >
        <path d="M8 7h8M8 17h8" />
        <path d="m6 9 2-2 2 2M18 15l-2 2-2-2" />
      </svg>
    ),
  },
];

function App() {
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="min-h-screen">
      <Sidebar
        navItems={navItems}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(prev => !prev)}
      />

      <div className={`transition-all duration-200 ${sidebarCollapsed ? 'md:ml-16' : 'md:ml-60'}`}>
        <header className="flex h-16 items-center justify-between border-b px-6 border-[var(--color-border)] bg-[var(--color-surface-card)]">
          <div className="flex items-center gap-3">
            {/* Mobile hamburger */}
            <button
              onClick={() => setSidebarCollapsed(prev => !prev)}
              className="rounded-md p-1.5 text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-surface-alt)] hover:text-[var(--color-text)] md:hidden"
              aria-label="Toggle sidebar"
            >
              <svg
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-xl font-bold tracking-tight text-[var(--color-text)]">
              Ticket Deduplication Platform
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <MonthSelector value={month} onChange={setMonth} />
            <ThemeToggle />
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
    </div>
  );
}

export default App;
