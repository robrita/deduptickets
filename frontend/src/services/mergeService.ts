/**
 * Merge service for API interactions.
 *
 * Provides methods for creating merges, viewing merge history, and reverting.
 */

import { api } from './api';
import type { MergeOperation, MergeRequest, PaginatedResponse, RevertConflict } from '../types';

export interface MergeListParams {
  month?: string;
  page?: number;
  limit?: number;
  revertible_only?: boolean;
}

export interface RevertRequest {
  reason?: string;
}

/**
 * Create a new merge operation.
 */
export async function createMerge(
  request: MergeRequest,
  month?: string
): Promise<MergeOperation> {
  const currentMonth = month || new Date().toISOString().slice(0, 7);

  return api.post<MergeOperation>('/merges', request, {
    params: { month: currentMonth },
  });
}

/**
 * List merge operations with optional filtering.
 */
export async function listMerges(
  month?: string,
  page: number = 1,
  limit: number = 20,
  revertible_only: boolean = false
): Promise<PaginatedResponse<MergeOperation>> {
  const currentMonth = month || new Date().toISOString().slice(0, 7);
  const offset = (page - 1) * limit;

  return api.get<PaginatedResponse<MergeOperation>>('/merges', {
    params: {
      month: currentMonth,
      offset,
      limit,
      revertible_only,
    },
  });
}

/**
 * Get merge operation by ID.
 */
export async function getMerge(
  mergeId: string,
  month?: string
): Promise<MergeOperation> {
  const currentMonth = month || new Date().toISOString().slice(0, 7);

  return api.get<MergeOperation>(`/merges/${mergeId}`, {
    params: { month: currentMonth },
  });
}

/**
 * Revert a merge operation.
 */
export async function revertMerge(
  mergeId: string,
  month?: string,
  reason?: string
): Promise<MergeOperation> {
  const currentMonth = month || new Date().toISOString().slice(0, 7);

  return api.post<MergeOperation>(
    `/merges/${mergeId}/revert`,
    { reason },
    {
      params: { month: currentMonth },
    }
  );
}

/**
 * Check for conflicts before reverting.
 */
export async function checkRevertConflicts(
  mergeId: string,
  month?: string
): Promise<RevertConflict[]> {
  const currentMonth = month || new Date().toISOString().slice(0, 7);

  return api.get<RevertConflict[]>(`/merges/${mergeId}/conflicts`, {
    params: { month: currentMonth },
  });
}

export const mergeService = {
  createMerge,
  listMerges,
  getMerge,
  revertMerge,
  checkRevertConflicts,
};

export default mergeService;
