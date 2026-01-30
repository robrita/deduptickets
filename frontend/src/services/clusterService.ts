/**
 * Cluster service for API interactions.
 *
 * Provides methods for listing, viewing, dismissing, and modifying clusters.
 */

import { api } from './api';
import type { Cluster, ClusterDetail, ClusterFilters, PaginatedResponse } from '../types';

export interface ClusterListParams extends ClusterFilters {
  page?: number;
  limit?: number;
}

export interface DismissClusterRequest {
  reason?: string;
}

export interface ClusterCountResponse {
  pending_count: number;
}

/**
 * List clusters with optional filtering.
 */
export async function listClusters(params: ClusterListParams): Promise<PaginatedResponse<Cluster>> {
  const { region = 'US', month, ...rest } = params;
  const currentMonth = month || new Date().toISOString().slice(0, 7);

  return api.get<PaginatedResponse<Cluster>>('/clusters', {
    params: {
      region,
      month: currentMonth,
      ...rest,
    },
  });
}

/**
 * Get cluster by ID with full ticket details.
 */
export async function getCluster(
  clusterId: string,
  region: string = 'US',
  month?: string
): Promise<ClusterDetail> {
  const currentMonth = month || new Date().toISOString().slice(0, 7);

  return api.get<ClusterDetail>(`/clusters/${clusterId}`, {
    params: { region, month: currentMonth },
  });
}

/**
 * Get pending cluster count.
 */
export async function getPendingCount(
  region?: string,
  month?: string
): Promise<ClusterCountResponse> {
  return api.get<ClusterCountResponse>('/clusters/pending/count', {
    params: { region, month },
  });
}

/**
 * Dismiss a cluster as not valid duplicates.
 */
export async function dismissCluster(
  clusterId: string,
  request: DismissClusterRequest,
  region: string = 'US',
  month?: string
): Promise<Cluster> {
  const currentMonth = month || new Date().toISOString().slice(0, 7);

  return api.post<Cluster>(`/clusters/${clusterId}/dismiss`, request, {
    params: { region, month: currentMonth },
  });
}

/**
 * Remove a ticket from a cluster.
 */
export async function removeClusterMember(
  clusterId: string,
  ticketId: string,
  region: string = 'US',
  month?: string
): Promise<Cluster> {
  const currentMonth = month || new Date().toISOString().slice(0, 7);

  return api.delete<Cluster>(`/clusters/${clusterId}/members/${ticketId}`, {
    params: { region, month: currentMonth },
  });
}

export const clusterService = {
  list: listClusters,
  get: getCluster,
  getPendingCount,
  dismiss: dismissCluster,
  removeMember: removeClusterMember,
};

export default clusterService;
