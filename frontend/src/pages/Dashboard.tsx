/**
 * Dashboard component with summary widgets.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listClusters } from '../services/clusterService';
import { listMerges } from '../services/mergeService';
import { listTickets } from '../services/ticketService';
import type { Cluster, MergeOperation, Ticket } from '../types';
import { statusStyles, priorityStyles } from '../theme/colors';

interface DashboardStats {
  pendingClusters: number;
  openTickets: number;
  totalTickets: number;
  totalMerges: number;
}

interface DashboardProps {
  month: string;
}

export function Dashboard({ month }: DashboardProps) {
  const [stats, setStats] = useState<DashboardStats>({
    pendingClusters: 0,
    openTickets: 0,
    totalTickets: 0,
    totalMerges: 0,
  });
  const [recentClusters, setRecentClusters] = useState<Cluster[]>([]);
  const [recentMerges, setRecentMerges] = useState<MergeOperation[]>([]);
  const [recentTickets, setRecentTickets] = useState<Ticket[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchDashboardData() {
      setIsLoading(true);
      try {
        const [clustersRes, ticketsRes, openTicketsRes, mergesRes] = await Promise.all([
          listClusters({ status: 'pending', page: 1, page_size: 5, month }),
          listTickets({ page: 1, page_size: 5, month }),
          listTickets({ status: 'open', page: 1, page_size: 1, month }),
          listMerges(month, 1, 5),
        ]);

        setRecentClusters(clustersRes.data);
        setRecentMerges(mergesRes.data);
        setRecentTickets(ticketsRes.data);

        setStats({
          pendingClusters: clustersRes.meta.total,
          openTickets: openTicketsRes.meta.total,
          totalTickets: ticketsRes.meta.total,
          totalMerges: mergesRes.meta.total,
        });
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchDashboardData();
  }, [month]);

  if (isLoading) {
    return (
      <div className="page-container">
        <div className="flex items-center justify-center py-12">
          <div className="spinner"></div>
          <span className="ml-3 helper-text">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="page-title mb-6">Dashboard</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Link to="/clusters" className="stat-card-blue">
          <p className="text-sm text-stat-blue-dark mb-1 dark:text-stat-blue-light">
            Pending Clusters
          </p>
          <p className="financial-amount text-stat-blue-dark dark:text-stat-blue-light">
            {stats.pendingClusters}
          </p>
          <p className="text-xs text-stat-blue mt-2 dark:text-stat-blue-light/70">
            Click to review →
          </p>
        </Link>

        <Link to="/tickets" className="stat-card-teal">
          <p className="text-sm text-stat-teal-dark mb-1 dark:text-stat-teal-light">Open Tickets</p>
          <p className="financial-amount text-stat-teal-dark dark:text-stat-teal-light">
            {stats.openTickets}
          </p>
          <p className="text-xs text-stat-teal mt-2 dark:text-stat-teal-light/70">
            View open tickets →
          </p>
        </Link>

        <Link to="/tickets" className="stat-card-emerald">
          <p className="text-sm text-stat-emerald-dark mb-1 dark:text-stat-emerald-light">
            Total Tickets
          </p>
          <p className="financial-amount text-stat-emerald-dark dark:text-stat-emerald-light">
            {stats.totalTickets}
          </p>
          <p className="text-xs text-stat-emerald mt-2 dark:text-stat-emerald-light/70">
            Browse ticket list →
          </p>
        </Link>

        <Link to="/merges" className="stat-card-violet">
          <p className="text-sm text-stat-violet-dark mb-1 dark:text-stat-violet-light">
            Merge Operations
          </p>
          <p className="financial-amount text-stat-violet-dark dark:text-stat-violet-light">
            {stats.totalMerges}
          </p>
          <p className="text-xs text-stat-violet mt-2 dark:text-stat-violet-light/70">
            View merge history →
          </p>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Clusters */}
        <div className="card !p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-navy-100 flex justify-between items-center dark:border-[var(--color-border-light)]">
            <h2 className="font-semibold text-navy-900 dark:text-[var(--color-text)]">
              Recent Pending Clusters
            </h2>
            <Link
              to="/clusters"
              className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
            >
              View all →
            </Link>
          </div>
          <div className="divide-y divide-navy-100 dark:divide-[var(--color-border-light)]">
            {recentClusters.length === 0 ? (
              <p className="p-6 text-center text-navy-600 dark:text-[var(--color-text-secondary)]">
                No pending clusters
              </p>
            ) : (
              recentClusters.map(cluster => (
                <Link
                  key={cluster.id}
                  to={`/clusters?id=${cluster.id}`}
                  className="block p-4 hover:bg-navy-50 dark:hover:bg-[var(--color-surface-alt)]"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                        {cluster.ticketCount} tickets
                      </p>
                      <p className="text-sm text-navy-600 line-clamp-1 dark:text-[var(--color-text-secondary)]">
                        {cluster.summary}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className={`badge ${statusStyles[cluster.status] || 'badge-neutral'}`}>
                        {cluster.status}
                      </span>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Recent Merge Operations */}
        <div className="card !p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-navy-100 flex justify-between items-center dark:border-[var(--color-border-light)]">
            <h2 className="font-semibold text-navy-900 dark:text-[var(--color-text)]">
              Recent Merge Operations
            </h2>
            <Link
              to="/merges"
              className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
            >
              View all →
            </Link>
          </div>
          <div className="divide-y divide-navy-100 dark:divide-[var(--color-border-light)]">
            {recentMerges.length === 0 ? (
              <p className="p-6 text-center text-navy-600 dark:text-[var(--color-text-secondary)]">
                No merge operations yet
              </p>
            ) : (
              recentMerges.map(merge => (
                <Link
                  key={merge.id}
                  to="/merges"
                  className="block p-4 hover:bg-navy-50 dark:hover:bg-[var(--color-surface-alt)]"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                        {merge.secondaryTicketIds.length + 1} tickets merged
                      </p>
                      <p className="text-sm text-navy-600 line-clamp-1 dark:text-[var(--color-text-secondary)]">
                        Cluster {merge.clusterId}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className={`badge ${statusStyles[merge.status] || 'badge-neutral'}`}>
                        {merge.status}
                      </span>
                      <p className="text-sm text-navy-600 mt-1 dark:text-[var(--color-text-secondary)]">
                        {new Date(merge.performedAt).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Recent Tickets */}
      <div className="mt-6 card !p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-navy-100 flex justify-between items-center dark:border-[var(--color-border-light)]">
          <h2 className="font-semibold text-navy-900 dark:text-[var(--color-text)]">
            Recent Tickets
          </h2>
          <Link
            to="/tickets"
            className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
          >
            View all →
          </Link>
        </div>
        <div className="overflow-x-auto">
          {recentTickets.length === 0 ? (
            <p className="p-6 text-center text-navy-600 dark:text-[var(--color-text-secondary)]">
              No recent tickets
            </p>
          ) : (
            <table className="min-w-full divide-y divide-navy-200 dark:divide-[var(--color-border)]">
              <thead className="bg-navy-50 dark:bg-[var(--color-surface-alt)]">
                <tr>
                  <th className="table-header">Ticket #</th>
                  <th className="table-header">Summary</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Priority</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-100 bg-white dark:divide-[var(--color-border-light)] dark:bg-[var(--color-surface-card)]">
                {recentTickets.map(ticket => (
                  <tr key={ticket.id} className="table-row-hover">
                    <td className="px-4 py-3 text-sm font-medium text-navy-900 dark:text-[var(--color-text)]">
                      {ticket.ticketNumber}
                    </td>
                    <td className="max-w-xs truncate px-4 py-3 text-sm text-navy-700 dark:text-[var(--color-text-secondary)]">
                      {ticket.summary}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`badge ${statusStyles[ticket.status] || 'badge-neutral'}`}>
                        {ticket.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {ticket.priority && (
                        <span
                          className={`badge ${priorityStyles[ticket.priority] || 'badge-neutral'}`}
                        >
                          {ticket.priority}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
