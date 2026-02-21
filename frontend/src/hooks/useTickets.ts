/**
 * useTickets hook.
 *
 * Provides ticket data fetching with pagination, sorting, and filtering.
 */

import { useCallback, useEffect, useState } from 'react';
import type { Ticket, TicketFilters, PaginationMeta } from '../types';
import { ticketService } from '../services/ticketService';

export interface UseTicketsResult {
  tickets: Ticket[];
  selectedTicket: Ticket | null;
  pagination: PaginationMeta | null;
  isLoading: boolean;
  isLoadingDetail: boolean;
  error: Error | null;
  filters: TicketFilters;
  page: number;
  pageSize: number;
  setFilters: (filters: TicketFilters) => void;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setSorting: (sortBy: TicketFilters['sort_by'], sortOrder: TicketFilters['sort_order']) => void;
  selectTicket: (ticketId: string | null) => Promise<void>;
  refresh: () => Promise<void>;
}

export function useTickets(defaultMonth?: string): UseTicketsResult {
  const currentMonth = defaultMonth || new Date().toISOString().slice(0, 7);

  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filters, setFilters] = useState<TicketFilters>({
    month: currentMonth,
    sort_by: 'createdAt',
    sort_order: 'desc',
  });

  const fetchTickets = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await ticketService.list({
        ...filters,
        page,
        page_size: pageSize,
      });

      setTickets(response.data);
      setPagination(response.meta);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load tickets'));
    } finally {
      setIsLoading(false);
    }
  }, [filters, page, pageSize]);

  const selectTicket = useCallback(
    async (ticketId: string | null) => {
      if (!ticketId) {
        setSelectedTicket(null);
        return;
      }

      setIsLoadingDetail(true);
      try {
        const ticket = await ticketService.get(ticketId, filters.month || currentMonth);
        setSelectedTicket(ticket);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to load ticket'));
      } finally {
        setIsLoadingDetail(false);
      }
    },
    [filters.month, currentMonth]
  );

  const setSorting = useCallback(
    (sortBy: TicketFilters['sort_by'], sortOrder: TicketFilters['sort_order']) => {
      setFilters(prev => ({ ...prev, sort_by: sortBy, sort_order: sortOrder }));
      setPage(1); // Reset to first page when sorting changes
    },
    []
  );

  const refresh = useCallback(async () => {
    await fetchTickets();
  }, [fetchTickets]);

  // Reset page when filters change
  const handleSetFilters = useCallback((newFilters: TicketFilters) => {
    setFilters(newFilters);
    setPage(1);
  }, []);

  // Sync month from parent when prop changes
  useEffect(() => {
    setFilters(prev => {
      if (prev.month === currentMonth) return prev;
      return { ...prev, month: currentMonth };
    });
    setPage(1);
  }, [currentMonth]);

  // Initial load and refetch on changes
  useEffect(() => {
    fetchTickets();
  }, [fetchTickets]);

  return {
    tickets,
    selectedTicket,
    pagination,
    isLoading,
    isLoadingDetail,
    error,
    filters,
    page,
    pageSize,
    setFilters: handleSetFilters,
    setPage,
    setPageSize,
    setSorting,
    selectTicket,
    refresh,
  };
}

export default useTickets;
