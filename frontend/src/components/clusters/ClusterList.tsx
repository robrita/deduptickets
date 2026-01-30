/**
 * ClusterList component.
 *
 * Displays list of clusters with filtering options.
 */

import { useState } from 'react';
import type { Cluster, ClusterStatus } from '../../types';
import { ClusterCard } from './ClusterCard';

export interface ClusterListProps {
  clusters: Cluster[];
  isLoading?: boolean;
  onClusterClick?: (clusterId: string) => void;
  onDismiss?: (clusterId: string) => void;
  onFilterChange?: (filters: ClusterListFilters) => void;
}

export interface ClusterListFilters {
  status?: ClusterStatus;
  minConfidence?: number;
}

const statusOptions: { value: ClusterStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'merged', label: 'Merged' },
  { value: 'dismissed', label: 'Dismissed' },
];

const confidenceOptions = [
  { value: undefined, label: 'All Confidence' },
  { value: 0.8, label: 'High (80%+)' },
  { value: 0.5, label: 'Medium+ (50%+)' },
  { value: 0.0, label: 'Any' },
];

export function ClusterList({
  clusters,
  isLoading = false,
  onClusterClick,
  onDismiss,
  onFilterChange,
}: ClusterListProps) {
  const [filters, setFilters] = useState<ClusterListFilters>({});

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const status = e.target.value as ClusterStatus | '';
    const newFilters = { ...filters, status: status || undefined };
    setFilters(newFilters);
    onFilterChange?.(newFilters);
  };

  const handleConfidenceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    const minConfidence = value ? parseFloat(value) : undefined;
    const newFilters = { ...filters, minConfidence };
    setFilters(newFilters);
    onFilterChange?.(newFilters);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
        <span className="ml-3 text-gray-600">Loading clusters...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 rounded-lg bg-gray-50 p-4">
        <div>
          <label htmlFor="status-filter" className="mb-1 block text-sm font-medium text-gray-700">
            Status
          </label>
          <select
            id="status-filter"
            className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
            value={filters.status || ''}
            onChange={handleStatusChange}
          >
            {statusOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="confidence-filter"
            className="mb-1 block text-sm font-medium text-gray-700"
          >
            Confidence
          </label>
          <select
            id="confidence-filter"
            className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
            value={filters.minConfidence ?? ''}
            onChange={handleConfidenceChange}
          >
            {confidenceOptions.map(option => (
              <option key={option.label} value={option.value ?? ''}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results count */}
      <p className="text-sm text-gray-600">Showing {clusters.length} clusters</p>

      {/* Cluster grid */}
      {clusters.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 py-12 text-center">
          <p className="text-gray-500">No clusters found</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {clusters.map(cluster => (
            <ClusterCard
              key={cluster.id}
              cluster={cluster}
              onClick={onClusterClick}
              onDismiss={onDismiss}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default ClusterList;
