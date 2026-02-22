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
  compact?: boolean;
  selectedClusterId?: string | null;
  onClusterClick?: (clusterId: string) => void;
  onDismiss?: (clusterId: string) => void;
  onFilterChange?: (filters: ClusterListFilters) => void;
}

export interface ClusterListFilters {
  status?: ClusterStatus;
}

const statusOptions: { value: ClusterStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'merged', label: 'Merged' },
  { value: 'dismissed', label: 'Dismissed' },
];

export function ClusterList({
  clusters,
  isLoading = false,
  compact = false,
  selectedClusterId,
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="spinner" />
        <span className="ml-3 text-navy-600 dark:text-[var(--color-text-secondary)]">
          Loading clusters...
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-4 rounded-lg bg-navy-50 p-4 dark:bg-[var(--color-surface-alt)]">
        <div>
          <label
            htmlFor="status-filter"
            className="mb-1 block text-sm font-medium text-navy-700 dark:text-[var(--color-text-secondary)]"
          >
            Status
          </label>
          <select
            id="status-filter"
            className="rounded-md border border-navy-300 bg-white px-3 py-2 text-sm dark:border-[var(--color-border)] dark:bg-[var(--color-surface-card)] dark:text-[var(--color-text)]"
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
      </div>

      {/* Results count */}
      <p className="text-sm text-navy-600 dark:text-[var(--color-text-secondary)]">
        Showing {clusters.length} clusters
      </p>

      {/* Cluster grid */}
      {clusters.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-navy-300 py-12 text-center dark:border-[var(--color-border)]">
          <p className="text-navy-600 dark:text-[var(--color-text-secondary)]">No clusters found</p>
        </div>
      ) : (
        <div
          className={
            compact
              ? 'grid gap-4 md:grid-cols-1 xl:grid-cols-2'
              : 'grid gap-4 md:grid-cols-2 lg:grid-cols-3'
          }
        >
          {clusters.map(cluster => (
            <ClusterCard
              key={cluster.id}
              cluster={cluster}
              isSelected={selectedClusterId === cluster.id}
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
