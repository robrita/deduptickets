/**
 * MergeDialog component.
 *
 * Confirmation dialog for merging tickets with primary selection.
 */

import { useState } from 'react';
import type { MergeBehavior, Ticket } from '../../types';
import { TicketPreview } from '../shared/TicketPreview';

export interface MergeDialogProps {
  tickets: Ticket[];
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
  tickets,
  selectedTicketId,
  onConfirm,
  onCancel,
  isLoading = false,
}: MergeDialogProps) {
  const [behavior, setBehavior] = useState<MergeBehavior>('keep_latest');

  const selectedTicket = tickets.find(t => t.id === selectedTicketId);
  const otherTickets = tickets.filter(t => t.id !== selectedTicketId);

  if (!selectedTicket) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white shadow-xl">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-900">Confirm Merge</h2>
          <p className="mt-1 text-sm text-gray-500">
            Merge {tickets.length} tickets into a single primary ticket
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          {/* Primary ticket */}
          <div className="mb-6">
            <h3 className="mb-2 text-sm font-medium text-gray-700">
              Primary Ticket (will be kept)
            </h3>
            <TicketPreview ticket={selectedTicket} isCanonical />
          </div>

          {/* Duplicates */}
          <div className="mb-6">
            <h3 className="mb-2 text-sm font-medium text-gray-700">
              Duplicates ({otherTickets.length} tickets will be merged)
            </h3>
            <div className="max-h-40 space-y-2 overflow-y-auto">
              {otherTickets.map(ticket => (
                <div
                  key={ticket.id}
                  className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm"
                >
                  <p className="font-medium text-gray-900">{ticket.summary}</p>
                  <p className="text-xs text-gray-500">
                    {ticket.channel} • {ticket.ticket_number}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Merge behavior */}
          <div>
            <h3 className="mb-2 text-sm font-medium text-gray-700">Merge Behavior</h3>
            <div className="space-y-2">
              {mergeBehaviorOptions.map(option => (
                <label
                  key={option.value}
                  className={`flex cursor-pointer items-start rounded-lg border p-3 transition-colors ${
                    behavior === option.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
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
                    <p className="font-medium text-gray-900">{option.label}</p>
                    <p className="text-sm text-gray-500">{option.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(behavior)}
            disabled={isLoading}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading && (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            )}
            Confirm Merge
          </button>
        </div>
      </div>
    </div>
  );
}

export default MergeDialog;
