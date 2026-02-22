import { Link, useLocation } from 'react-router-dom';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

interface SidebarProps {
  navItems: NavItem[];
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ navItems, collapsed, onToggle }: SidebarProps) {
  const location = useLocation();

  const isActive = (path: string): boolean => {
    if (path === '/') return location.pathname === '/';
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  return (
    <>
      {/* Mobile overlay backdrop */}
      {!collapsed && (
        <div
          className="fixed inset-0 z-30 bg-navy-950/50 md:hidden dark:bg-black/70"
          onClick={onToggle}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed top-0 left-0 z-40 flex h-full flex-col shadow-elevated transition-all duration-200
          bg-gradient-to-b from-primary-600 to-primary-700
          dark:bg-none dark:bg-navy-950 dark:border-r dark:border-[var(--color-border)]
          ${collapsed ? '-translate-x-full md:w-16 md:translate-x-0' : 'w-60 translate-x-0'}`}
      >
        {/* Sidebar header with logo */}
        <div className="flex h-16 items-center border-b border-white/10 justify-between px-5">
          {!collapsed && (
            <img
              src="https://vcmthecelebritysource.com/wp-content/uploads/2024/10/Gcash-logo.jpg"
              alt="GCash logo"
              className="h-9 w-9 flex-shrink-0 rounded-lg bg-white p-0.5 shadow-sm"
            />
          )}
          <button
            onClick={onToggle}
            className={`flex h-8 w-8 items-center justify-center rounded-lg text-white/70 transition-colors hover:bg-white/10 hover:text-white dark:text-white/70 dark:hover:bg-white/10 dark:hover:text-white ${collapsed ? 'hidden md:inline-flex mx-auto' : 'hidden md:inline-flex'}`}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              {collapsed ? (
                <>
                  <path d="M13 5l7 7-7 7" />
                  <path d="M6 5l7 7-7 7" />
                </>
              ) : (
                <>
                  <path d="M11 19l-7-7 7-7" />
                  <path d="M18 19l-7-7 7-7" />
                </>
              )}
            </svg>
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex-1 space-y-1 px-2 py-2" aria-label="Sidebar navigation">
          {navItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              onClick={() => {
                // Close sidebar on mobile after navigating
                if (window.innerWidth < 768) onToggle();
              }}
              title={collapsed ? item.label : undefined}
              className={isActive(item.path) ? 'sidebar-link-active' : 'sidebar-link'}
            >
              <span className="flex-shrink-0">{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* Placeholder login user */}
        <div className="border-t border-white/10 py-3 px-4">
          <div className={`flex items-center gap-3 ${collapsed ? 'justify-center' : ''}`}>
            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-white/20 text-sm font-medium text-white">
              A
            </div>
            {!collapsed && (
              <div className="text-sm">
                <p className="font-medium text-white">Admin User</p>
                <p className="text-xs text-white/60 dark:text-white/70">Support Operations</p>
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
