/**
 * TopDrivers component displays ranked list of top issue drivers.
 */

import type { Driver } from '../../types';

interface TopDriversProps {
  drivers: Driver[];
  totalClusters: number;
  title?: string;
  onDriverClick?: (driver: Driver) => void;
}

function formatGrowth(growth: number): string {
  const sign = growth >= 0 ? '+' : '';
  return `${sign}${growth.toFixed(1)}%`;
}

function getGrowthColor(growth: number): string {
  if (growth > 50) return 'text-red-600';
  if (growth > 20) return 'text-orange-600';
  if (growth > 0) return 'text-yellow-600';
  if (growth < 0) return 'text-green-600';
  return 'text-gray-600';
}

function getRankBadge(rank: number): string {
  if (rank === 1) return 'bg-yellow-400 text-yellow-900';
  if (rank === 2) return 'bg-gray-300 text-gray-900';
  if (rank === 3) return 'bg-orange-300 text-orange-900';
  return 'bg-gray-100 text-gray-600';
}

export function TopDrivers({
  drivers,
  totalClusters,
  title = 'Top Drivers',
  onDriverClick,
}: TopDriversProps) {
  if (drivers.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <p className="text-gray-500 text-center py-4">No driver data available</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          <span className="text-sm text-gray-500">{totalClusters} total clusters</span>
        </div>
      </div>

      <div className="divide-y divide-gray-100">
        {drivers.map((driver, index) => {
          const rank = index + 1;
          const percentage =
            totalClusters > 0 ? ((driver.cluster_count / totalClusters) * 100).toFixed(1) : '0';

          return (
            <div
              key={driver.id}
              className={`px-6 py-4 flex items-center gap-4 ${
                onDriverClick ? 'hover:bg-gray-50 cursor-pointer' : ''
              }`}
              onClick={() => onDriverClick?.(driver)}
            >
              {/* Rank Badge */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${getRankBadge(
                  rank
                )}`}
              >
                {rank}
              </div>

              {/* Driver Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="font-medium text-gray-900 truncate">
                    {driver.field_value || driver.theme_summary}
                  </h4>
                  {driver.field_name && (
                    <span className="text-xs text-gray-400">({driver.field_name})</span>
                  )}
                </div>
                <p className="text-sm text-gray-500">
                  {driver.ticket_count} tickets •{' '}
                  {(
                    driver.avg_tickets_per_cluster ??
                    driver.ticket_count / Math.max(driver.cluster_count, 1)
                  ).toFixed(1)}{' '}
                  per cluster
                </p>
              </div>

              {/* Stats */}
              <div className="flex items-center gap-6">
                <div className="text-right">
                  <p className="text-lg font-bold text-gray-900">{driver.cluster_count}</p>
                  <p className="text-xs text-gray-500">clusters</p>
                </div>

                <div className="text-right w-16">
                  <p className="text-sm font-medium text-gray-600">{percentage}%</p>
                  <p className="text-xs text-gray-400">of total</p>
                </div>

                <div className="text-right w-20">
                  {driver.week_over_week_growth !== undefined ? (
                    <>
                      <p
                        className={`text-sm font-medium ${getGrowthColor(
                          driver.week_over_week_growth
                        )}`}
                      >
                        {formatGrowth(driver.week_over_week_growth)}
                      </p>
                      <p className="text-xs text-gray-400">WoW</p>
                    </>
                  ) : (
                    <p className="text-sm text-gray-400">-</p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default TopDrivers;
