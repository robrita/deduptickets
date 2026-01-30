/**
 * TrendsPage displays all trend analysis views.
 */

import { useEffect, useState, useCallback } from 'react';
import type { Driver, TrendFilters } from '../types';
import { getTopDrivers, getFastestGrowing, getMostDuplicated } from '../services/trendService';
import { TopDrivers } from '../components/trends/TopDrivers';
import { TrendChart } from '../components/trends/TrendChart';
import { driversToChartData } from '../components/trends/trendUtils';

const REGIONS = ['US', 'EU', 'APAC'];
const FIELD_OPTIONS = ['product', 'category', 'severity', 'source_system'];

type TabKey = 'top-drivers' | 'fastest-growing' | 'most-duplicated';

export function TrendsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('top-drivers');
  const [topDrivers, setTopDrivers] = useState<Driver[]>([]);
  const [fastestGrowing, setFastestGrowing] = useState<Driver[]>([]);
  const [mostDuplicated, setMostDuplicated] = useState<Driver[]>([]);
  const [totalClusters, setTotalClusters] = useState(0);
  const [avgDuplication, setAvgDuplication] = useState(0);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filters, setFilters] = useState<TrendFilters>({
    region: 'US',
    field_name: 'product',
    days: 7,
    limit: 10,
  });

  const fetchAllData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [topRes, growthRes, dupRes] = await Promise.all([
        getTopDrivers(filters),
        getFastestGrowing(filters, 3),
        getMostDuplicated(filters, 2),
      ]);

      setTopDrivers(topRes.drivers);
      setTotalClusters(topRes.total_clusters);

      setFastestGrowing(growthRes.drivers);

      setMostDuplicated(dupRes.drivers);
      setAvgDuplication(dupRes.avg_duplication_ratio);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trends');
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);

  const handleFilterChange = (key: keyof TrendFilters, value: string | number) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
    }));
  };

  const tabs: { key: TabKey; label: string; count: number }[] = [
    { key: 'top-drivers', label: 'Top Drivers', count: topDrivers.length },
    { key: 'fastest-growing', label: 'Fastest Growing', count: fastestGrowing.length },
    { key: 'most-duplicated', label: 'Most Duplicated', count: mostDuplicated.length },
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Trend Analysis</h1>
          <p className="text-gray-500">
            Identify top drivers, fastest growing issues, and duplication patterns
          </p>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-600">Total Clusters</p>
            <p className="text-3xl font-bold text-blue-700">{totalClusters}</p>
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <p className="text-sm text-purple-600">Fastest Growing</p>
            <p className="text-3xl font-bold text-purple-700">
              {fastestGrowing[0]?.field_value || fastestGrowing[0]?.theme_summary || '-'}
            </p>
            {fastestGrowing[0]?.week_over_week_growth !== undefined && (
              <p className="text-sm text-purple-500">
                +{fastestGrowing[0].week_over_week_growth.toFixed(1)}% WoW
              </p>
            )}
          </div>
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <p className="text-sm text-orange-600">Avg Duplication</p>
            <p className="text-3xl font-bold text-orange-700">{avgDuplication.toFixed(1)}x</p>
            <p className="text-sm text-orange-500">tickets per cluster</p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Region</label>
              <select
                value={filters.region || 'US'}
                onChange={e => handleFilterChange('region', e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                {REGIONS.map(r => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Group By</label>
              <select
                value={filters.field_name || 'product'}
                onChange={e => handleFilterChange('field_name', e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                {FIELD_OPTIONS.map(f => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Time Range</label>
              <select
                value={filters.days || 7}
                onChange={e => handleFilterChange('days', parseInt(e.target.value))}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
              </select>
            </div>

            <button
              onClick={fetchAllData}
              className="self-end px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
            <button onClick={() => setError(null)} className="ml-4 text-red-500 hover:text-red-700">
              Dismiss
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              {tabs.map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.key
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                  <span className="ml-2 text-xs bg-gray-100 px-2 py-0.5 rounded-full">
                    {tab.count}
                  </span>
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Loading State */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-gray-600">Loading trends...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Main Content based on active tab */}
            {activeTab === 'top-drivers' && (
              <>
                <TopDrivers
                  drivers={topDrivers}
                  totalClusters={totalClusters}
                  title="Top Drivers by Cluster Count"
                />
                <TrendChart
                  data={driversToChartData(topDrivers, 'cluster_count')}
                  title="Cluster Distribution"
                  valueLabel="Clusters"
                />
              </>
            )}

            {activeTab === 'fastest-growing' && (
              <>
                <TopDrivers
                  drivers={fastestGrowing}
                  totalClusters={totalClusters}
                  title="Fastest Growing Drivers"
                />
                <TrendChart
                  data={driversToChartData(fastestGrowing, 'cluster_count')}
                  title="Growth Comparison"
                  valueLabel="Week-over-Week Growth"
                />
              </>
            )}

            {activeTab === 'most-duplicated' && (
              <>
                <TopDrivers
                  drivers={mostDuplicated}
                  totalClusters={totalClusters}
                  title="Most Duplicated Drivers"
                />
                <TrendChart
                  data={driversToChartData(mostDuplicated, 'ticket_count')}
                  title="Duplication Ratio"
                  valueLabel="Tickets per Cluster"
                />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default TrendsPage;
