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
      <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" onClick={onCancel} />

      {/* Dialog */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-lg rounded-lg bg-white shadow-xl">
          {/* Header */}
          <div className="border-b border-gray-200 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900">Revert Merge Operation</h2>
            <p className="mt-1 text-sm text-gray-500">
              This will restore {merge.secondary_ticket_ids.length} tickets to their original state.
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Body */}
            <div className="px-6 py-4 space-y-4">
              {/* Merge details */}
              <div className="rounded-md bg-gray-50 p-4">
                <h3 className="text-sm font-medium text-gray-700">Merge Details</h3>
                <dl className="mt-2 space-y-1 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Performed by:</dt>
                    <dd className="text-gray-900">{merge.performed_by}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Performed at:</dt>
                    <dd className="text-gray-900">{formatDate(merge.performed_at)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Tickets merged:</dt>
                    <dd className="text-gray-900">{merge.secondary_ticket_ids.length}</dd>
                  </div>
                </dl>
              </div>

              {/* Conflict warning */}
              {hasConflicts && (
                <div className="rounded-md bg-amber-50 border border-amber-200 p-4">
                  <div className="flex">
                    <svg className="h-5 w-5 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
                      <path
                        fillRule="evenodd"
                        d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-amber-800">Conflicts Detected</h3>
                      <p className="mt-1 text-sm text-amber-700">
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
                <label htmlFor="revert-reason" className="block text-sm font-medium text-gray-700">
                  Reason for revert
                </label>
                <textarea
                  id="revert-reason"
                  name="reason"
                  rows={3}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                  placeholder="Optional: Explain why this merge is being reverted..."
                  value={reason}
                  onChange={e => setReason(e.target.value)}
                />
              </div>

              {/* Warning */}
              <p className="text-sm text-gray-500">
                ⚠️ This action will restore the merged tickets to their state before the merge. The
                cluster will be reopened for review.
              </p>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-200 px-6 py-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={onCancel}
                disabled={isLoading}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {isLoading ? (
                  <span className="flex items-center">
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
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
