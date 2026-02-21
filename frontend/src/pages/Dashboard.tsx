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
          <p className="text-sm text-stat-blue-dark mb-1">Pending Clusters</p>
          <p className="financial-amount text-stat-blue-dark">{stats.pendingClusters}</p>
          <p className="text-xs text-stat-blue mt-2">Click to review →</p>
        </Link>

        <Link to="/tickets" className="stat-card-teal">
          <p className="text-sm text-stat-teal-dark mb-1">Open Tickets</p>
          <p className="financial-amount text-stat-teal-dark">{stats.openTickets}</p>
          <p className="text-xs text-stat-teal mt-2">View open tickets →</p>
        </Link>

        <Link to="/tickets" className="stat-card-emerald">
          <p className="text-sm text-stat-emerald-dark mb-1">Total Tickets</p>
          <p className="financial-amount text-stat-emerald-dark">{stats.totalTickets}</p>
          <p className="text-xs text-stat-emerald mt-2">Browse ticket list →</p>
        </Link>

        <Link to="/merges" className="stat-card-violet">
          <p className="text-sm text-stat-violet-dark mb-1">Merge Operations</p>
          <p className="financial-amount text-stat-violet-dark">{stats.totalMerges}</p>
          <p className="text-xs text-stat-violet mt-2">View merge history →</p>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Clusters */}
        <div className="card !p-0 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
            <h2 className="font-semibold text-gray-900">Recent Pending Clusters</h2>
            <Link to="/clusters" className="text-sm text-primary-600 hover:text-primary-700">
              View all →
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {recentClusters.length === 0 ? (
              <p className="p-6 text-center text-gray-500">No pending clusters</p>
            ) : (
              recentClusters.map(cluster => (
                <Link
                  key={cluster.id}
                  to={`/clusters?id=${cluster.id}`}
                  className="block p-4 hover:bg-gray-50"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium text-gray-900">{cluster.ticketCount} tickets</p>
                      <p className="text-sm text-gray-500 line-clamp-1">{cluster.summary}</p>
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
          <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
            <h2 className="font-semibold text-gray-900">Recent Merge Operations</h2>
            <Link to="/merges" className="text-sm text-primary-600 hover:text-primary-700">
              View all →
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {recentMerges.length === 0 ? (
              <p className="p-6 text-center text-gray-500">No merge operations yet</p>
            ) : (
              recentMerges.map(merge => (
                <Link
                  key={merge.id}
                  to="/merges"
                  className="block p-4 hover:bg-gray-50"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium text-gray-900">
                        {merge.secondaryTicketIds.length + 1} tickets merged
                      </p>
                      <p className="text-sm text-gray-500 line-clamp-1">Cluster {merge.clusterId}</p>
                    </div>
                    <div className="text-right">
                      <span className={`badge ${statusStyles[merge.status] || 'badge-neutral'}`}>
                        {merge.status}
                      </span>
                      <p className="text-sm text-gray-600 mt-1">
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
        <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
          <h2 className="font-semibold text-gray-900">Recent Tickets</h2>
          <Link to="/tickets" className="text-sm text-primary-600 hover:text-primary-700">
            View all →
          </Link>
        </div>
        <div className="overflow-x-auto">
          {recentTickets.length === 0 ? (
            <p className="p-6 text-center text-gray-500">No recent tickets</p>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="table-header">
                    Ticket #
                  </th>
                  <th className="table-header">
                    Summary
                  </th>
                  <th className="table-header">
                    Status
                  </th>
                  <th className="table-header">
                    Priority
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {recentTickets.map(ticket => (
                  <tr key={ticket.id} className="table-row-hover">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {ticket.ticketNumber}
                    </td>
                    <td className="max-w-xs truncate px-4 py-3 text-sm text-gray-700">
                      {ticket.summary}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`badge ${statusStyles[ticket.status] || 'badge-neutral'}`}
                      >
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
