/**
 * TicketsPage component.
 *
 * Main page for viewing and filtering tickets with pagination.
 */

import { useState, useCallback } from 'react';
import { useTickets } from '../hooks/useTickets';
import { TicketsTable } from '../components/tickets/TicketsTable';
import { TicketDetailModal } from '../components/tickets/TicketDetailModal';
import type { TicketFilters, TicketStatus } from '../types';

const STATUSES: TicketStatus[] = ['open', 'in_progress', 'resolved', 'closed', 'merged'];

interface TicketsPageProps {
  month: string;
}

export function TicketsPage({ month }: TicketsPageProps) {
  const [showModal, setShowModal] = useState(false);
  const {
    tickets,
    selectedTicket,
    pagination,
    isLoading,
    isLoadingDetail,
    error,
    filters,
    page,
    pageSize,
    setFilters,
    setPage,
    setSorting,
    selectTicket,
  } = useTickets(month);

  const totalPages = pagination ? Math.ceil(pagination.total / pagination.limit) : 1;

  const handleSort = useCallback(
    (field: TicketFilters['sort_by']) => {
      const newOrder = filters.sort_by === field && filters.sort_order === 'desc' ? 'asc' : 'desc';
      setSorting(field, newOrder);
    },
    [filters.sort_by, filters.sort_order, setSorting]
  );

  const handleRowClick = useCallback(
    async (ticketId: string) => {
      await selectTicket(ticketId);
      setShowModal(true);
    },
    [selectTicket]
  );

  const handleCloseModal = useCallback(() => {
    setShowModal(false);
    selectTicket(null);
  }, [selectTicket]);


  const handleStatusChange = useCallback(
    (status: string) => {
      setFilters({ ...filters, status: status ? (status as TicketStatus) : undefined });
    },
    [filters, setFilters]
  );

  return (
    <div className="page-container">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="page-title">Tickets</h1>
        {pagination && (
          <span className="helper-text text-gray-600">{pagination.total} total tickets</span>
        )}
      </div>

      {/* Filters */}
      <div className="mb-6 rounded-lg bg-gray-50 p-4">
        <div className="flex flex-wrap items-center gap-4">
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="status" className="text-sm font-medium text-gray-700">
              Status:
            </label>
            <select
              id="status"
              value={filters.status || ''}
              onChange={e => handleStatusChange(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">All</option>
              {STATUSES.map(status => (
                <option key={status} value={status}>
                  {status.replace('_', ' ')}
                </option>
              ))}
            </select>
          </div>

          {/* Unassigned Only */}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={filters.unassigned_only || false}
              onChange={e => setFilters({ ...filters, unassigned_only: e.target.checked })}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <span className="text-gray-700">Unassigned only</span>
          </label>
        </div>
      </div>

      {/* Error Display */}
      {error && <div className="mb-6 alert-danger">{error.message}</div>}

      {/* Table */}
      <TicketsTable
        tickets={tickets}
        sortBy={filters.sort_by}
        sortOrder={filters.sort_order}
        onSort={handleSort}
        onRowClick={handleRowClick}
        isLoading={isLoading}
      />

      {/* Pagination */}
      {pagination && pagination.total > 0 && (
        <div className="mt-6 flex items-center justify-center gap-4">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="btn-secondary"
          >
            Previous
          </button>
          <span className="helper-text text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="btn-secondary"
          >
            Next
          </button>
          <select
            value={pageSize}
            onChange={() => {
              setPage(1);
              // Note: setPageSize would need to be exposed from useTickets if we want this
            }}
            className="ml-4 rounded-md border border-gray-300 px-2 py-1 text-sm"
            disabled
          >
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
            <option value={100}>100 / page</option>
          </select>
        </div>
      )}

      {/* Detail Modal */}
      {showModal && selectedTicket && (
        <TicketDetailModal
          ticket={selectedTicket}
          onClose={handleCloseModal}
          isLoading={isLoadingDetail}
        />
      )}
    </div>
  );
}

export default TicketsPage;
