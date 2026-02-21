/**
 * ClusterCard component.
 *
 * Display card for cluster summary in list views.
 */

import type { Cluster } from '../../types';

export interface ClusterCardProps {
  cluster: Cluster;
  isSelected?: boolean;
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

export function ClusterCard({ cluster, isSelected = false, onClick, onDismiss }: ClusterCardProps) {
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

  return (
    <div
      className={`rounded-lg border bg-white p-4 shadow-sm transition-all hover:shadow-md ${
        isSelected ? 'border-blue-400 ring-2 ring-blue-100' : 'border-gray-200'
      } ${
        onClick ? 'cursor-pointer' : ''
      }`}
      onClick={onClick ? handleClick : undefined}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-pressed={onClick ? isSelected : undefined}
      onKeyDown={onClick ? e => e.key === 'Enter' && handleClick() : undefined}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-semibold text-gray-900">{cluster.ticketCount} Tickets</h3>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${statusStyles[cluster.status] || 'bg-gray-100 text-gray-800'}`}
            >
              {cluster.status}
            </span>
          </div>

          <p className="mt-1 text-sm text-gray-600 line-clamp-2">{cluster.summary}</p>
        </div>

        {cluster.status === 'pending' && onDismiss && (
          <button
            className="ml-auto shrink-0 self-start rounded-md border border-gray-300 bg-white px-3 py-1 text-sm font-medium text-gray-700 hover:bg-gray-50"
            onClick={handleDismiss}
          >
            Dismiss
          </button>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
        <span>Created {formatDate(cluster.createdAt)}</span>
        <span className="font-mono">{cluster.id.slice(0, 8)}...</span>
      </div>
    </div>
  );
}

export default ClusterCard;
