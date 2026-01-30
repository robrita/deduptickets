/**
 * Service for spike alert API operations.
 */

import { api } from './api';
import type { PaginatedResponse, SpikeAlert, SpikeDetail, SpikeFilters } from '../types';

/**
 * List spike alerts with optional filtering.
 */
export async function listSpikes(
  filters: SpikeFilters = {},
  page = 1,
  pageSize = 20
): Promise<PaginatedResponse<SpikeAlert>> {
  const params = new URLSearchParams();
  const offset = (page - 1) * pageSize;
  params.set('offset', offset.toString());
  params.set('limit', pageSize.toString());

  if (filters.status) params.set('status', filters.status);
  if (filters.severity) params.set('severity', filters.severity);
  if (filters.field_name) params.set('field_name', filters.field_name);
  if (filters.detected_after) params.set('detected_after', filters.detected_after);

  return api.get<PaginatedResponse<SpikeAlert>>(`/spikes?${params.toString()}`);
}

/**
 * Get spike alert details by ID.
 */
export async function getSpike(
  spikeId: string,
  region: string,
  month: string
): Promise<SpikeDetail> {
  const params = new URLSearchParams({ region, month });
  return api.get<SpikeDetail>(`/spikes/${spikeId}?${params.toString()}`);
}

/**
 * Get count of active spike alerts.
 */
export async function getActiveCount(region?: string, month?: string): Promise<number> {
  const params = new URLSearchParams();
  if (region) params.set('region', region);
  if (month) params.set('month', month);

  const queryString = params.toString();
  const url = queryString ? `/spikes/active/count?${queryString}` : '/spikes/active/count';

  const response = await api.get<{ active_count: number }>(url);
  return response.active_count;
}

/**
 * Acknowledge a spike alert.
 */
export async function acknowledgeSpike(
  spikeId: string,
  region: string,
  month: string,
  acknowledgedBy?: string
): Promise<SpikeAlert> {
  const params = new URLSearchParams({ region, month });
  return api.post<SpikeAlert>(`/spikes/${spikeId}/acknowledge?${params.toString()}`, {
    acknowledged_by: acknowledgedBy,
  });
}

/**
 * Resolve a spike alert.
 */
export async function resolveSpike(
  spikeId: string,
  region: string,
  month: string,
  resolutionNotes?: string,
  resolvedBy?: string
): Promise<SpikeAlert> {
  const params = new URLSearchParams({ region, month });
  return api.post<SpikeAlert>(`/spikes/${spikeId}/resolve?${params.toString()}`, {
    resolution_notes: resolutionNotes,
    resolved_by: resolvedBy,
  });
}
