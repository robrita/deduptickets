/**
 * Utility functions for trend components.
 */

import type { Driver } from '../../types';

/**
 * Utility to convert Driver array to chart data.
 */
export function driversToChartData(
  drivers: Driver[],
  valueKey: 'cluster_count' | 'ticket_count' = 'cluster_count'
): { label: string; value: number; growth: number }[] {
  return drivers.map((d) => ({
    label: d.field_value || d.theme_summary,
    value: d[valueKey],
    growth: d.week_over_week_growth ?? 0,
  }));
}
