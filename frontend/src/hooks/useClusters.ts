/**
 * useClusters hook.
 *
 * Provides cluster data fetching and mutations with React state management.
 * Could be upgraded to React Query for caching/revalidation.
 */

import { useCallback, useEffect, useState } from 'react';
import type { Cluster, ClusterDetail, ClusterFilters } from '../types';
import { clusterService } from '../services/clusterService';
import { mergeService } from '../services/mergeService';

export interface UseClustersResult {
  clusters: Cluster[];
  selectedCluster: ClusterDetail | null;
  pendingCount: number;
  isLoading: boolean;
  isLoadingDetail: boolean;
  error: Error | null;
  filters: ClusterFilters;
  setFilters: (filters: ClusterFilters) => void;
  selectCluster: (clusterId: string | null) => Promise<void>;
  dismissCluster: (clusterId: string, reason?: string) => Promise<void>;
  mergeCluster: (primaryTicketId: string) => Promise<void>;
  removeTicketFromCluster: (ticketId: string) => Promise<void>;
  refresh: () => Promise<void>;
}

export function useClusters(month?: string): UseClustersResult {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<ClusterDetail | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [filters, setFilters] = useState<ClusterFilters>({ month });

  const currentMonth = month || new Date().toISOString().slice(0, 7);

  const fetchClusters = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [listResponse, countResponse] = await Promise.all([
        clusterService.list({
          ...filters,
          month: currentMonth,
        }),
        clusterService.getPendingCount(currentMonth),
      ]);

      setClusters(listResponse.data);
      setPendingCount(countResponse.pendingCount);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load clusters'));
    } finally {
      setIsLoading(false);
    }
  }, [currentMonth, filters]);

  const selectCluster = useCallback(
    async (clusterId: string | null) => {
      if (!clusterId) {
        setSelectedCluster(null);
        return;
      }

      setIsLoadingDetail(true);
      try {
        const detail = await clusterService.get(clusterId, currentMonth);
        setSelectedCluster(detail);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to load cluster'));
      } finally {
        setIsLoadingDetail(false);
      }
    },
    [currentMonth]
  );

  const dismissCluster = useCallback(
    async (clusterId: string, reason?: string) => {
      try {
        await clusterService.dismiss(clusterId, { reason }, currentMonth);
        await fetchClusters();
        if (selectedCluster?.id === clusterId) {
          setSelectedCluster(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to dismiss cluster'));
        throw err;
      }
    },
    [currentMonth, fetchClusters, selectedCluster?.id]
  );

  const mergeCluster = useCallback(
    async (primaryTicketId: string) => {
      if (!selectedCluster) return;

      try {
        await mergeService.createMerge(
          {
            clusterId: selectedCluster.id,
            primaryTicketId: primaryTicketId,
            mergeBehavior: 'keep_latest',
          },
          currentMonth
        );
        await fetchClusters();
        setSelectedCluster(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to merge cluster'));
        throw err;
      }
    },
    [selectedCluster, currentMonth, fetchClusters]
  );

  const removeTicketFromCluster = useCallback(
    async (ticketId: string) => {
      if (!selectedCluster) return;

      try {
        const updated = await clusterService.removeMember(
          selectedCluster.id,
          ticketId,
          currentMonth
        );

        // Refresh the cluster detail
        if (updated.status === 'dismissed') {
          setSelectedCluster(null);
          await fetchClusters();
        } else {
          await selectCluster(selectedCluster.id);
        }
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to remove ticket'));
        throw err;
      }
    },
    [selectedCluster, currentMonth, fetchClusters, selectCluster]
  );

  const refresh = useCallback(async () => {
    await fetchClusters();
  }, [fetchClusters]);

  // Sync month from parent when prop changes
  useEffect(() => {
    setFilters(prev => {
      if (prev.month === currentMonth) return prev;
      return { ...prev, month: currentMonth };
    });
  }, [currentMonth]);

  // Initial load
  useEffect(() => {
    fetchClusters();
  }, [fetchClusters]);

  return {
    clusters,
    selectedCluster,
    pendingCount,
    isLoading,
    isLoadingDetail,
    error,
    filters,
    setFilters,
    selectCluster,
    dismissCluster,
    mergeCluster,
    removeTicketFromCluster,
    refresh,
  };
}

export default useClusters;
