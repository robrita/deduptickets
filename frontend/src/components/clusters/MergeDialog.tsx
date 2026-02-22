/**
 * MergeDialog component.
 *
 * Confirmation dialog for merging tickets with primary selection.
 */

import { useState } from 'react';
import type { ClusterMember, MergeBehavior } from '../../types';

export interface MergeDialogProps {
  members: ClusterMember[];
  selectedTicketId: string;
  onConfirm: (behavior: MergeBehavior) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const mergeBehaviorOptions: { value: MergeBehavior; label: string; description: string }[] = [
  {
    value: 'keep_latest',
    label: 'Keep Latest',
    description: 'Use the most recent ticket data only',
  },
  {
    value: 'combine_notes',
    label: 'Combine Notes',
    description: 'Merge notes and comments from all tickets',
  },
  {
    value: 'retain_all',
    label: 'Retain All',
    description: 'Keep all data, link duplicates for reference',
  },
];

export function MergeDialog({
  members,
  selectedTicketId,
  onConfirm,
  onCancel,
  isLoading = false,
}: MergeDialogProps) {
  const [behavior, setBehavior] = useState<MergeBehavior>('keep_latest');

  const selectedMember = members.find(m => m.ticketId === selectedTicketId);
  const otherMembers = members.filter(m => m.ticketId !== selectedTicketId);

  if (!selectedMember) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-black/70">
      <div className="mx-4 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white shadow-xl dark:bg-[var(--color-surface-card)]">
        {/* Header */}
        <div className="border-b border-navy-200 px-6 py-4 dark:border-[var(--color-border)]">
          <h2 className="text-lg font-semibold text-navy-900 dark:text-[var(--color-text)]">
            Confirm Merge
          </h2>
          <p className="mt-1 text-sm text-navy-600 dark:text-[var(--color-text-secondary)]">
            Merge {members.length} tickets into a single primary ticket
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          {/* Primary ticket */}
          <div className="mb-6">
            <h3 className="mb-2 text-sm font-medium text-navy-700 dark:text-[var(--color-text-secondary)]">
              Primary Ticket (will be kept)
            </h3>
            <div className="rounded-lg border border-green-500 bg-green-50 p-3 dark:bg-green-900/30">
              <div className="flex items-center gap-2">
                <h4 className="truncate font-medium text-navy-900 dark:text-[var(--color-text)]">
                  {selectedMember.summary || 'No summary'}
                </h4>
                <span className="flex-shrink-0 rounded bg-green-500 px-1.5 py-0.5 text-xs font-medium text-white">
                  Primary
                </span>
              </div>
              <p className="mt-1 text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                {selectedMember.ticketNumber}
              </p>
            </div>
          </div>

          {/* Duplicates */}
          <div className="mb-6">
            <h3 className="mb-2 text-sm font-medium text-navy-700 dark:text-[var(--color-text-secondary)]">
              Duplicates ({otherMembers.length} tickets will be merged)
            </h3>
            <div className="max-h-40 space-y-2 overflow-y-auto">
              {otherMembers.map(member => (
                <div
                  key={member.ticketId}
                  className="rounded-md border border-navy-200 bg-navy-50 px-3 py-2 text-sm dark:border-[var(--color-border)] dark:bg-[var(--color-surface-alt)]"
                >
                  <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                    {member.summary || 'No summary'}
                  </p>
                  <p className="text-xs text-navy-600 dark:text-[var(--color-text-secondary)]">
                    {member.ticketNumber}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Merge behavior */}
          <div>
            <h3 className="mb-2 text-sm font-medium text-navy-700 dark:text-[var(--color-text-secondary)]">
              Merge Behavior
            </h3>
            <div className="space-y-2">
              {mergeBehaviorOptions.map(option => (
                <label
                  key={option.value}
                  className={`flex cursor-pointer items-start rounded-lg border p-3 transition-colors ${
                    behavior === option.value
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                      : 'border-navy-200 hover:border-navy-300 dark:border-[var(--color-border)] dark:hover:border-[var(--color-border-light)]'
                  }`}
                >
                  <input
                    type="radio"
                    name="mergeBehavior"
                    value={option.value}
                    checked={behavior === option.value}
                    onChange={() => setBehavior(option.value)}
                    className="mt-0.5"
                  />
                  <div className="ml-3">
                    <p className="font-medium text-navy-900 dark:text-[var(--color-text)]">
                      {option.label}
                    </p>
                    <p className="text-sm text-navy-600 dark:text-[var(--color-text-secondary)]">
                      {option.description}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-navy-200 bg-navy-50 px-6 py-4 dark:border-[var(--color-border)] dark:bg-[var(--color-surface-alt)]">
          <button onClick={onCancel} disabled={isLoading} className="btn-secondary">
            Cancel
          </button>
          <button
            onClick={() => onConfirm(behavior)}
            disabled={isLoading}
            className="btn-primary flex items-center gap-2"
          >
            {isLoading && <div className="spinner-sm" />}
            Confirm Merge
          </button>
        </div>
      </div>
    </div>
  );
}

export default MergeDialog;
