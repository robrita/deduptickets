/**
 * TicketDetailModal component.
 *
 * Modal dialog displaying full ticket details.
 */

import type { Ticket } from '../../types';
import { statusStyles, priorityStyles } from '../../theme/colors';

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
  return (
    <div className="modal-backdrop flex items-center justify-center">
      <div className="mx-4 max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{ticket.ticketNumber}</h2>
            <p className="mt-1 text-sm text-gray-500">{ticket.category}</p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`badge ${statusStyles[ticket.status] || 'badge-neutral'}`}
            >
              {ticket.status.replace('_', ' ')}
            </span>
            {ticket.priority && (
              <span
                className={`badge ${priorityStyles[ticket.priority] || 'badge-neutral'}`}
              >
                {ticket.priority}
              </span>
            )}
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="spinner" />
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
            className="btn-secondary"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default TicketDetailModal;
