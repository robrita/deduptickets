/**
 * TicketDetailModal component.
 *
 * Modal dialog displaying full ticket details.
 */

import type { Ticket } from '../../types';

export interface TicketDetailModalProps {
  ticket: Ticket;
  onClose: () => void;
  isLoading?: boolean;
}

function formatDate(dateString?: string): string {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleString();
}

function formatCurrency(amount?: number, currency?: string): string {
  if (amount === undefined || amount === null) return '-';
  return `${currency || 'PHP'} ${amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

export function TicketDetailModal({ ticket, onClose, isLoading = false }: TicketDetailModalProps) {
  const statusColors: Record<string, string> = {
    open: 'bg-blue-100 text-blue-800',
    in_progress: 'bg-yellow-100 text-yellow-800',
    resolved: 'bg-green-100 text-green-800',
    closed: 'bg-gray-100 text-gray-800',
    merged: 'bg-purple-100 text-purple-800',
  };

  const priorityColors: Record<string, string> = {
    low: 'bg-gray-100 text-gray-800',
    medium: 'bg-blue-100 text-blue-800',
    high: 'bg-orange-100 text-orange-800',
    urgent: 'bg-red-100 text-red-800',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{ticket.ticketNumber}</h2>
            <p className="mt-1 text-sm text-gray-500">{ticket.category}</p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-3 py-1 text-xs font-medium ${statusColors[ticket.status] || 'bg-gray-100'}`}
            >
              {ticket.status.replace('_', ' ')}
            </span>
            {ticket.priority && (
              <span
                className={`rounded-full px-3 py-1 text-xs font-medium ${priorityColors[ticket.priority] || 'bg-gray-100'}`}
              >
                {ticket.priority}
              </span>
            )}
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          </div>
        ) : (
          <div className="px-6 py-4">
            {/* Summary & Description */}
            <div className="mb-6">
              <h3 className="mb-2 text-sm font-medium text-gray-700">Summary</h3>
              <p className="text-gray-900">{ticket.summary}</p>
              {ticket.description && (
                <>
                  <h3 className="mb-2 mt-4 text-sm font-medium text-gray-700">Description</h3>
                  <p className="whitespace-pre-wrap text-gray-700">{ticket.description}</p>
                </>
              )}
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-2 gap-4 border-t border-gray-200 pt-4 md:grid-cols-3">
              <div>
                <p className="text-xs text-gray-500">Channel</p>
                <p className="font-medium text-gray-900">
                  {ticket.channel?.replace('_', ' ') || '-'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Severity</p>
                <p className="font-medium text-gray-900">{ticket.severity?.toUpperCase() || '-'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Subcategory</p>
                <p className="font-medium text-gray-900">{ticket.subcategory || '-'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Customer ID</p>
                <p className="font-medium text-gray-900">{ticket.customerId || '-'}</p>
              </div>
            </div>

            {/* Transaction Details */}
            {(ticket.transactionId || ticket.amount !== undefined) && (
              <div className="mt-4 grid grid-cols-2 gap-4 border-t border-gray-200 pt-4 md:grid-cols-3">
                <div>
                  <p className="text-xs text-gray-500">Transaction ID</p>
                  <p className="font-medium text-gray-900">{ticket.transactionId || '-'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Amount</p>
                  <p className="font-medium text-gray-900">
                    {formatCurrency(ticket.amount, ticket.currency)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Merchant</p>
                  <p className="font-medium text-gray-900">{ticket.merchant || '-'}</p>
                </div>
              </div>
            )}

            {/* Timestamps */}
            <div className="mt-4 grid grid-cols-2 gap-4 border-t border-gray-200 pt-4 md:grid-cols-3">
              <div>
                <p className="text-xs text-gray-500">Created At</p>
                <p className="font-medium text-gray-900">{formatDate(ticket.createdAt)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Updated At</p>
                <p className="font-medium text-gray-900">{formatDate(ticket.updatedAt)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Occurred At</p>
                <p className="font-medium text-gray-900">{formatDate(ticket.occurredAt)}</p>
              </div>
            </div>

            {/* Cluster & Merge Info */}
            {(ticket.clusterId || ticket.mergedIntoId) && (
              <div className="mt-4 grid grid-cols-2 gap-4 border-t border-gray-200 pt-4">
                {ticket.clusterId && (
                  <div>
                    <p className="text-xs text-gray-500">Cluster ID</p>
                    <p className="font-mono text-sm text-gray-900">{ticket.clusterId}</p>
                  </div>
                )}
                {ticket.mergedIntoId && (
                  <div>
                    <p className="text-xs text-gray-500">Merged Into</p>
                    <p className="font-mono text-sm text-gray-900">{ticket.mergedIntoId}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end border-t border-gray-200 bg-gray-50 px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default TicketDetailModal;
