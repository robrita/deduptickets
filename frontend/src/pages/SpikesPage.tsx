/**
 * SpikesPage displays and manages spike alerts.
 */

import { useEffect, useState, useCallback } from 'react';
import type { SpikeAlert, SpikeDetail, SpikeFilters } from '../types';
import { listSpikes, getSpike, acknowledgeSpike, resolveSpike } from '../services/spikeService';
import { SpikeAlertCard } from '../components/spikes/SpikeAlertCard';
import { SpikeDrilldown } from '../components/spikes/SpikeDrilldown';

const REGIONS = ['US', 'EU', 'APAC'];

function getCurrentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

export function SpikesPage() {
  const [spikes, setSpikes] = useState<SpikeAlert[]>([]);
  const [selectedSpike, setSelectedSpike] = useState<SpikeDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filters, setFilters] = useState<SpikeFilters>({
    active_only: true,
    month: getCurrentMonth(),
  });

  const fetchSpikes = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await listSpikes(filters);
      setSpikes(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load spikes');
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchSpikes();
  }, [fetchSpikes]);

  const handleViewDetails = async (spike: SpikeAlert) => {
    try {
      const month = spike.detected_at.slice(0, 7); // Extract YYYY-MM
      const details = await getSpike(spike.id, spike.region || 'US', month);
      setSelectedSpike(details);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load spike details');
    }
  };

  const handleAcknowledge = async (spike: SpikeAlert) => {
    try {
      const month = spike.detected_at.slice(0, 7);
      await acknowledgeSpike(spike.id, spike.region || 'US', month);
      await fetchSpikes();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to acknowledge spike');
    }
  };

  const handleResolve = async (spike: SpikeAlert) => {
    const month = spike.detected_at.slice(0, 7);
    const details = await getSpike(spike.id, spike.region || 'US', month);
    setSelectedSpike(details);
  };

  const handleDrilldownAcknowledge = async (spikeId: string) => {
    if (!selectedSpike) return;
    const month = selectedSpike.detected_at.slice(0, 7);
    await acknowledgeSpike(spikeId, selectedSpike.region || 'US', month);
    await fetchSpikes();
    // Refresh the detail view
    const updated = await getSpike(spikeId, selectedSpike.region || 'US', month);
    setSelectedSpike(updated);
  };

  const handleDrilldownResolve = async (spikeId: string, notes?: string) => {
    if (!selectedSpike) return;
    const month = selectedSpike.detected_at.slice(0, 7);
    await resolveSpike(spikeId, selectedSpike.region || 'US', month, notes);
    await fetchSpikes();
    setSelectedSpike(null);
  };

  const handleFilterChange = (key: keyof SpikeFilters, value: string | boolean) => {
    setFilters(prev => ({
      ...prev,
      [key]: value === '' ? undefined : value,
    }));
  };

  const activeCount = spikes.filter(s => s.status === 'active').length;
  const acknowledgedCount = spikes.filter(s => s.status === 'acknowledged').length;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Spike Alerts</h1>
          <p className="text-gray-500">Monitor and manage ticket volume anomalies across regions</p>
        </div>

        {/* Stats Summary */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-600">Active Alerts</p>
            <p className="text-3xl font-bold text-red-700">{activeCount}</p>
          </div>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-600">Acknowledged</p>
            <p className="text-3xl font-bold text-yellow-700">{acknowledgedCount}</p>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-600">Total Shown</p>
            <p className="text-3xl font-bold text-gray-700">{spikes.length}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Region</label>
              <select
                value={filters.region || ''}
                onChange={e => handleFilterChange('region', e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Regions</option>
                {REGIONS.map(r => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Month</label>
              <input
                type="month"
                value={filters.month || ''}
                onChange={e => handleFilterChange('month', e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Product</label>
              <input
                type="text"
                value={filters.product || ''}
                onChange={e => handleFilterChange('product', e.target.value)}
                placeholder="Filter by product..."
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex items-center gap-2 self-end pb-2">
              <input
                type="checkbox"
                id="active-only"
                checked={filters.active_only ?? true}
                onChange={e => handleFilterChange('active_only', e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="active-only" className="text-sm text-gray-700">
                Active only
              </label>
            </div>

            <button
              onClick={fetchSpikes}
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

        {/* Loading State */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-gray-600">Loading spikes...</span>
          </div>
        ) : spikes.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg shadow-sm">
            <p className="text-xl text-gray-500">No spike alerts found</p>
            <p className="text-gray-400 mt-2">
              {filters.active_only
                ? 'Try unchecking "Active only" to see resolved alerts'
                : 'Adjust your filters or check back later'}
            </p>
          </div>
        ) : (
          /* Spike Cards Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {spikes.map(spike => (
              <SpikeAlertCard
                key={spike.id}
                spike={spike}
                onViewDetails={handleViewDetails}
                onAcknowledge={handleAcknowledge}
                onResolve={handleResolve}
              />
            ))}
          </div>
        )}
      </div>

      {/* Drilldown Modal */}
      {selectedSpike && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <SpikeDrilldown
            spike={selectedSpike}
            onAcknowledge={handleDrilldownAcknowledge}
            onResolve={handleDrilldownResolve}
            onClose={() => setSelectedSpike(null)}
          />
        </div>
      )}
    </div>
  );
}

export default SpikesPage;
