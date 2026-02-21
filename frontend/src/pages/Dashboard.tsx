/**
 * Dashboard component with summary widgets.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listClusters } from '../services/clusterService';
import { listMerges } from '../services/mergeService';
import { listTickets } from '../services/ticketService';
import type { Cluster, MergeOperation, Ticket } from '../types';

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
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-600">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Link
          to="/clusters"
          className="bg-blue-50 border border-blue-200 rounded-lg p-6 hover:shadow-md transition-shadow"
        >
          <p className="text-sm text-blue-600 mb-1">Pending Clusters</p>
          <p className="text-4xl font-bold text-blue-700">{stats.pendingClusters}</p>
          <p className="text-xs text-blue-500 mt-2">Click to review →</p>
        </Link>

        <Link
          to="/tickets"
          className="bg-green-50 border border-green-200 rounded-lg p-6 hover:shadow-md transition-shadow"
        >
          <p className="text-sm text-green-600 mb-1">Open Tickets</p>
          <p className="text-4xl font-bold text-green-700">{stats.openTickets}</p>
          <p className="text-xs text-green-500 mt-2">View open tickets →</p>
        </Link>

        <Link
          to="/tickets"
          className="bg-emerald-50 border border-emerald-200 rounded-lg p-6 hover:shadow-md transition-shadow"
        >
          <p className="text-sm text-emerald-600 mb-1">Total Tickets</p>
          <p className="text-4xl font-bold text-emerald-700">{stats.totalTickets}</p>
          <p className="text-xs text-emerald-500 mt-2">Browse ticket list →</p>
        </Link>

        <Link
          to="/merges"
          className="bg-purple-50 border border-purple-200 rounded-lg p-6 hover:shadow-md transition-shadow"
        >
          <p className="text-sm text-purple-600 mb-1">Merge Operations</p>
          <p className="text-4xl font-bold text-purple-700">{stats.totalMerges}</p>
          <p className="text-xs text-purple-500 mt-2">View merge history →</p>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Clusters */}
        <div className="bg-white rounded-lg shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="font-semibold text-gray-900">Recent Pending Clusters</h2>
            <Link to="/clusters" className="text-sm text-blue-600 hover:text-blue-800">
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
                      <span className="px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800">
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
        <div className="bg-white rounded-lg shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="font-semibold text-gray-900">Recent Merge Operations</h2>
            <Link to="/merges" className="text-sm text-blue-600 hover:text-blue-800">
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
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          merge.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
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
      <div className="mt-6 bg-white rounded-lg shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="font-semibold text-gray-900">Recent Tickets</h2>
          <Link to="/tickets" className="text-sm text-blue-600 hover:text-blue-800">
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
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Ticket #
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Summary
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    Priority
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {recentTickets.map(ticket => (
                  <tr key={ticket.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {ticket.ticketNumber}
                    </td>
                    <td className="max-w-xs truncate px-4 py-3 text-sm text-gray-700">
                      {ticket.summary}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-medium ${
                          ticket.status === 'open'
                            ? 'bg-blue-100 text-blue-800'
                            : ticket.status === 'in_progress'
                              ? 'bg-yellow-100 text-yellow-800'
                              : ticket.status === 'resolved'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {ticket.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {ticket.priority && (
                        <span
                          className={`rounded-full px-2 py-1 text-xs font-medium ${
                            ticket.priority === 'urgent'
                              ? 'bg-red-100 text-red-800'
                              : ticket.priority === 'high'
                                ? 'bg-orange-100 text-orange-800'
                                : ticket.priority === 'medium'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-gray-100 text-gray-800'
                          }`}
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
