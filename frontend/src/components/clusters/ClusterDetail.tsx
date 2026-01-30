/**
 * ClusterDetail component.
 *
 * Full cluster view with member tickets and merge actions.
 */

import { useState } from 'react';
import type { ClusterDetail as ClusterDetailType } from '../../types';
import { ConfidenceBadge } from '../shared/ConfidenceBadge';
import { TicketPreview } from '../shared/TicketPreview';
import { MergeDialog } from './MergeDialog';

export interface ClusterDetailProps {
  cluster: ClusterDetailType;
  onMerge?: (primaryTicketId: string) => Promise<void>;
  onDismiss?: () => Promise<void>;
  onRemoveTicket?: (ticketId: string) => Promise<void>;
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

  const handleDismiss = async () => {
    if (!onDismiss) return;

    setIsProcessing(true);
    try {
      await onDismiss();
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRemoveTicket = async (ticketId: string) => {
    if (!onRemoveTicket) return;

    setIsProcessing(true);
    try {
      await onRemoveTicket(ticketId);
    } finally {
      setIsProcessing(false);
    }
  };

  const isPending = cluster.status === 'pending';

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-semibold text-gray-900">Cluster Details</h2>
              <ConfidenceBadge level={cluster.confidence} />
            </div>
            <p className="mt-1 text-sm text-gray-600">{cluster.summary}</p>
            <p className="mt-1 text-sm text-gray-500">
              {cluster.ticket_count} tickets • Created {formatDate(cluster.created_at)}
            </p>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              className="rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-500"
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

        {/* Matching signals */}
        {cluster.matching_signals && (
          <div className="mt-4">
            <p className="text-xs font-medium uppercase text-gray-500">Matching Signals</p>
            <div className="mt-1 flex flex-wrap gap-2">
              {cluster.matching_signals.exact_matches?.map((match, i) => (
                <span
                  key={`exact-${i}`}
                  className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800"
                >
                  {match.field}: {match.value}
                </span>
              ))}
              {cluster.matching_signals.field_matches?.map((match, i) => (
                <span
                  key={`field-${i}`}
                  className="rounded-full bg-blue-100 px-3 py-1 text-sm font-medium text-blue-800"
                >
                  {match.field}
                </span>
              ))}
              {cluster.matching_signals.text_similarity && (
                <span className="rounded-full bg-purple-100 px-3 py-1 text-sm font-medium text-purple-800">
                  {Math.round(cluster.matching_signals.text_similarity.score * 100)}% text
                  similarity
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Tickets */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-medium text-gray-900">Member Tickets</h3>
          {isPending && (
            <p className="text-sm text-gray-500">Select a ticket as the primary for merging</p>
          )}
        </div>

        <div className="space-y-3">
          {cluster.tickets.map(ticket => (
            <div key={ticket.id} className="relative">
              <TicketPreview
                ticket={ticket}
                isSelected={ticket.id === selectedTicketId}
                onSelect={isPending ? handleTicketSelect : undefined}
              />
              {isPending && onRemoveTicket && cluster.ticket_count > 2 && (
                <button
                  className="absolute right-2 top-2 rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-red-500"
                  onClick={() => handleRemoveTicket(ticket.id)}
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
        <div className="border-t border-gray-200 bg-gray-50 px-6 py-4">
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={handleDismiss}
              disabled={isProcessing}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Dismiss Cluster
            </button>

            <button
              onClick={() => setShowMergeDialog(true)}
              disabled={!selectedTicketId || isProcessing}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Merge Tickets
            </button>
          </div>
        </div>
      )}

      {/* Dismissed info */}
      {cluster.status === 'dismissed' && (
        <div className="border-t border-gray-200 bg-gray-50 px-6 py-4">
          <p className="text-sm text-gray-600">
            <span className="font-medium">Dismissed</span>
          </p>
        </div>
      )}

      {/* Merge dialog */}
      {showMergeDialog && selectedTicketId && (
        <MergeDialog
          tickets={cluster.tickets}
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
