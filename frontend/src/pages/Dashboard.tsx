/**
 * Dashboard component with summary widgets.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listClusters } from '../services/clusterService';
import { listSpikes, getActiveCount } from '../services/spikeService';
import { getTrendSummary } from '../services/trendService';
import type { Cluster, SpikeAlert } from '../types';

interface DashboardStats {
  pendingClusters: number;
  activeSpikes: number;
  productCount: number;
  avgDuplication: number;
}

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    pendingClusters: 0,
    activeSpikes: 0,
    productCount: 0,
    avgDuplication: 0,
  });
  const [recentClusters, setRecentClusters] = useState<Cluster[]>([]);
  const [activeAlerts, setActiveAlerts] = useState<SpikeAlert[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchDashboardData() {
      setIsLoading(true);
      try {
        const [clustersRes, spikesRes, activeCount, trendSummary] = await Promise.all([
          listClusters({ status: 'pending', page: 1, limit: 5 }),
          listSpikes({ status: 'active' }, 1, 5),
          getActiveCount(),
          getTrendSummary(),
        ]);

        setRecentClusters(clustersRes.data);
        setActiveAlerts(spikesRes.data);

        setStats({
          pendingClusters: clustersRes.meta.total,
          activeSpikes: activeCount,
          productCount: trendSummary.product_count,
          avgDuplication: 0, // Would need additional API call
        });
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchDashboardData();
  }, []);

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
          to="/spikes"
          className="bg-red-50 border border-red-200 rounded-lg p-6 hover:shadow-md transition-shadow"
        >
          <p className="text-sm text-red-600 mb-1">Active Spikes</p>
          <p className="text-4xl font-bold text-red-700">{stats.activeSpikes}</p>
          <p className="text-xs text-red-500 mt-2">Click to investigate →</p>
        </Link>

        <Link
          to="/trends"
          className="bg-purple-50 border border-purple-200 rounded-lg p-6 hover:shadow-md transition-shadow"
        >
          <p className="text-sm text-purple-600 mb-1">Products Tracked</p>
          <p className="text-4xl font-bold text-purple-700">{stats.productCount}</p>
          <p className="text-xs text-purple-500 mt-2">View trends →</p>
        </Link>

        <Link
          to="/audit"
          className="bg-gray-50 border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
        >
          <p className="text-sm text-gray-600 mb-1">Audit Trail</p>
          <p className="text-4xl font-bold text-gray-700">📋</p>
          <p className="text-xs text-gray-500 mt-2">View history →</p>
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
                      <p className="font-medium text-gray-900">{cluster.ticket_count} tickets</p>
                      <p className="text-sm text-gray-500 line-clamp-1">{cluster.summary}</p>
                    </div>
                    <div className="text-right">
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          cluster.confidence === 'high'
                            ? 'bg-green-100 text-green-800'
                            : cluster.confidence === 'medium'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {cluster.confidence}
                      </span>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>

        {/* Active Spike Alerts */}
        <div className="bg-white rounded-lg shadow-sm">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="font-semibold text-gray-900">Active Spike Alerts</h2>
            <Link to="/spikes" className="text-sm text-blue-600 hover:text-blue-800">
              View all →
            </Link>
          </div>
          <div className="divide-y divide-gray-100">
            {activeAlerts.length === 0 ? (
              <p className="p-6 text-center text-gray-500">No active alerts</p>
            ) : (
              activeAlerts.map(spike => (
                <Link
                  key={spike.id}
                  to={`/spikes?id=${spike.id}`}
                  className="block p-4 hover:bg-gray-50"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="font-medium text-gray-900">{spike.field_value}</p>
                      <p className="text-sm text-gray-500">{spike.field_name}</p>
                    </div>
                    <div className="text-right">
                      <span
                        className={`px-2 py-1 text-xs rounded-full ${
                          spike.severity === 'high'
                            ? 'bg-red-100 text-red-800'
                            : spike.severity === 'medium'
                              ? 'bg-orange-100 text-orange-800'
                              : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {spike.severity}
                      </span>
                      <p className="text-sm text-gray-600 mt-1">
                        +{spike.percentage_increase.toFixed(0)}%
                      </p>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
