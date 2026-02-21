/**
 * TicketsTable component.
 *
 * Sortable table displaying tickets with click-to-view functionality.
 */

import type { Ticket, TicketFilters } from '../../types';
import { statusStyles, priorityStyles } from '../../theme/colors';

export interface TicketsTableProps {
  tickets: Ticket[];
  sortBy: TicketFilters['sort_by'];
  sortOrder: TicketFilters['sort_order'];
  onSort: (field: TicketFilters['sort_by']) => void;
  onRowClick: (ticketId: string) => void;
  isLoading?: boolean;
}

type SortableField = 'createdAt' | 'priority' | 'status' | 'ticketNumber';

function SortIcon({ active, order }: { active: boolean; order: 'asc' | 'desc' }) {
  if (!active) {
    return (
      <svg
        className="ml-1 inline h-4 w-4 text-gray-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
        />
      </svg>
    );
  }
  return order === 'asc' ? (
    <svg
      className="ml-1 inline h-4 w-4 text-primary-600"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
    </svg>
  ) : (
    <svg
      className="ml-1 inline h-4 w-4 text-primary-600"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

function formatDate(dateString?: string): string {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString();
}

export function TicketsTable({
  tickets,
  sortBy,
  sortOrder,
  onSort,
  onRowClick,
  isLoading = false,
}: TicketsTableProps) {
  const columns: {
    key: SortableField | 'summary' | 'clusterId';
    label: string;
    sortable: boolean;
  }[] = [
    { key: 'ticketNumber', label: 'Ticket #', sortable: true },
    { key: 'summary', label: 'Summary', sortable: false },
    { key: 'status', label: 'Status', sortable: true },
    { key: 'priority', label: 'Priority', sortable: true },
    { key: 'createdAt', label: 'Created', sortable: true },
    { key: 'clusterId', label: 'Cluster', sortable: false },
  ];

  const handleHeaderClick = (field: SortableField | 'summary' | 'clusterId') => {
    if (['summary', 'clusterId'].includes(field)) return;
    onSort(field as SortableField);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="spinner" />
        <span className="ml-3 text-gray-600">Loading tickets...</span>
      </div>
    );
  }

  if (tickets.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
        <p className="text-gray-500">No tickets found</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                scope="col"
                className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 ${
                  col.sortable ? 'cursor-pointer hover:bg-gray-100' : ''
                }`}
                onClick={() => handleHeaderClick(col.key)}
              >
                {col.label}
                {col.sortable && (
                  <SortIcon active={sortBy === col.key} order={sortOrder || 'desc'} />
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {tickets.map(ticket => (
            <tr
              key={ticket.id}
              onClick={() => onRowClick(ticket.id)}
              className="cursor-pointer hover:bg-gray-50"
            >
              <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                {ticket.ticketNumber}
              </td>
              <td className="max-w-xs truncate px-4 py-3 text-sm text-gray-700">
                {ticket.summary}
              </td>
              <td className="whitespace-nowrap px-4 py-3">
                <span
                  className={`badge ${statusStyles[ticket.status] || 'badge-neutral'}`}
                >
                  {ticket.status.replace('_', ' ')}
                </span>
              </td>
              <td className="whitespace-nowrap px-4 py-3">
                {ticket.priority && (
                  <span
                    className={`badge ${priorityStyles[ticket.priority] || 'badge-neutral'}`}
                  >
                    {ticket.priority}
                  </span>
                )}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                {formatDate(ticket.createdAt)}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-sm">
                {ticket.clusterId ? (
                  <span className="rounded bg-primary-100 px-2 py-1 text-xs text-primary-700">
                    Assigned
                  </span>
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default TicketsTable;
