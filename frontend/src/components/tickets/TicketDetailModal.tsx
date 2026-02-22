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
      <div className="mx-4 max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white shadow-xl dark:bg-[var(--color-surface-card)]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-navy-200 px-6 py-4 dark:border-[var(--color-border)]">
          <div>
            <h2 className="text-lg font-semibold text-navy-900 dark:text-[var(--color-text)]">
              {ticket.ticketNumber}
            </h2>
            <p className="mt-1 text-sm text-navy-600 dark:text-[var(--color-text-secondary)]">
              {ticket.category}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`badge ${statusStyles[ticket.status] || 'badge-neutral'}`}>
              {ticket.status.replace('_', ' ')}
            </span>
            {ticket.priority && (
              <span className={`badge ${priorityStyles[ticket.priority] || 'badge-neutral'}`}>
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
              <h3 className="mb-2 text-sm font-medium text-navy-700 dark:text-[var(--color-text-secondary)]">
                Summary
              </h3>
              <p className="text-navy-900 dark:text-[var(--color-text)]">{ticket.summary}</p>
              {ticket.description && (
                <>
                  <h3 className="mb-2 mt-4 text-sm font-medium text-navy-700 dark:text-[var(--color-text-secondary)]">
                    Description
                  </h3>
                  <p className="whitespace-pre-wrap text-navy-700 dark:text-[var(--color-text-secondary)]">
                    {ticket.description}
                  </p>
                </>
              )}
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-2 gap-4 border-t border-navy-200 pt-4 md:grid-cols-3 dark:border-[var(--color-border)]">
              <div>
                <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Channel
                </p>
                <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                  {ticket.channel?.replace('_', ' ') || '-'}
                </p>
              </div>
              <div>
                <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Severity
                </p>
                <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                  {ticket.severity?.toUpperCase() || '-'}
                </p>
              </div>
              <div>
                <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Subcategory
                </p>
                <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                  {ticket.subcategory || '-'}
                </p>
              </div>
              <div>
                <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Customer ID
                </p>
                <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                  {ticket.customerId || '-'}
                </p>
              </div>
            </div>

            {/* Transaction Details */}
            {(ticket.transactionId || ticket.amount !== undefined) && (
              <div className="mt-4 grid grid-cols-2 gap-4 border-t border-navy-200 pt-4 md:grid-cols-3 dark:border-[var(--color-border)]">
                <div>
                  <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                    Transaction ID
                  </p>
                  <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                    {ticket.transactionId || '-'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                    Amount
                  </p>
                  <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                    {formatCurrency(ticket.amount, ticket.currency)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                    Merchant
                  </p>
                  <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                    {ticket.merchant || '-'}
                  </p>
                </div>
              </div>
            )}

            {/* Timestamps */}
            <div className="mt-4 grid grid-cols-2 gap-4 border-t border-navy-200 pt-4 md:grid-cols-3 dark:border-[var(--color-border)]">
              <div>
                <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Created At
                </p>
                <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                  {formatDate(ticket.createdAt)}
                </p>
              </div>
              <div>
                <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Updated At
                </p>
                <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                  {formatDate(ticket.updatedAt)}
                </p>
              </div>
              <div>
                <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                  Occurred At
                </p>
                <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                  {formatDate(ticket.occurredAt)}
                </p>
              </div>
            </div>

            {/* Cluster & Merge Info */}
            {(ticket.clusterId || ticket.mergedIntoId) && (
              <div className="mt-4 grid grid-cols-2 gap-4 border-t border-navy-200 pt-4 dark:border-[var(--color-border)]">
                {ticket.clusterId && (
                  <div>
                    <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                      Cluster ID
                    </p>
                    <p className="font-mono text-sm text-navy-900 dark:text-[var(--color-text)]">
                      {ticket.clusterId}
                    </p>
                  </div>
                )}
                {ticket.mergedIntoId && (
                  <div>
                    <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                      Merged Into
                    </p>
                    <p className="font-mono text-sm text-navy-900 dark:text-[var(--color-text)]">
                      {ticket.mergedIntoId}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end border-t border-navy-200 bg-navy-50 px-6 py-4 dark:border-[var(--color-border)] dark:bg-[var(--color-surface-alt)]">
          <button onClick={onClose} className="btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default TicketDetailModal;
