/**
 * SpikeDrilldown component shows detailed spike information with baseline stats
 * and resolution workflow.
 */

import { useState } from 'react';
import type { SpikeDetail, SeverityLevel } from '../../types';

interface SpikeDrilldownProps {
  spike: SpikeDetail;
  onAcknowledge?: (spikeId: string) => Promise<void>;
  onResolve?: (spikeId: string, notes?: string) => Promise<void>;
  onClose?: () => void;
}

const severityConfig: Record<SeverityLevel, { color: string; label: string }> = {
  low: { color: 'text-yellow-600', label: 'Low (150-200%)' },
  medium: { color: 'text-orange-600', label: 'Medium (200-300%)' },
  high: { color: 'text-red-600', label: 'High (300%+)' },
};

function formatDateTime(isoString?: string): string {
  if (!isoString) return 'N/A';
  return new Date(isoString).toLocaleString();
}

export function SpikeDrilldown({ spike, onAcknowledge, onResolve, onClose }: SpikeDrilldownProps) {
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const severity = severityConfig[spike.severity];

  const handleAcknowledge = async () => {
    if (!onAcknowledge) return;
    setIsLoading(true);
    setError(null);
    try {
      await onAcknowledge(spike.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to acknowledge spike');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!onResolve) return;
    setIsLoading(true);
    setError(null);
    try {
      await onResolve(spike.id, resolutionNotes || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resolve spike');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Spike Alert Details</h2>
          <p className="text-sm text-gray-500">
            {spike.field_name}: {spike.field_value}
          </p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        )}
      </div>

      <div className="p-6 space-y-6">
        {/* Status & Severity */}
        <div className="flex gap-4">
          <div className="flex-1 bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500 mb-1">Status</p>
            <span
              className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                spike.status === 'active'
                  ? 'bg-red-100 text-red-800'
                  : spike.status === 'acknowledged'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-green-100 text-green-800'
              }`}
            >
              {spike.status}
            </span>
          </div>
          <div className="flex-1 bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500 mb-1">Severity</p>
            <p className={`font-semibold ${severity.color}`}>{severity.label}</p>
          </div>
        </div>

        {/* Volume Stats */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Volume Statistics</h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-xs text-gray-500">Baseline Count</p>
              <p className="text-2xl font-bold text-gray-600">{spike.baseline_count}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Current Count</p>
              <p className="text-2xl font-bold text-gray-900">{spike.current_count}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Increase</p>
              <p className={`text-2xl font-bold ${severity.color}`}>
                +{spike.percentage_increase.toFixed(1)}%
              </p>
            </div>
          </div>
        </div>

        {/* Baseline Details */}
        {(spike.time_window_start || spike.time_window_end) && (
          <div className="bg-blue-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-blue-800 mb-3">Time Window</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-blue-600">Start</p>
                <p className="text-lg font-semibold text-blue-900">
                  {formatDateTime(spike.time_window_start)}
                </p>
              </div>
              <div>
                <p className="text-xs text-blue-600">End</p>
                <p className="text-lg font-semibold text-blue-900">
                  {formatDateTime(spike.time_window_end)}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Timeline */}
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Timeline</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Detected</span>
              <span className="font-medium">{formatDateTime(spike.detected_at)}</span>
            </div>
            {spike.acknowledged_at && (
              <div className="flex justify-between">
                <span className="text-gray-500">Acknowledged by {spike.acknowledged_by}</span>
                <span className="font-medium">{formatDateTime(spike.acknowledged_at)}</span>
              </div>
            )}
            {spike.resolved_at && (
              <div className="flex justify-between">
                <span className="text-gray-500">Resolved</span>
                <span className="font-medium">{formatDateTime(spike.resolved_at)}</span>
              </div>
            )}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Actions */}
        {spike.status !== 'resolved' && (
          <div className="border-t pt-4 space-y-4">
            {spike.status === 'active' && onAcknowledge && (
              <button
                onClick={handleAcknowledge}
                disabled={isLoading}
                className="w-full px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Processing...' : 'Acknowledge Spike'}
              </button>
            )}

            {onResolve && (
              <div className="space-y-2">
                <textarea
                  value={resolutionNotes}
                  onChange={e => setResolutionNotes(e.target.value)}
                  placeholder="Resolution notes (optional)..."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                />
                <button
                  onClick={handleResolve}
                  disabled={isLoading}
                  className="w-full px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? 'Processing...' : 'Resolve Spike'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default SpikeDrilldown;
