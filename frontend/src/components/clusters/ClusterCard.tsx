/**
 * ClusterCard component.
 *
 * Display card for cluster summary in list views.
 */

import type { Cluster } from '../../types';
import { ConfidenceBadge } from '../shared/ConfidenceBadge';

export interface ClusterCardProps {
  cluster: Cluster;
  onClick?: (clusterId: string) => void;
  onDismiss?: (clusterId: string) => void;
}

const statusStyles: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  merged: 'bg-green-100 text-green-800',
  dismissed: 'bg-gray-100 text-gray-800',
  expired: 'bg-gray-100 text-gray-500',
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function ClusterCard({ cluster, onClick, onDismiss }: ClusterCardProps) {
  const handleClick = () => {
    if (onClick) {
      onClick(cluster.id);
    }
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDismiss) {
      onDismiss(cluster.id);
    }
  };

  // Extract matching signal summaries
  const matchingSummary: string[] = [];
  if (cluster.matching_signals) {
    if (cluster.matching_signals.exact_matches?.length) {
      matchingSummary.push(`${cluster.matching_signals.exact_matches.length} exact matches`);
    }
    if (cluster.matching_signals.field_matches?.length) {
      matchingSummary.push(`${cluster.matching_signals.field_matches.length} field matches`);
    }
    if (cluster.matching_signals.text_similarity) {
      matchingSummary.push(
        `${Math.round(cluster.matching_signals.text_similarity.score * 100)}% text similarity`
      );
    }
  }

  return (
    <div
      className={`rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md ${
        onClick ? 'cursor-pointer' : ''
      }`}
      onClick={onClick ? handleClick : undefined}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? e => e.key === 'Enter' && handleClick() : undefined}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold text-gray-900">{cluster.ticket_count} Tickets</h3>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${statusStyles[cluster.status] || 'bg-gray-100 text-gray-800'}`}
            >
              {cluster.status}
            </span>
          </div>

          <p className="mt-1 text-sm text-gray-600 line-clamp-2">{cluster.summary}</p>

          <div className="mt-2">
            <ConfidenceBadge level={cluster.confidence} size="sm" />
          </div>
        </div>

        {cluster.status === 'pending' && onDismiss && (
          <button
            className="rounded-md border border-gray-300 bg-white px-3 py-1 text-sm font-medium text-gray-700 hover:bg-gray-50"
            onClick={handleDismiss}
          >
            Dismiss
          </button>
        )}
      </div>

      {matchingSummary.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-gray-500">Matching Signals</p>
          <div className="mt-1 flex flex-wrap gap-1">
            {matchingSummary.map(signal => (
              <span key={signal} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                {signal}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
        <span>Created {formatDate(cluster.created_at)}</span>
        <span className="font-mono">{cluster.id.slice(0, 8)}...</span>
      </div>
    </div>
  );
}

export default ClusterCard;
