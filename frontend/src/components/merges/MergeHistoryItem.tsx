/**
 * MergeHistoryItem component.
 *
 * Displays a single merge operation in the history list with revert button.
 */

import React from 'react';
import type { MergeOperation } from '../../types';

interface MergeHistoryItemProps {
  merge: MergeOperation;
  onRevert?: (merge: MergeOperation) => void;
  onViewDetails?: (merge: MergeOperation) => void;
}

export const MergeHistoryItem: React.FC<MergeHistoryItemProps> = ({
  merge,
  onRevert,
  onViewDetails,
}) => {
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const formatRelativeTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  const isRevertable = () => {
    if (merge.status !== 'completed') return false;
    if (!merge.revert_deadline) return true;
    return new Date(merge.revert_deadline) > new Date();
  };

  const getTimeUntilDeadline = () => {
    if (!merge.revert_deadline) return '';
    const deadline = new Date(merge.revert_deadline);
    const now = new Date();
    const diffMs = deadline.getTime() - now.getTime();
    if (diffMs <= 0) return 'Expired';
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    if (diffHours > 24) {
      const days = Math.floor(diffHours / 24);
      return `${days}d ${diffHours % 24}h remaining`;
    }
    return `${diffHours}h ${diffMins}m remaining`;
  };

  const statusStyles: Record<string, string> = {
    completed: 'bg-green-100 text-green-800',
    reverted: 'bg-gray-100 text-gray-800',
  };

  const statusLabels: Record<string, string> = {
    completed: 'Merged',
    reverted: 'Reverted',
  };

  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between">
        {/* Left side: merge info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                statusStyles[merge.status] || statusStyles.pending
              }`}
            >
              {statusLabels[merge.status] || merge.status}
            </span>
            <span className="text-sm text-gray-500">{formatRelativeTime(merge.performed_at)}</span>
          </div>

          <div className="mt-2">
            <p className="text-sm text-gray-900">
              <span className="font-medium">{merge.performed_by}</span> merged{' '}
              <span className="font-medium">{merge.secondary_ticket_ids.length} tickets</span>
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Primary ticket: {merge.primary_ticket_id.slice(0, 8)}...
            </p>
          </div>

          {/* Reverted info */}
          {merge.status === 'reverted' && merge.reverted_by && (
            <div className="mt-2 text-xs text-gray-500">
              <p>
                Reverted by {merge.reverted_by}
                {merge.reverted_at && ` on ${formatDate(merge.reverted_at)}`}
              </p>
              {merge.revert_reason && <p className="mt-1 italic">Reason: {merge.revert_reason}</p>}
            </div>
          )}

          {/* Revert deadline */}
          {merge.status === 'completed' && merge.revert_deadline && (
            <div className="mt-2">
              <p className={`text-xs ${isRevertable() ? 'text-gray-500' : 'text-red-600'}`}>
                {isRevertable() ? (
                  <>
                    <svg
                      className="inline-block w-3 h-3 mr-1"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    {getTimeUntilDeadline()}
                  </>
                ) : (
                  <>Revert window expired</>
                )}
              </p>
            </div>
          )}
        </div>

        {/* Right side: actions */}
        <div className="flex items-center gap-2 ml-4">
          {onViewDetails && (
            <button
              onClick={() => onViewDetails(merge)}
              className="text-sm text-indigo-600 hover:text-indigo-800"
            >
              View
            </button>
          )}
          {onRevert && isRevertable() && (
            <button
              onClick={() => onRevert(merge)}
              className="inline-flex items-center px-3 py-1.5 border border-amber-300 text-xs font-medium rounded-md text-amber-700 bg-amber-50 hover:bg-amber-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-amber-500"
            >
              <svg
                className="w-3.5 h-3.5 mr-1"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
                />
              </svg>
              Revert
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
