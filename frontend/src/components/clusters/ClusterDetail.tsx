/**
 * ClusterDetail component.
 *
 * Full cluster view with member tickets and merge actions.
 */

import { useState } from 'react';
import type { ClusterDetail as ClusterDetailType } from '../../types';
import { MergeDialog } from './MergeDialog';

export interface ClusterDetailProps {
  cluster: ClusterDetailType;
  onMerge?: (primaryTicketId: string) => Promise<void>;
  onDismiss?: () => void;
  onRemoveTicket?: (ticketId: string) => void;
  onClose?: () => void;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function ClusterDetail({
  cluster,
  onMerge,
  onDismiss,
  onRemoveTicket,
  onClose,
}: ClusterDetailProps) {
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [showMergeDialog, setShowMergeDialog] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleTicketSelect = (ticketId: string) => {
    setSelectedTicketId(ticketId === selectedTicketId ? null : ticketId);
  };

  const handleMerge = async () => {
    if (!selectedTicketId || !onMerge) return;

    setIsProcessing(true);
    try {
      await onMerge(selectedTicketId);
      setShowMergeDialog(false);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDismiss = () => {
    if (onDismiss) onDismiss();
  };

  const handleRemoveTicket = (ticketId: string) => {
    if (onRemoveTicket) onRemoveTicket(ticketId);
  };

  const isPending = cluster.status === 'pending';

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-navy-200 bg-white px-6 py-4 dark:border-[var(--color-border)] dark:bg-[var(--color-surface-card)]">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-semibold text-navy-900 dark:text-[var(--color-text)]">
                Cluster Details
              </h2>
            </div>
            <p className="mt-1 text-sm text-navy-600 dark:text-[var(--color-text-secondary)]">
              {cluster.summary}
            </p>
            <p className="mt-1 text-sm text-navy-600 dark:text-[var(--color-text-secondary)]">
              {cluster.ticketCount} tickets • Created {formatDate(cluster.createdAt)}
            </p>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              className="rounded-md p-2 text-navy-600 hover:bg-navy-100 hover:text-navy-600 dark:text-[var(--color-text-secondary)] dark:hover:bg-navy-800"
            >
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Tickets */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-medium text-navy-900 dark:text-[var(--color-text)]">
            Member Tickets
          </h3>
          {isPending && (
            <p className="text-sm text-navy-600 dark:text-[var(--color-text-secondary)]">
              Select a ticket as the primary for merging
            </p>
          )}
        </div>

        <div className="space-y-3">
          {cluster.members.map(member => (
            <div key={member.ticketId} className="relative">
              <div
                className={`rounded-lg border p-3 transition-colors ${
                  member.ticketId === selectedTicketId
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                    : 'border-navy-200 bg-white hover:border-navy-300 dark:border-[var(--color-border)] dark:bg-[var(--color-surface-card)] dark:hover:border-[var(--color-border-light)]'
                } ${isPending ? 'cursor-pointer' : ''}`}
                onClick={isPending ? () => handleTicketSelect(member.ticketId) : undefined}
                role={isPending ? 'button' : undefined}
                tabIndex={isPending ? 0 : undefined}
                onKeyDown={
                  isPending
                    ? e => e.key === 'Enter' && handleTicketSelect(member.ticketId)
                    : undefined
                }
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <h4 className="truncate font-medium text-navy-900 dark:text-[var(--color-text)]">
                      {member.summary || 'No summary'}
                    </h4>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                      <span>{member.ticketNumber}</span>
                      {member.category && (
                        <>
                          <span>•</span>
                          <span>{member.category}</span>
                        </>
                      )}
                      {member.createdAt && (
                        <>
                          <span>•</span>
                          <span>{formatDate(member.createdAt)}</span>
                        </>
                      )}
                      {member.confidenceScore != null && (
                        <>
                          <span>•</span>
                          <span className="rounded bg-primary-100 px-1.5 py-0.5 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300">
                            {Math.round(member.confidenceScore * 100)}% match
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              {isPending && onRemoveTicket && cluster.ticketCount > 2 && (
                <button
                  className="absolute right-2 top-2 rounded-md p-1 text-navy-600 hover:bg-navy-100 hover:text-red-500 dark:text-[var(--color-text-secondary)] dark:hover:bg-navy-800"
                  onClick={() => handleRemoveTicket(member.ticketId)}
                  title="Remove from cluster"
                  disabled={isProcessing}
                >
                  <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path
                      fillRule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      {isPending && (
        <div className="border-t border-navy-200 bg-navy-50 px-6 py-4 dark:border-[var(--color-border)] dark:bg-[var(--color-surface-alt)]">
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={handleDismiss}
              disabled={isProcessing}
              className="rounded-md border border-navy-300 bg-white px-4 py-2 text-sm font-medium text-navy-700 hover:bg-navy-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-[var(--color-border)] dark:bg-[var(--color-surface-card)] dark:text-[var(--color-text-secondary)] dark:hover:bg-[var(--color-surface-alt)]"
            >
              Dismiss Cluster
            </button>

            <button
              onClick={() => setShowMergeDialog(true)}
              disabled={!selectedTicketId || isProcessing}
              className="btn-primary"
            >
              Merge Tickets
            </button>
          </div>
        </div>
      )}

      {/* Dismissed info */}
      {cluster.status === 'dismissed' && (
        <div className="border-t border-navy-200 bg-navy-50 px-6 py-4 dark:border-[var(--color-border)] dark:bg-[var(--color-surface-alt)]">
          <p className="text-sm text-navy-600 dark:text-[var(--color-text-secondary)]">
            <span className="font-medium">Dismissed</span>
          </p>
        </div>
      )}

      {/* Merge dialog */}
      {showMergeDialog && selectedTicketId && (
        <MergeDialog
          members={cluster.members}
          selectedTicketId={selectedTicketId}
          onConfirm={handleMerge}
          onCancel={() => setShowMergeDialog(false)}
          isLoading={isProcessing}
        />
      )}
    </div>
  );
}

export default ClusterDetail;
