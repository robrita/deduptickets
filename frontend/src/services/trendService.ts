/**
 * Service for trend analysis API operations.
 */

import { api } from './api';
import type {
  GrowingDriversResponse,
  DuplicatedDriversResponse,
  TopDriversResponse,
  TrendFilters,
} from '../types';

/**
 * Get top drivers ranked by cluster count.
 */
export async function getTopDrivers(filters: TrendFilters = {}): Promise<TopDriversResponse> {
  const params = new URLSearchParams();

  if (filters.region) params.set('region', filters.region);
  if (filters.field_name) params.set('field_name', filters.field_name);
  if (filters.days) params.set('days', filters.days.toString());
  if (filters.limit) params.set('limit', filters.limit.toString());

  const query = params.toString();
  const url = query ? `/trends/top-drivers?${query}` : '/trends/top-drivers';

  return api.get<TopDriversResponse>(url);
}

/**
 * Get fastest growing drivers by week-over-week growth.
 */
export async function getFastestGrowing(
  filters: TrendFilters = {},
  minClusters = 3
): Promise<GrowingDriversResponse> {
  const params = new URLSearchParams();

  if (filters.region) params.set('region', filters.region);
  if (filters.field_name) params.set('field_name', filters.field_name);
  if (filters.days) params.set('days', filters.days.toString());
  if (filters.limit) params.set('limit', filters.limit.toString());
  params.set('min_clusters', minClusters.toString());

  return api.get<GrowingDriversResponse>(`/trends/fastest-growing?${params.toString()}`);
}

/**
 * Get most duplicated drivers by tickets-per-cluster ratio.
 */
export async function getMostDuplicated(
  filters: TrendFilters = {},
  minClusters = 2
): Promise<DuplicatedDriversResponse> {
  const params = new URLSearchParams();

  if (filters.region) params.set('region', filters.region);
  if (filters.field_name) params.set('field_name', filters.field_name);
  if (filters.days) params.set('days', filters.days.toString());
  if (filters.limit) params.set('limit', filters.limit.toString());
  params.set('min_clusters', minClusters.toString());

  return api.get<DuplicatedDriversResponse>(`/trends/most-duplicated?${params.toString()}`);
}

/**
 * Get ticket volume trends for a product.
 */
export async function getVolumeTrends(
  product: string,
  days = 30
): Promise<{ product: string; data_points: { date: string; mean: number; std: number }[] }> {
  return api.get(`/trends/volume?product=${encodeURIComponent(product)}&days=${days}`);
}

/**
 * Get list of products with baseline data.
 */
export async function getProducts(): Promise<{ products: string[] }> {
  return api.get('/trends/products');
}

/**
 * Get current baseline for a product.
 */
export async function getBaseline(product: string): Promise<{
  product: string;
  region: string;
  date: string;
  mean_daily_count: number;
  std_deviation: number;
  rolling_window_days: number;
  spike_threshold_2std: number;
  spike_threshold_3std: number;
}> {
  return api.get(`/trends/baseline/${encodeURIComponent(product)}`);
}

/**
 * Get system-wide summary.
 */
export async function getTrendSummary(): Promise<{
  product_count: number;
  products: {
    product: string;
    mean_daily_count: number;
    std_deviation: number;
    last_updated: string;
  }[];
  generated_at: string;
}> {
  return api.get('/trends/summary');
}
