/**
 * SpikeAlertCard component displays a single spike alert with severity indicator.
 */

import type { SpikeAlert, SeverityLevel } from '../../types';

interface SpikeAlertCardProps {
  spike: SpikeAlert;
  onAcknowledge?: (spike: SpikeAlert) => void;
  onResolve?: (spike: SpikeAlert) => void;
  onViewDetails?: (spike: SpikeAlert) => void;
}

const severityConfig: Record<
  SeverityLevel,
  { label: string; bgColor: string; textColor: string; icon: string }
> = {
  low: {
    label: 'Low',
    bgColor: 'bg-yellow-100',
    textColor: 'text-yellow-800',
    icon: '⚠️',
  },
  medium: {
    label: 'Medium',
    bgColor: 'bg-orange-100',
    textColor: 'text-orange-800',
    icon: '🔶',
  },
  high: {
    label: 'High',
    bgColor: 'bg-red-100',
    textColor: 'text-red-800',
    icon: '🔴',
  },
};

const statusColors: Record<string, { bg: string; text: string }> = {
  active: { bg: 'bg-red-500', text: 'text-white' },
  acknowledged: { bg: 'bg-yellow-500', text: 'text-white' },
  resolved: { bg: 'bg-green-500', text: 'text-white' },
};

function formatDateTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
}

export function SpikeAlertCard({
  spike,
  onAcknowledge,
  onResolve,
  onViewDetails,
}: SpikeAlertCardProps) {
  const severity = severityConfig[spike.severity];
  const statusStyle = statusColors[spike.status] || statusColors.active;

  return (
    <div
      className={`border rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow ${severity.bgColor}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{severity.icon}</span>
          <div>
            <h3 className="font-semibold text-gray-900">{spike.field_value}</h3>
            <p className="text-sm text-gray-600">{spike.field_name}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span
            className={`px-2 py-1 text-xs font-medium rounded-full ${statusStyle.bg} ${statusStyle.text}`}
          >
            {spike.status}
          </span>
          <span
            className={`px-2 py-0.5 text-xs font-medium rounded ${severity.bgColor} ${severity.textColor}`}
          >
            {severity.label} Severity
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-3 text-center">
        <div>
          <p className="text-xs text-gray-500">Baseline</p>
          <p className="text-lg font-bold text-gray-700">{spike.baseline_count}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Current</p>
          <p className="text-lg font-bold text-gray-900">{spike.current_count}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Increase</p>
          <p
            className={`text-lg font-bold ${
              spike.percentage_increase >= 200
                ? 'text-red-600'
                : spike.percentage_increase >= 150
                  ? 'text-orange-600'
                  : 'text-yellow-600'
            }`}
          >
            {formatPercent(spike.percentage_increase)}
          </p>
        </div>
      </div>

      {/* Timeline */}
      <p className="text-xs text-gray-500 mb-3">Detected: {formatDateTime(spike.detected_at)}</p>

      {/* Actions */}
      <div className="flex gap-2 pt-2 border-t border-gray-200">
        {onViewDetails && (
          <button
            onClick={() => onViewDetails(spike)}
            className="flex-1 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
          >
            View Details
          </button>
        )}
        {spike.status === 'active' && onAcknowledge && (
          <button
            onClick={() => onAcknowledge(spike)}
            className="flex-1 px-3 py-1.5 text-sm bg-yellow-500 text-white rounded hover:bg-yellow-600 transition-colors"
          >
            Acknowledge
          </button>
        )}
        {spike.status !== 'resolved' && onResolve && (
          <button
            onClick={() => onResolve(spike)}
            className="flex-1 px-3 py-1.5 text-sm bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
          >
            Resolve
          </button>
        )}
      </div>
    </div>
  );
}

export default SpikeAlertCard;
