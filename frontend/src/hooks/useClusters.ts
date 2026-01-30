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

export function useClusters(region: string = 'US', month?: string): UseClustersResult {
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [selectedCluster, setSelectedCluster] = useState<ClusterDetail | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [filters, setFilters] = useState<ClusterFilters>({ region, month });

  const currentMonth = month || new Date().toISOString().slice(0, 7);

  const fetchClusters = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [listResponse, countResponse] = await Promise.all([
        clusterService.list({
          ...filters,
          region,
          month: currentMonth,
        }),
        clusterService.getPendingCount(region, currentMonth),
      ]);

      setClusters(listResponse.data);
      setPendingCount(countResponse.pending_count);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load clusters'));
    } finally {
      setIsLoading(false);
    }
  }, [region, currentMonth, filters]);

  const selectCluster = useCallback(
    async (clusterId: string | null) => {
      if (!clusterId) {
        setSelectedCluster(null);
        return;
      }

      setIsLoadingDetail(true);
      try {
        const detail = await clusterService.get(clusterId, region, currentMonth);
        setSelectedCluster(detail);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to load cluster'));
      } finally {
        setIsLoadingDetail(false);
      }
    },
    [region, currentMonth]
  );

  const dismissCluster = useCallback(
    async (clusterId: string, reason?: string) => {
      try {
        await clusterService.dismiss(clusterId, { reason }, region, currentMonth);
        await fetchClusters();
        if (selectedCluster?.id === clusterId) {
          setSelectedCluster(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to dismiss cluster'));
        throw err;
      }
    },
    [region, currentMonth, fetchClusters, selectedCluster?.id]
  );

  const mergeCluster = useCallback(
    async (primaryTicketId: string) => {
      if (!selectedCluster) return;

      try {
        await mergeService.createMerge(
          {
            cluster_id: selectedCluster.id,
            primary_ticket_id: primaryTicketId,
            merge_behavior: 'keep_latest',
          },
          region,
          currentMonth
        );
        await fetchClusters();
        setSelectedCluster(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to merge cluster'));
        throw err;
      }
    },
    [selectedCluster, region, currentMonth, fetchClusters]
  );

  const removeTicketFromCluster = useCallback(
    async (ticketId: string) => {
      if (!selectedCluster) return;

      try {
        const updated = await clusterService.removeMember(
          selectedCluster.id,
          ticketId,
          region,
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
    [selectedCluster, region, currentMonth, fetchClusters, selectCluster]
  );

  const refresh = useCallback(async () => {
    await fetchClusters();
  }, [fetchClusters]);

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
