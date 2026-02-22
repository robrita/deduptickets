/**
 * RevertConfirmDialog component.
 *
 * Modal dialog for confirming merge revert with conflict warnings.
 */

import React, { useState } from 'react';
import type { MergeOperation, RevertConflict } from '../../types';

interface RevertConfirmDialogProps {
  merge: MergeOperation;
  conflicts: RevertConflict[] | null;
  isOpen: boolean;
  isLoading: boolean;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}

export const RevertConfirmDialog: React.FC<RevertConfirmDialogProps> = ({
  merge,
  conflicts,
  isOpen,
  isLoading,
  onConfirm,
  onCancel,
}) => {
  const [reason, setReason] = useState('');

  if (!isOpen) return null;

  const hasConflicts = conflicts && conflicts.length > 0;
  const conflictCount = conflicts?.length ?? 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onConfirm(reason);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div className="modal-backdrop" onClick={onCancel} />

      {/* Dialog */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="modal-panel relative max-w-lg p-0">
          {/* Header */}
          <div className="border-b border-navy-200 px-6 py-4 dark:border-[var(--color-border)]">
            <h2 className="text-lg font-semibold text-navy-900 dark:text-[var(--color-text)]">
              Revert Merge Operation
            </h2>
            <p className="mt-1 text-sm text-navy-600 dark:text-[var(--color-text-secondary)]">
              This will restore {merge.secondaryTicketIds.length} tickets to their original state.
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Body */}
            <div className="px-6 py-4 space-y-4">
              {/* Merge details */}
              <div className="rounded-md bg-navy-50 p-4 dark:bg-[var(--color-surface-alt)]">
                <h3 className="text-sm font-medium text-navy-700 dark:text-[var(--color-text-secondary)]">
                  Merge Details
                </h3>
                <dl className="mt-2 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-navy-600 dark:text-[var(--color-text-secondary)]">
                      Performed by:
                    </dt>
                    <dd className="text-navy-900 dark:text-[var(--color-text)]">
                      {merge.performedBy}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-navy-600 dark:text-[var(--color-text-secondary)]">
                      Performed at:
                    </dt>
                    <dd className="text-navy-900 dark:text-[var(--color-text)]">
                      {formatDate(merge.performedAt)}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-navy-600 dark:text-[var(--color-text-secondary)]">
                      Tickets merged:
                    </dt>
                    <dd className="text-navy-900 dark:text-[var(--color-text)]">
                      {merge.secondaryTicketIds.length}
                    </dd>
                  </div>
                </dl>
              </div>

              {/* Conflict warning */}
              {hasConflicts && (
                <div className="alert-warning">
                  <div className="flex">
                    <svg className="h-5 w-5 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
                      <path
                        fillRule="evenodd"
                        d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium">Conflicts Detected</h3>
                      <p className="mt-1 text-sm">
                        {conflictCount} subsequent merge operation
                        {conflictCount !== 1 ? 's' : ''} may be affected. Reverting will restore
                        original tickets but subsequent merges may need to be reviewed.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Reason input */}
              <div>
                <label
                  htmlFor="revert-reason"
                  className="block text-sm font-medium text-navy-700 dark:text-[var(--color-text-secondary)]"
                >
                  Reason for revert
                </label>
                <textarea
                  id="revert-reason"
                  name="reason"
                  rows={3}
                  className="mt-1 block w-full rounded-md border-navy-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:border-[var(--color-border)] dark:bg-[var(--color-surface-alt)] dark:text-[var(--color-text)]"
                  placeholder="Optional: Explain why this merge is being reverted..."
                  value={reason}
                  onChange={e => setReason(e.target.value)}
                />
              </div>

              {/* Warning */}
              <p className="helper-text">
                ⚠️ This action will restore the merged tickets to their state before the merge. The
                cluster will be reopened for review.
              </p>
            </div>

            {/* Footer */}
            <div className="border-t border-navy-200 px-6 py-4 flex justify-end gap-3 dark:border-[var(--color-border)]">
              <button
                type="button"
                onClick={onCancel}
                disabled={isLoading}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button type="submit" disabled={isLoading} className="btn-warning">
                {isLoading ? (
                  <span className="flex items-center">
                    <span className="spinner-sm mr-2" />
                    Reverting...
                  </span>
                ) : (
                  'Confirm Revert'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
